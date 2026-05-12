from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.mqtt import mqtt_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "raw").mkdir(parents=True, exist_ok=True)
    mqtt_manager.connect()
    yield
    mqtt_manager.disconnect()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(settings.public_storage_url, StaticFiles(directory=settings.storage_dir), name="storage")
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "mqtt_connected": mqtt_manager.connected}
