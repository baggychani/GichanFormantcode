"""Framework-neutral display naming helpers."""

import os
import re

MAX_FILE_LABEL_LEN = 25
MAX_DISPLAY_NAME_LEN = 20
MAX_LAYER_FILE_BTN_LEN = 19
PREFIX_STRIP = "gichanformant_"


def strip_gichan_prefix(name: str) -> str:
    if not name:
        return name
    if name.lower().startswith(PREFIX_STRIP):
        return name[len(PREFIX_STRIP) :].lstrip("_") or name
    return name


def truncate_display_name(name: str, max_len: int = MAX_DISPLAY_NAME_LEN) -> str:
    name = strip_gichan_prefix(name)
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."


def _basename_no_ext(name: str) -> str:
    return os.path.splitext(strip_gichan_prefix(name or ""))[0]


def format_combined_group_short_label(
    names: list[str], max_first_len: int = MAX_DISPLAY_NAME_LEN
) -> str:
    cleaned = [_basename_no_ext(name) for name in names if name]
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
    lines = [_basename_no_ext(name) for name in names if name]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return f"포함 {len(lines)}명\n" + "\n".join(f"· {name}" for name in lines)


def default_combined_export_txt_basename(
    source_names: list[str], *, fallback: str = "Combined"
) -> str:
    cleaned = [_basename_no_ext(name) for name in source_names if name]
    if not cleaned:
        base = fallback
    elif len(cleaned) == 1:
        base = cleaned[0]
    else:
        base = f"{cleaned[0]}_외{len(cleaned) - 1}명"
    safe = re.sub(r'[<>:"/\\|?*]', "_", base).strip()
    return safe or fallback


def compare_item_legend_display(
    item: dict | None,
) -> tuple[str, str, list[str] | None]:
    if not item:
        return "", "", None
    members = item.get("combined_source_names")
    if item.get("is_combined") and isinstance(members, list) and len(members) >= 2:
        return (
            format_combined_group_short_label(members),
            format_combined_members_tooltip(members),
            list(members),
        )
    raw = item.get("name", "")
    clean = _basename_no_ext(raw)
    return truncate_display_name(clean, MAX_DISPLAY_NAME_LEN), clean, None


def apply_file_indicator_style(label, data_item) -> None:
    if data_item and data_item.get("is_combined"):
        label.setStyleSheet("color: #409EFF; border: none;")
    else:
        label.setStyleSheet("color: #1976D2; border: none;")


def format_file_label(
    n: int, m: int, name: str, max_len: int = MAX_FILE_LABEL_LEN
) -> str:
    name = strip_gichan_prefix(name)
    prefix = f"{n}/{m}: "
    full = prefix + name
    if len(full) <= max_len:
        return full
    allowed = max_len - len(prefix) - 3
    if allowed < 1:
        return prefix + "..."
    return prefix + name[:allowed] + "..."
