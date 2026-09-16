import os
import sys
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        internal_root = Path(sys.executable).resolve().parent / "_internal"
        if internal_root.exists():
            return internal_root
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _port_from_env(default: int) -> int:
    raw = os.environ.get("ECOMPASS_PORT", "").strip()
    if not raw:
        return default
    try:
        port = int(raw)
    except ValueError:
        return default
    return port if 1 <= port <= 65535 else default


@dataclass(slots=True)
class Config:
    data_dir: Path | None = None
    host: str = "0.0.0.0"
    port: int = 8000

    def __post_init__(self) -> None:
        if self.data_dir is None:
            self.data_dir = data_root() / "data"
        self.host = os.environ.get("ECOMPASS_HOST", self.host)
        self.port = _port_from_env(self.port)

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archive"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ecompass.db"
