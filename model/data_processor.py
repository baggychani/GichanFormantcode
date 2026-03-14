# data_processor.py

import pandas as pd
import numpy as np
import os
import re

import config
import app_logger

# 텍스트 파일 로드 시 시도할 인코딩 순서 (UTF-16 BOM, UTF-8, 한글 Windows, 기타)
ENCODINGS = ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp949", "euc-kr", "latin-1"]


def _read_csv_with_encoding(path):
    """여러 인코딩을 순서대로 시도하여 CSV/텍스트 파일을 읽는다. 성공 시 DataFrame 반환."""
    last_err = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(
                path, sep=None, engine="python", header=None, encoding=enc
            )
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    if last_err is not None:
        raise last_err
    raise ValueError("파일을 읽을 수 있는 인코딩을 찾지 못했습니다.")


class DataProcessor:
    def __init__(self):
        # 전체 병합된 포먼트 데이터 (F1, F2, F3, Label 등)
        self.df_all = pd.DataFrame()
        self.has_f3 = False
        # 파일별 조건 미충족 행(라벨별 누락) 정보: load_files 호출마다 갱신
        self.row_drops = []

    def load_files(self, filepaths):
        """
        지정된 경로의 데이터 파일을 로드하고 병합합니다.
        열의 위치(Index)를 기준으로 포먼트 데이터를 엄격하게 매핑합니다.
        - Col 0: F1
        - Col 1: F2
        - Col 2: F3 (단, 유효 조건 충족 시)
        """
        dfs = []
        errors = []
        self.row_drops = []

        for path in filepaths:
            try:
                # 확장자에 따른 파일 읽기 방식 분기
                ext = os.path.splitext(path)[1].lower()
                if ext in [".xls", ".xlsx"]:
                    temp_df = pd.read_excel(path, header=None)
                else:
                    temp_df = _read_csv_with_encoding(path)

                # 개별 파일 전처리 (실패 시 구체적 사유 반환)
                processed_df, parse_error, drop_report = self._parse_fixed_columns(
                    temp_df
                )

                if parse_error:
                    errors.append((path, parse_error))
                elif processed_df is not None and not processed_df.empty:
                    dfs.append(processed_df)
                    # 조건 위반으로 제외된 행이 있다면, 파일 경로와 함께 누락 정보를 저장해 둔다.
                    if drop_report:
                        self.row_drops.append((path, drop_report))
                else:
                    errors.append((path, config.PARSE_ERR_EMPTY_RESULT))

            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                print(f"[DataProcessor] 파일 로드 오류 ({path}): {msg}")
                errors.append((path, msg))

        if dfs:
            self.df_all = pd.concat(dfs, ignore_index=True)
            self.df_all.dropna(subset=["F1", "F2"], inplace=True)

            # 데이터 정밀도 유지를 위해 실수형(float)으로 통일
            self.df_all["F1"] = self.df_all["F1"].astype(float)
            self.df_all["F2"] = self.df_all["F2"].astype(float)

            # 유효한 F3 데이터가 존재하는 경우 타입 변환 및 상태 업데이트
            if "F3" in self.df_all.columns:
                self.df_all["F3"] = self.df_all["F3"].astype(float)
                self.has_f3 = True
            else:
                self.has_f3 = False

            return True, self.has_f3, errors
        else:
            return False, False, errors

    def _parse_fixed_columns(self, df):
        """
        데이터프레임의 열을 분석하여 포먼트 및 라벨을 추출합니다.
        - Col 0: F1, Col 1: F2 (필수)
        - Col 2~: 순서대로 첫 번째 숫자 열은 F3(선택), 첫 번째 /.../ 패턴 열은 라벨로 인식. F4 등 추가 포먼트는 지원하지 않음.
        반환: (결과 DataFrame 또는 None, 실패 시 오류 메시지 또는 None, 제거된 행 리포트 또는 None)
        """
        # 분석에 필요한 최소 열 개수 검증
        if len(df.columns) < 2:
            return None, config.PARSE_ERR_COLUMNS_TOO_FEW, None

        # 1. F1, F2 데이터 추출 및 숫자형 변환
        f1_col = df.iloc[:, 0]
        f2_col = df.iloc[:, 1]

        f1_numeric = pd.to_numeric(f1_col, errors="coerce")
        f2_numeric = pd.to_numeric(f2_col, errors="coerce")

        # 문자열 헤더 제거 및 F1 < F2 물리적 검증 (음성학적 예외 데이터 차단)
        valid_idx = f1_numeric.notna() & f2_numeric.notna() & (f1_numeric < f2_numeric)
        df = df[valid_idx].copy()

        if df.empty:
            return None, config.PARSE_ERR_F1_F2_INVALID, None

        # 2. 결과 데이터프레임 초기화
        final_df = pd.DataFrame()
        final_df["F1"] = f1_numeric[valid_idx]
        final_df["F2"] = f2_numeric[valid_idx]

        # 3. F3 및 Label 탐색
        remaining_cols = range(2, len(df.columns))
        found_f3 = False
        found_label = False

        for i in remaining_cols:
            col_data = df.iloc[:, i]

            # 숫자형 데이터 검증
            numeric_data = pd.to_numeric(col_data, errors="coerce")
            is_numeric = numeric_data.notna().all()

            if is_numeric and not found_f3:
                # 음향 데이터의 특성을 반영하여 100Hz 초과 값 존재 여부로 실제 F3 판단
                if (numeric_data > 100).any():
                    final_df["F3"] = numeric_data
                    found_f3 = True

            elif not found_label:
                # 라벨 패턴 정규식 매칭 (/Label/ 형식)
                str_data = col_data.astype(str)
                if str_data.str.contains(r"/.+/").any():
                    extracted = str_data.str.extract(r"/([^/]+)/")[0]
                    final_df["Label"] = extracted.str.strip()
                    found_label = True

        # 라벨 열이 발견되지 않은 경우 기본값 할당
        if "Label" not in final_df.columns:
            final_df["Label"] = "Unknown"

        # 라벨이 누락된 행 제거
        final_df.dropna(subset=["Label"], inplace=True)

        # ------------------------------------------------------------------
        # F1>0, F1<F2, (F3 존재 시) F2<F3 및 F3>0 조건을 만족하지 않는 행 제거
        # 제거된 행에 대해서는 라벨별 누락 개수를 drop_report로 반환한다.
        # ------------------------------------------------------------------
        drop_report = None
        if not final_df.empty:
            if "F3" in final_df.columns:
                cond = (
                    (final_df["F1"] > 0)
                    & (final_df["F2"] > final_df["F1"])
                    & (final_df["F3"] > final_df["F2"])
                    & (final_df["F3"] > 0)
                )
            else:
                cond = (final_df["F1"] > 0) & (final_df["F2"] > final_df["F1"])
            invalid_rows = final_df[~cond]
            if not invalid_rows.empty:
                # 라벨별 누락 개수 집계
                drop_report = invalid_rows["Label"].value_counts().to_dict()
            final_df = final_df[cond]

        return final_df, None, drop_report

    def get_data(self):
        return self.df_all.copy()
