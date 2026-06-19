# GichanFormant Theme File Format

## Purpose

`.gftheme`는 플롯의 디자인 프리셋만 저장하는 JSON 파일이다.

프로젝트 전체 상태를 저장하는 `.gfproj`와 달리, `.gftheme`는 데이터 파일,
정규화, 이상치 제거, 축 범위, 필터 표시 상태, 라벨 이동, 그리기 객체를 저장하지
않는다. 같은 디자인을 다른 데이터와 프로젝트에 재사용하기 위한 파일이다.

## Extension

- Extension: `.gftheme`
- Container: plain UTF-8 JSON
- Schema version: integer, 시작값 `1`

## Top-Level Shape

```json
{
  "schema_version": 1,
  "app": "GichanFormant",
  "theme_name": "Publication Serif",
  "description": "Paper-ready black-and-white formant plot style",
  "created_by": "",
  "created_at": "2026-06-20T00:00:00Z",
  "design": {
    "single": {},
    "compare": {},
    "layer_presets": {}
  }
}
```

## `design.single`

단일 Plot 창의 전역 디자인 설정이다. 현재 `DesignSettingsPanel.get_current_settings()`
및 `SINGLE_DESIGN_DEFAULTS`와 같은 키를 사용한다.

```json
{
  "show_raw": true,
  "show_centroid": true,
  "show_axis_units": false,
  "raw_marker": "o",
  "raw_color": "#606060",
  "centroid_marker": "o",
  "font_style": "serif",
  "lbl_color": "#000000",
  "lbl_size": 18,
  "lbl_bold": false,
  "lbl_italic": false,
  "ell_thick": 1.0,
  "ell_style": "--",
  "ell_color": "#606060",
  "ell_fill_color": null,
  "ell_fill_opacity": 0.15,
  "axis_position_swap": false,
  "y_label_rotation": false,
  "box_spines": false,
  "show_grid": false,
  "grid_opacity": 0.3,
  "show_minor_ticks": true,
  "label_slash_wrap": false
}
```

### Allowed Values

- `font_style`: `"serif"` 또는 `"sans"`
- `raw_marker`: `"o"`, `"x"`, `"a"`
- `centroid_marker`: `"o"`, `"s"`, `"^"`, `"D"`, `"wo"`, `"ws"`, `"w^"`, `"wD"`
- `ell_style`: `"-"`, `"---"`, `"--"`
- `ell_thick`: `0.5`, `1.0`, `2.0`
- color fields: `"#RRGGBB"` 또는 `null`
- opacity fields: `0.0`부터 `1.0`

`is_locked`는 저장하지 않는다. 이것은 UI 조작 상태이지 디자인 자체가 아니다.

## `design.compare`

Compare Plot 창의 디자인 설정이다. 현재 `compare_settings.py`의 구조와 맞춘다.

```json
{
  "common": {
    "show_raw": true,
    "show_centroid": true,
    "raw_marker": "o",
    "label_slash_wrap": false,
    "show_axis_units": false,
    "axis_position_swap": false,
    "y_label_rotation": false,
    "box_spines": false,
    "show_grid": false,
    "grid_opacity": 0.3,
    "show_minor_ticks": true,
    "font_style": "serif"
  },
  "series": {
    "0": {
      "lbl_color": "#000000",
      "lbl_size": 18,
      "lbl_bold": false,
      "lbl_italic": false,
      "ell_thick": 1.0,
      "ell_style": "-",
      "ell_color": "#1976D2",
      "ell_fill_color": null,
      "ell_fill_opacity": 0.15,
      "raw_color": "#606060",
      "centroid_marker": "o"
    },
    "1": {
      "lbl_color": "#000000",
      "lbl_size": 18,
      "lbl_bold": false,
      "lbl_italic": false,
      "ell_thick": 1.0,
      "ell_style": "--",
      "ell_color": "#E64A19",
      "ell_fill_color": null,
      "ell_fill_opacity": 0.15,
      "raw_color": "#606060",
      "centroid_marker": "o"
    }
  }
}
```

`blue`, `red`, `series_2` 같은 legacy mirror key는 `.gftheme`에 저장하지 않는다.
파일에는 `series` 블록만 저장하고, 앱 내부 적용 시 `pack_compare_design_settings()`
또는 `normalize_compare_design_settings()`로 legacy mirror를 생성한다.

## `design.layer_presets`

모음별 레이어 디자인을 재사용하고 싶을 때 쓰는 선택 섹션이다. 특정 데이터의
표시 여부는 저장하지 않고, 순수 디자인 override만 저장한다.

```json
{
  "a": {
    "lbl_color": "#000000",
    "lbl_size": 18,
    "lbl_bold": false,
    "lbl_italic": false,
    "centroid_marker": "o",
    "ell_thick": 1.0,
    "ell_style": "--",
    "ell_color": "#606060",
    "ell_fill_color": null,
    "ell_fill_opacity": 0.15,
    "raw_color": "#606060"
  },
  "i": {
    "lbl_color": "#000000",
    "ell_color": "#606060"
  }
}
```

부분 override를 허용한다. 빠진 키는 현재 전역 디자인 또는 앱 기본값을 따른다.

## Not Included

`.gftheme`에는 아래 항목을 저장하지 않는다.

- 데이터 파일 경로 또는 DataFrame 스냅샷
- plot type, F1/F2 scale, origin, Bark 표시 단위
- normalization, outlier mode, outlier scope
- 축 범위, sigma 값
- 모음 필터 ON/OFF/SEMI
- 라벨 이동 offset
- draw line/polygon/text/reference/legend 객체
- 최근 열기/저장 경로

위 항목은 프로젝트 상태이므로 `.gfproj`에 속한다.

## Example

```json
{
  "schema_version": 1,
  "app": "GichanFormant",
  "theme_name": "Clean Publication",
  "description": "Serif labels, no grid, monochrome ellipses",
  "created_by": "Bae Gichan",
  "created_at": "2026-06-20T00:00:00Z",
  "design": {
    "single": {
      "show_raw": true,
      "show_centroid": true,
      "show_axis_units": false,
      "raw_marker": "o",
      "raw_color": "#606060",
      "centroid_marker": "wo",
      "font_style": "serif",
      "lbl_color": "#000000",
      "lbl_size": 18,
      "lbl_bold": false,
      "lbl_italic": false,
      "ell_thick": 1.0,
      "ell_style": "--",
      "ell_color": "#000000",
      "ell_fill_color": null,
      "ell_fill_opacity": 0.0,
      "axis_position_swap": false,
      "y_label_rotation": false,
      "box_spines": false,
      "show_grid": false,
      "grid_opacity": 0.3,
      "show_minor_ticks": true,
      "label_slash_wrap": false
    },
    "compare": {
      "common": {
        "show_raw": true,
        "show_centroid": true,
        "raw_marker": "o",
        "label_slash_wrap": false,
        "show_axis_units": false,
        "axis_position_swap": false,
        "y_label_rotation": false,
        "box_spines": false,
        "show_grid": false,
        "grid_opacity": 0.3,
        "show_minor_ticks": true,
        "font_style": "serif"
      },
      "series": {
        "0": {
          "lbl_color": "#000000",
          "lbl_size": 18,
          "lbl_bold": false,
          "lbl_italic": false,
          "ell_thick": 1.0,
          "ell_style": "-",
          "ell_color": "#1976D2",
          "ell_fill_color": null,
          "ell_fill_opacity": 0.15,
          "raw_color": "#606060",
          "centroid_marker": "o"
        },
        "1": {
          "lbl_color": "#000000",
          "lbl_size": 18,
          "lbl_bold": false,
          "lbl_italic": false,
          "ell_thick": 1.0,
          "ell_style": "--",
          "ell_color": "#E64A19",
          "ell_fill_color": null,
          "ell_fill_opacity": 0.15,
          "raw_color": "#606060",
          "centroid_marker": "o"
        }
      }
    },
    "layer_presets": {}
  }
}
```
