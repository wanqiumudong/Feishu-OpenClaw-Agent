from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    output_dir: Path
    reports_dir: Path
    provider: str = "mock"
    dry_run: bool = True
    real_write: bool = False
    lark_cli_bin: str = "lark-cli"
    feishu_doc_urls: tuple[str, ...] = ()
    feishu_minute_tokens: tuple[str, ...] = ()
    feishu_chat_id: str = ""
    feishu_send_as: str = "bot"
    feishu_tasklist_id: str = ""
    feishu_base_token: str = ""
    feishu_base_table_id: str = ""
    feishu_app_id: str = ""
    feishu_app_credential: str = ""
    feishu_encrypt_key: str = ""
    feishu_verification_token: str = ""
    reply_mode: str = "card"
    public_base_url: str = ""
    llm_enabled: bool = False
    llm_base_url: str = ""
    llm_model: str = "gemini-3.1-flash-lite-preview"
    llm_api_key: str = ""
    llm_timeout_s: int = 60

    @classmethod
    def default(cls) -> "Settings":
        root = Path(__file__).resolve().parents[1]
        return cls(
            project_root=root,
            data_dir=root / "data",
            output_dir=root / "outputs",
            reports_dir=root / "reports",
            provider=os.getenv("MEETINGFLOW_PROVIDER", "mock").strip().lower() or "mock",
            dry_run=_bool_env("MEETINGFLOW_DRY_RUN", default=True),
            real_write=_bool_env("MEETINGFLOW_REAL_WRITE", default=False),
            lark_cli_bin=os.getenv("LARK_CLI_BIN", "lark-cli").strip() or "lark-cli",
            feishu_doc_urls=_csv_env("FEISHU_DOC_URLS") or _csv_env("FEISHU_DOC_TEST_TOKEN"),
            feishu_minute_tokens=_csv_env("FEISHU_MINUTE_TOKENS") or _csv_env("FEISHU_MINUTES_TEST_TOKEN"),
            feishu_chat_id=os.getenv("FEISHU_CHAT_ID", "").strip(),
            feishu_send_as=os.getenv("FEISHU_SEND_AS", "bot").strip().lower() or "bot",
            feishu_tasklist_id=os.getenv("FEISHU_TASKLIST_ID", "").strip(),
            feishu_base_token=os.getenv("FEISHU_BASE_TOKEN", "").strip(),
            feishu_base_table_id=os.getenv("FEISHU_BASE_TABLE_ID", "").strip(),
            feishu_app_id=os.getenv("FEISHU_APP_ID", "").strip(),
            feishu_app_credential=os.getenv("FEISHU_APP_SECRET", "").strip(),
            feishu_encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", "").strip(),
            feishu_verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip(),
            reply_mode=os.getenv("MEETINGFLOW_REPLY_MODE", "card").strip().lower() or "card",
            public_base_url=os.getenv("MEETINGFLOW_PUBLIC_BASE_URL", "").strip(),
            llm_enabled=_bool_env("MEETINGFLOW_LLM_ENABLED", default=False),
            llm_base_url=(
                os.getenv("MEETINGFLOW_LLM_BASE_URL", "").strip()
                or os.getenv("TCAD_LLM_BASE_URL", "").strip()
            ),
            llm_model=(
                os.getenv("MEETINGFLOW_LLM_MODEL", "").strip()
                or os.getenv("TCAD_MODEL_MAIN", "").strip()
                or os.getenv("TCAD_LLM_MODEL", "").strip()
                or "gemini-3.1-flash-lite-preview"
            ),
            llm_api_key=(
                os.getenv("MEETINGFLOW_LLM_API_KEY", "").strip()
                or os.getenv("TCAD_LLM_API_KEY", "").strip()
                or os.getenv("WEB_FABGPT_OHMYGPT_API_KEY", "").strip()
            ),
            llm_timeout_s=int(os.getenv("MEETINGFLOW_LLM_TIMEOUT_S", "60")),
        )


def _bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")
    return tuple(part.strip() for part in raw_value.split(",") if part.strip())
