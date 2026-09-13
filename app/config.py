import sys
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


@dataclass(slots=True)
class Config:
    data_dir: Path | None = None
    host: str = "0.0.0.0"
    port: int = 8000

    def __post_init__(self) -> None:
        if self.data_dir is None:
            self.data_dir = project_root() / "data"

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archive"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ecompass.db"
