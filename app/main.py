from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.mqtt import mqtt_manager
from app.services.scan_scheduler import scan_scheduler
from app.services.scan_runner_service import scan_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "raw").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "detected").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "datasets").mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "models").mkdir(parents=True, exist_ok=True)
    mqtt_manager.connect()
    scan_scheduler.start()
    scan_runner.start()
    yield
    await scan_runner.stop()
    await scan_scheduler.stop()
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
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mqtt_connected": mqtt_manager.connected,
        "simulation_mode": settings.simulation_mode,
        "ai_mock_mode": settings.ai_mock_mode,
    }
