# update_manager.py

import json
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

import config
import app_logger


class UpdateManager(QObject):
    """
    GitHub API를 통해 최신 버전을 확인하고 업데이트 알림을 관리합니다.
    점심(12시) 기준 하루 1회 확인 로직을 포함합니다.
    """

    update_available = Signal(
        str, str, str
    )  # latest_version, download_url, release_notes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
        self.reply = None

    def check_for_updates(self, current_version, last_check_str=None):
        """
        업데이트 필요 여부를 확인합니다.
        last_check_str: ISO 형식의 마지막 확인 일시 문자열
        """
        now = datetime.now()
        last_check = None
        if last_check_str:
            try:
                last_check = datetime.fromisoformat(last_check_str)
            except Exception:
                app_logger.debug(
                    f"[UpdateManager] Invalid last_check format: {last_check_str}"
                )

        if not self._should_check_now(now, last_check):
            app_logger.debug(
                "[UpdateManager] Skipping update check (already checked within the current 12:00 PM cycle)."
            )
            return False

        app_logger.debug(
            f"[UpdateManager] Starting update check via GitHub API: {config.GITHUB_API_LATEST_RELEASE}"
        )

        request = QNetworkRequest(QUrl(config.GITHUB_API_LATEST_RELEASE))
        # GitHub API는 User-Agent를 권장함
        request.setRawHeader(b"User-Agent", b"GichanFormant-App")

        self.reply = self.network_manager.get(request)
        self.reply.finished.connect(
            lambda: self._on_check_finished(current_version, now)
        )
        return True

    def _should_check_now(self, now, last_check):
        """정오(12시) 기준으로 새로운 확인 주기가 시작되었는지 검사합니다."""
        if last_check is None:
            return True

        today_12 = now.replace(hour=12, minute=0, second=0, microsecond=0)
        # 현재가 12시 이전이면 기준은 '어제의 12시', 12시 이후면 '오늘의 12시'
        threshold = today_12 if now >= today_12 else today_12 - timedelta(days=1)

        return last_check < threshold

    def _on_check_finished(self, current_version, check_time):
        """API 응답 결과를 처리합니다."""
        try:
            if self.reply.error() != QNetworkReply.NetworkError.NoError:
                app_logger.debug(
                    f"[UpdateManager] Network error or no release found: {self.reply.errorString()}"
                )
                return

            data = json.loads(self.reply.readAll().data().decode("utf-8"))
            latest_tag = data.get("tag_name", "").strip()
            # 'v2.3.4' 형식을 '2.3.4'로 정규화
            latest_version = latest_tag.lstrip("vV")
            html_url = data.get("html_url", config.GITHUB_RELEASE_URL)
            body = data.get("body", "")

            app_logger.debug(
                f"[UpdateManager] Current: {current_version}, Latest: {latest_version}"
            )

            if self._is_newer(current_version, latest_version):
                app_logger.debug("[UpdateManager] New version detected!")
                self.update_available.emit(latest_version, html_url, body)

        except Exception as e:
            app_logger.debug(
                f"[UpdateManager] Failed to parsing GitHub API response: {e}"
            )
        finally:
            # 성공 여부와 상관없이 '확인 시도' 자체를 기록하여 반복 체크 방지
            if hasattr(self, "on_success_callback"):
                self.on_success_callback(check_time.isoformat())
            self.reply.deleteLater()

    def _is_newer(self, current, latest):
        """지능형 버전 비교 (2.3.4.1 > 2.3.4 지원)"""
        try:
            c_parts = [int(p) for p in current.split(".") if p.strip().isdigit()]
            l_parts = [int(p) for p in latest.split(".") if p.strip().isdigit()]

            for i in range(max(len(c_parts), len(l_parts))):
                cv = c_parts[i] if i < len(c_parts) else 0
                lv = l_parts[i] if i < len(l_parts) else 0
                if lv > cv:
                    return True
                if lv < cv:
                    return False
            return False
        except Exception:
            # 파싱 실패 시 보수적으로 동일 버전으로 간주
            return False
