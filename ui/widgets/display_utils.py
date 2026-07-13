"""Compatibility exports for display helpers moved to the application core."""

from core.display_utils import (
    MAX_DISPLAY_NAME_LEN,
    MAX_FILE_LABEL_LEN,
    MAX_LAYER_FILE_BTN_LEN,
    PREFIX_STRIP,
    apply_file_indicator_style,
    compare_item_legend_display,
    default_combined_export_txt_basename,
    format_combined_group_short_label,
    format_combined_members_tooltip,
    format_file_label,
    strip_gichan_prefix,
    truncate_display_name,
)

__all__ = [
    "MAX_DISPLAY_NAME_LEN",
    "MAX_FILE_LABEL_LEN",
    "MAX_LAYER_FILE_BTN_LEN",
    "PREFIX_STRIP",
    "apply_file_indicator_style",
    "compare_item_legend_display",
    "default_combined_export_txt_basename",
    "format_combined_group_short_label",
    "format_combined_members_tooltip",
    "format_file_label",
    "strip_gichan_prefix",
    "truncate_display_name",
]
