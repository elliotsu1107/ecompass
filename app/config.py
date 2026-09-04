from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Config:
    data_dir: Path = Path("data")
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archive"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ecompass.db"
