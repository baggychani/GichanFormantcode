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
        return name[len(PREFIX_STRIP) :].lstrip("_") or name
    return name


def truncate_display_name(name: str, max_len: int = MAX_DISPLAY_NAME_LEN) -> str:
    """표시용 파일명을 max_len 이하로 자른다. 넘치면 끝에 ... 붙인다."""
    name = strip_gichan_prefix(name)
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."


def _basename_no_ext(name: str) -> str:
    import os

    return os.path.splitext(strip_gichan_prefix(name or ""))[0]


def format_combined_group_short_label(
    names: list[str], max_first_len: int = MAX_DISPLAY_NAME_LEN
) -> str:
    """다중 compare/combined 그룹 짧은 표시 — 예: 박성진_Short 외 2명."""
    cleaned = [_basename_no_ext(n) for n in names if n]
    if not cleaned:
        return "Combined"
    if len(cleaned) == 1:
        return truncate_display_name(cleaned[0], max_first_len)
    first = truncate_display_name(cleaned[0], max_first_len)
    full = f"{first} 외 {len(cleaned) - 1}명"
    if len(full) <= max_first_len:
        return full
    return full[: max_first_len - 3] + "..."


def format_combined_members_tooltip(names: list[str]) -> str:
    """호버 툴팁용 — 포함 멤버 전체 목록."""
    lines = [_basename_no_ext(n) for n in names if n]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return f"포함 {len(lines)}명\n" + "\n".join(f"· {x}" for x in lines)


def compare_item_legend_display(
    item: dict | None,
) -> tuple[str, str, list[str] | None]:
    """compare 범례용 (짧은 표시, 툴팁, 상세 팝업용 멤버 목록)."""
    if not item:
        return "", "", None
    members = item.get("combined_source_names")
    if item.get("is_combined") and isinstance(members, list) and len(members) >= 2:
        short = format_combined_group_short_label(members)
        tooltip = format_combined_members_tooltip(members)
        return short, tooltip, list(members)
    raw = item.get("name", "")
    clean = _basename_no_ext(raw)
    display = truncate_display_name(clean, MAX_DISPLAY_NAME_LEN)
    return display, clean, None


def apply_file_indicator_style(label, data_item) -> None:
    """플롯 상단 n/m 파일 인디케이터 라벨 스타일. Combined는 강조색."""
    if data_item and data_item.get("is_combined"):
        label.setStyleSheet("color: #409EFF; border: none;")
    else:
        label.setStyleSheet("color: #1976D2; border: none;")


def format_file_label(
    n: int, m: int, name: str, max_len: int = MAX_FILE_LABEL_LEN
) -> str:
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
