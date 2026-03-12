# path_prefs.py — 최근 업로드/다운로드 경로 JSON 저장·로드

import os
import json


def get_path_prefs_path(base_dir):
    """앱 데이터 디렉터리(base_dir) 기준 path_prefs.json 경로 반환."""
    return os.path.join(base_dir, "path_prefs.json")


def load_path_prefs(base_dir):
    """
    path_prefs.json에서 경로 설정 로드.
    base_dir: QStandardPaths.writableLocation(AppDataLocation) 등.
    반환: {"last_open_dir": str or None, "last_save_dir": str or None}
    """
    path = get_path_prefs_path(base_dir)
    out = {"last_open_dir": None, "last_save_dir": None}
    if not base_dir or not os.path.isfile(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out["last_open_dir"] = data.get("last_open_dir") or None
        out["last_save_dir"] = data.get("last_save_dir") or None
    except Exception:
        pass
    return out


def save_path_prefs(base_dir, prefs):
    """
    경로 설정을 path_prefs.json에 저장.
    base_dir가 없으면 생성 후 저장.
    prefs: {"last_open_dir": str or None, "last_save_dir": str or None}
    """
    if not base_dir:
        return
    path = get_path_prefs_path(base_dir)
    try:
        os.makedirs(base_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_open_dir": prefs.get("last_open_dir") or "",
                    "last_save_dir": prefs.get("last_save_dir") or "",
                },
                f,
                ensure_ascii=False,
                indent=0,
            )
    except Exception:
        pass
