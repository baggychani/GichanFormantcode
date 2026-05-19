# data_processor.py

import pandas as pd
import numpy as np
import os

import config
from utils import app_logger

# 텍스트 파일 로드 시 시도할 인코딩 순서 (UTF-16 BOM, UTF-8, 한글 Windows, 기타)
ENCODINGS = ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp949", "euc-kr", "latin-1"]

# 마지막 열을 라벨로 쓸 때, 값의 절반 이상이 숫자로 파싱되면 라벨 열이 아닌 것으로 본다.
_LABEL_NUMERIC_RATIO_MAX = 0.5
# F3 열 후보: 100Hz를 넘는 값이 하나라도 있어야 F3로 인정 (기존 휴리스틱 유지)
_F3_MIN_HZ_HINT = 100


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


def _extract_label_series(col_data: pd.Series) -> pd.Series | None:
    """마지막 열에서 모음 라벨 문자열을 추출한다.

    - /모음/ 형식이 있으면 내부 기호만 사용 (공식 가이드 형식).
    - 그 외 짧은 비숫자 텍스트(o, u, ɯ, ㅏ 등)도 인식한다 (편의; 가이드 문구는 변경하지 않음).
    - 열 값의 과반이 숫자로 파싱되면 라벨 열이 아닌 것으로 보고 None을 반환한다.
    """
    str_data = col_data.astype(str).str.strip()
    str_data = str_data.replace({"nan": "", "None": "", "<NA>": ""})

    nonempty = str_data[str_data != ""]
    if nonempty.empty:
        return None

    numeric_ratio = pd.to_numeric(nonempty, errors="coerce").notna().mean()
    if numeric_ratio > _LABEL_NUMERIC_RATIO_MAX:
        return None

    if str_data.str.contains(r"/.+/", regex=True).any():
        extracted = str_data.str.extract(r"/([^/]+)/")[0]
        labels = extracted.fillna(str_data).str.strip()
    else:
        labels = str_data

    labels = labels.replace("", np.nan)
    if labels.notna().sum() == 0:
        return None
    return labels


def _try_parse_f3_column(col_data: pd.Series) -> pd.Series | None:
    """중간 열이 F3인지 판별하고, 0은 측정 없음(NaN)으로 변환한 Series를 반환한다."""
    numeric_data = pd.to_numeric(col_data, errors="coerce")
    if not numeric_data.notna().all():
        return None
    if not (numeric_data > _F3_MIN_HZ_HINT).any():
        return None
    f3 = numeric_data.astype(float)
    f3 = f3.mask(f3 == 0, np.nan)
    return f3


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
        - Col 2 ~ 마지막-1: F3 후보(첫 번째로 인정되는 숫자 열)
        - 마지막 Col: 모음 라벨(IPA 등)
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
                app_logger.error(f"[DataProcessor] 파일 로드 오류 ({path}): {msg}")
                errors.append((path, msg))

        if dfs:
            self.df_all = pd.concat(dfs, ignore_index=True)
            self.df_all.dropna(subset=["F1", "F2"], inplace=True)

            # 데이터 정밀도 유지를 위해 실수형(float)으로 통일
            self.df_all["F1"] = self.df_all["F1"].astype(float)
            self.df_all["F2"] = self.df_all["F2"].astype(float)

            # 유효한 F3 값(측정 있음)이 하나라도 있을 때만 F3 사용 가능
            if "F3" in self.df_all.columns:
                self.df_all["F3"] = self.df_all["F3"].astype(float)
                self.has_f3 = bool(self.df_all["F3"].notna().any())
            else:
                self.has_f3 = False

            return True, self.has_f3, errors
        else:
            return False, False, errors

    def _parse_fixed_columns(self, df):
        """
        데이터프레임의 열을 분석하여 포먼트 및 라벨을 추출합니다.
        - Col 0: F1, Col 1: F2 (필수)
        - 마지막 열: 모음 라벨 (/.../ 또는 짧은 IPA·한글 기호)
        - 그 사이 열: 순서대로 첫 F3 후보 열만 F3로 사용 (F3=0 → NaN, 측정 없음)
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
        final_df["F1"] = f1_numeric[valid_idx].astype(float).values
        final_df["F2"] = f2_numeric[valid_idx].astype(float).values

        ncols = len(df.columns)
        label_col_idx = ncols - 1 if ncols >= 3 else None

        # 3. F3: 마지막 열 직전까지 순서대로 첫 후보만
        if label_col_idx is not None and label_col_idx > 2:
            for i in range(2, label_col_idx):
                f3_series = _try_parse_f3_column(df.iloc[:, i])
                if f3_series is not None:
                    final_df["F3"] = f3_series.values
                    break

        # 4. 라벨: 마지막 열 (열이 3개 이상일 때만; 2열 파일은 라벨 열 없음)
        if label_col_idx is not None:
            labels = _extract_label_series(df.iloc[:, label_col_idx])
            if labels is not None:
                final_df["Label"] = labels.values

        if "Label" not in final_df.columns:
            final_df["Label"] = "Unknown"

        final_df.dropna(subset=["Label"], inplace=True)

        # ------------------------------------------------------------------
        # F1>0, F2>F1 필수.
        # F3가 유효한 행(>0, >F2)만 F3 조건 적용; F3=NaN(측정 없음) 행은 F1·F2만 검사.
        # ------------------------------------------------------------------
        drop_report = None
        if not final_df.empty:
            base_ok = (final_df["F1"] > 0) & (final_df["F2"] > final_df["F1"])

            if "F3" in final_df.columns:
                f3_valid = final_df["F3"].notna()
                f3_ok = (
                    f3_valid & (final_df["F3"] > 0) & (final_df["F3"] > final_df["F2"])
                )
                cond = base_ok & ((~f3_valid) | f3_ok)
            else:
                cond = base_ok

            invalid_rows = final_df[~cond]
            if not invalid_rows.empty:
                drop_report = invalid_rows["Label"].value_counts().to_dict()
            final_df = final_df[cond]

        return final_df, None, drop_report

    def get_data(self, copy=True):
        if copy:
            return self.df_all.copy()
        return self.df_all
