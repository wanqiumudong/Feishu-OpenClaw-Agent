from typing import Any

from config import Settings


class FeishuSdkProvider:
    """Optional Feishu SDK adapter for event and card integration boundaries."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._sdk = self._load_sdk()

    @property
    def available(self) -> bool:
        return self._sdk is not None and bool(self.settings.feishu_app_id and self.settings.feishu_app_credential)

    def status(self) -> dict[str, Any]:
        return {
            "sdk_imported": self._sdk is not None,
            "app_configured": bool(self.settings.feishu_app_id and self.settings.feishu_app_credential),
            "event_security_configured": bool(self.settings.feishu_encrypt_key or self.settings.feishu_verification_token),
            "dry_run": self.settings.dry_run or not self.settings.real_write,
        }

    @staticmethod
    def _load_sdk() -> Any | None:
        try:
            import lark_oapi  # type: ignore
        except Exception:
            return None
        return lark_oapi
