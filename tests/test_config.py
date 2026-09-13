import sys
from pathlib import Path

from app.config import Config, project_root


def test_config_uses_executable_parent_for_portable_data(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ecompass.exe"), raising=False)

    settings = Config()

    assert settings.data_dir == tmp_path / "data"


def test_config_uses_project_root_data_in_development(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    settings = Config()

    assert settings.data_dir == project_root() / "data"


def test_config_preserves_explicit_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ecompass.exe"), raising=False)
    explicit_dir = tmp_path / "custom-data"

    settings = Config(data_dir=explicit_dir)

    assert settings.data_dir == explicit_dir
