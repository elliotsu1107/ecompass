import sys
from pathlib import Path

from app.config import Config, data_root, project_root


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


def test_project_root_uses_pyinstaller_internal_resource_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ecompass.exe"), raising=False)
    (tmp_path / "_internal" / "app" / "web" / "static").mkdir(parents=True)

    assert project_root() == tmp_path / "_internal"
    assert data_root() == tmp_path


def test_config_reads_host_and_port_from_environment(monkeypatch):
    monkeypatch.setenv("ECOMPASS_HOST", "127.0.0.1")
    monkeypatch.setenv("ECOMPASS_PORT", "8101")

    settings = Config()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8101


def test_config_ignores_invalid_port_environment(monkeypatch):
    monkeypatch.setenv("ECOMPASS_PORT", "abc")

    assert Config().port == 8000

    monkeypatch.setenv("ECOMPASS_PORT", "70000")

    assert Config().port == 8000
