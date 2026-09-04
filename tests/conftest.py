from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.config import Config


@pytest.fixture
def app_config(tmp_path: Path) -> Config:
    return Config(data_dir=tmp_path / "data", host="127.0.0.1", port=8000)


@pytest.fixture
def client(app_config: Config) -> TestClient:
    with TestClient(create_app(app_config)) as test_client:
        yield test_client


@pytest.fixture
def db_path(app_config: Config) -> Path:
    return app_config.db_path
