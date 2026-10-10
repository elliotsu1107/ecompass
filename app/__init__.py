from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import Config, project_root
from .db import connect_db, init_db
from .security import CredentialStore, ensure_secret_key


def create_app(config: Config | None = None) -> FastAPI:
    settings = config or Config()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.archive_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.db_path)

    app = FastAPI(title="电商经营罗盘")
    app.state.config = settings
    app.state.data_dir = settings.data_dir
    app.state.db = lambda: connect_db(settings.db_path)
    app.state.secret_key = ensure_secret_key(settings.data_dir / "secret.key")
    app.state.credentials = CredentialStore(settings.data_dir / "admin.json")
    static_dir = project_root() / "app" / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    from .web.routes_admin import router as admin_router
    from .web.routes_dashboard import router as dashboard_router
    from .web.routes_import import router as import_router
    app.include_router(dashboard_router)
    app.include_router(admin_router)
    app.include_router(import_router)
    return app
