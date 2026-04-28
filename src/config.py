from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    output_dir: Path
    provider: str = "mock"
    dry_run: bool = True
    lark_cli_bin: str = "lark-cli"
    feishu_doc_test_token: str = ""
    feishu_minutes_test_token: str = ""

    @classmethod
    def default(cls) -> "Settings":
        root = Path(__file__).resolve().parents[1]
        return cls(
            project_root=root,
            data_dir=root / "data",
            output_dir=root / "outputs",
            provider=os.getenv("MEETINGFLOW_PROVIDER", "mock"),
            dry_run=_bool_env("MEETINGFLOW_DRY_RUN", default=True),
            lark_cli_bin=os.getenv("LARK_CLI_BIN", "lark-cli"),
            feishu_doc_test_token=os.getenv("FEISHU_DOC_TEST_TOKEN", ""),
            feishu_minutes_test_token=os.getenv("FEISHU_MINUTES_TEST_TOKEN", ""),
        )


def _bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
