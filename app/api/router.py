from fastapi import APIRouter

from app.api.v1 import camera, detections, devices, harvest, motion, tanks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tanks.router, prefix="/tanks", tags=["tanks"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(motion.router, prefix="/motion", tags=["motion"])
api_router.include_router(camera.router, prefix="/camera", tags=["camera"])
api_router.include_router(detections.router, prefix="/detections", tags=["detections"])
api_router.include_router(harvest.router, prefix="/harvest", tags=["harvest"])
