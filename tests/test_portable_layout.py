from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_script_declares_portable_pyinstaller_layout():
    script = (ROOT / "build_portable.ps1").read_text(encoding="utf-8")

    assert "--onedir" in script
    assert '"--name", "ecompass"' in script
    assert "app\\web\\templates;app\\web\\templates" in script
    assert "app\\web\\static;app\\web\\static" in script
    assert "app\\schema.sql;app" in script
    assert "dist/ecompass-portable/ecompass.exe" in script.replace("\\", "/")
    assert "ecompass-portable.zip" in script


def test_portable_package_contains_runtime_files_and_empty_import_directory():
    script = (ROOT / "build_portable.ps1").read_text(encoding="utf-8")

    assert "Copy-Item" in script
    assert "start.bat" in script
    assert "backup.bat" in script
    assert "README.txt" in script
    assert "data\\imports" in script or "data/imports" in script


def test_built_portable_package_contains_runtime_files_and_resources():
    package = ROOT / "dist" / "ecompass-portable"
    assert (package / "ecompass.exe").exists()
    assert (package / "start.bat").exists()
    assert (package / "backup.bat").exists()
    assert (package / "README.txt").exists()
    assert (package / "data" / "imports").is_dir()
    assert list(package.rglob("templates/*.html"))
    assert list(package.rglob("static/*"))

    start = (ROOT / "start.bat").read_text(encoding="utf-8")
    backup = (ROOT / "backup.bat").read_text(encoding="utf-8")

    assert "%~dp0" in start
    assert "ecompass.exe" in start
    assert "%~dp0" in backup
    assert "data" in backup


def test_portable_readme_and_build_requirements_exist():
    assert (ROOT / "portable" / "README.txt").exists()
    requirements = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")
    assert "pyinstaller" in requirements.lower()
