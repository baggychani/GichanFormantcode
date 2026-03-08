# ui/display_utils.py — 표시용 파일명/라벨 길이 제한 (순환 import 방지)

# 파일 인디케이터 라벨용 최대 글자 수 (n/m은 항상 보이도록, 초과분은 파일명 말줄임)
MAX_FILE_LABEL_LEN = 25
# 탭/범례 등 표시용 파일명 최대 글자 수
MAX_DISPLAY_NAME_LEN = 20
# 다중 플롯 레이어 설정 - 레이어 목록 위 파일 선택 버튼용
MAX_LAYER_FILE_BTN_LEN = 19

PREFIX_STRIP = "gichanformant_"


def strip_gichan_prefix(name: str) -> str:
    """표시용: 파일명이 GichanFormant_ 로 시작하면(대소문자 무시) 해당 접두사 제거."""
    if not name:
        return name
    if name.lower().startswith(PREFIX_STRIP):
        return name[len(PREFIX_STRIP):].lstrip("_") or name
    return name


def truncate_display_name(name: str, max_len: int = MAX_DISPLAY_NAME_LEN) -> str:
    """표시용 파일명을 max_len 이하로 자른다. 넘치면 끝에 ... 붙인다."""
    name = strip_gichan_prefix(name)
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."


def format_file_label(n: int, m: int, name: str, max_len: int = MAX_FILE_LABEL_LEN) -> str:
    """n/m: 파일명 형식 문자열을 max_len 이하로 만든다. 넘치면 파일명만 잘라 끝에 ... 붙인다."""
    name = strip_gichan_prefix(name)
    prefix = f"{n}/{m}: "
    full = prefix + name
    if len(full) <= max_len:
        return full
    allowed = max_len - len(prefix) - 3  # 3 = "..."
    if allowed < 1:
        return prefix + "..."
    return prefix + name[:allowed] + "..."
