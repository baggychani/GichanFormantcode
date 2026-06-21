"""Plot 창에서 쓰는 재사용 이벤트 필터."""

from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget


class TabBarWheelBlocker(QObject):
    """탭 위에서 마우스 휠로 탭이 바뀌지 않도록 휠 이벤트를 흡수합니다."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return False


class ClickClearFocusFilter(QObject):
    """다른 위젯 클릭 시 지정한 LineEdit들에서 포커스를 빼서 분석 탭으로 넘깁니다."""

    def __init__(self, window, analysis_tab, edits, parent=None):
        super().__init__(parent)
        self._window = window
        self._analysis_tab = analysis_tab
        self._edits = set(edits)

    def eventFilter(self, obj, event):
        try:
            if (
                event.type() != QEvent.Type.MouseButtonPress
                or event.button() != Qt.MouseButton.LeftButton
            ):
                return False

            focused = QApplication.focusWidget()
            if not focused or focused not in self._edits:
                return False

            clicked_inside_edit = obj is focused
            if (
                not clicked_inside_edit
                and isinstance(obj, QWidget)
                and hasattr(focused, "isAncestorOf")
            ):
                clicked_inside_edit = focused.isAncestorOf(obj)
            if clicked_inside_edit:
                return False

            same_window = False
            if isinstance(obj, QWidget) and hasattr(obj, "window"):
                same_window = obj.window() is self._window
            else:
                target_window = focused.window() if hasattr(focused, "window") else None
                if (
                    target_window
                    and hasattr(target_window, "windowHandle")
                    and target_window.windowHandle() is obj
                ):
                    same_window = True
            if same_window:
                focused.clearFocus()
                self._analysis_tab.setFocus()
        except (RuntimeError, TypeError, AttributeError):
            pass
        return False


class RangeInputFilter(QObject):
    """좌표축 범위 입력란에서 허용 키와 Tab 이동을 관리합니다."""

    def __init__(self, owner_window):
        super().__init__(owner_window)
        self._owner_window = owner_window

    ALLOWED_KEYS = frozenset(
        {
            Qt.Key.Key_0,
            Qt.Key.Key_1,
            Qt.Key.Key_2,
            Qt.Key.Key_3,
            Qt.Key.Key_4,
            Qt.Key.Key_5,
            Qt.Key.Key_6,
            Qt.Key.Key_7,
            Qt.Key.Key_8,
            Qt.Key.Key_9,
            Qt.Key.Key_Period,
            Qt.Key.Key_Minus,
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backtab,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }
    )

    def eventFilter(self, obj, event):
        if event.type() != QEvent.Type.KeyPress:
            return False

        key = event.key()
        modifiers = event.modifiers()
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            forward = key == Qt.Key.Key_Tab
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                forward = False
            tab_order = getattr(self._owner_window, "_range_tab_order", [])
            if obj in tab_order:
                current_idx = tab_order.index(obj)
                step = 1 if forward else -1
                next_widget = tab_order[(current_idx + step) % len(tab_order)]
                next_widget.setFocus(Qt.FocusReason.TabFocusReason)
                next_widget.selectAll()
            else:
                self._owner_window.focusNextPrevChild(forward)
            return True

        if modifiers & Qt.KeyboardModifier.ControlModifier and key in (
            Qt.Key.Key_A,
            Qt.Key.Key_C,
            Qt.Key.Key_V,
            Qt.Key.Key_X,
        ):
            return False
        if key in self.ALLOWED_KEYS:
            return False

        obj.clearFocus()
        return True
