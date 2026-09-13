import uvicorn

from app.config import Config


if __name__ == "__main__":
    settings = Config()
    uvicorn.run(
        "app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
