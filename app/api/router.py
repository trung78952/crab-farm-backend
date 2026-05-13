from fastapi import APIRouter, Depends

from app.api.v1 import auth, camera, detections, devices, harvest, motion, mqtt_logs, scan_schedules, scans, tanks
from app.core.auth import get_current_user

api_router = APIRouter(prefix="/api/v1")
protected = [Depends(get_current_user)]

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tanks.router, prefix="/tanks", tags=["tanks"], dependencies=protected)
api_router.include_router(devices.router, prefix="/devices", tags=["devices"], dependencies=protected)
api_router.include_router(motion.router, prefix="/motion", tags=["motion"], dependencies=protected)
api_router.include_router(camera.router, prefix="/camera", tags=["camera"], dependencies=protected)
api_router.include_router(detections.router, prefix="/detections", tags=["detections"], dependencies=protected)
api_router.include_router(harvest.router, prefix="/harvest", tags=["harvest"], dependencies=protected)
api_router.include_router(scan_schedules.router, prefix="/scan-schedules", tags=["scan-schedules"], dependencies=protected)
api_router.include_router(scans.router, prefix="/scans", tags=["scans"], dependencies=protected)
api_router.include_router(mqtt_logs.router, prefix="/mqtt-logs", tags=["mqtt-logs"], dependencies=protected)
