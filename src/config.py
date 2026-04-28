from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    output_dir: Path

    @classmethod
    def default(cls) -> "Settings":
        root = Path(__file__).resolve().parents[1]
        return cls(
            project_root=root,
            data_dir=root / "data",
            output_dir=root / "outputs",
        )
