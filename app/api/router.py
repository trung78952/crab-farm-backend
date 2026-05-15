from fastapi import APIRouter, Depends

from app.api.v1 import (
    ai,
    auth,
    camera,
    detections,
    devices,
    harvest,
    motion,
    mqtt_console,
    mqtt_logs,
    recheck_tasks,
    scan_jobs,
    scan_schedules,
    scans,
    sensor_alert_rules,
    sensor_alerts,
    sensor_readings,
    sensor_types,
    sensors,
    shelves,
    tanks,
    training_samples,
)
from app.core.auth import get_current_user

api_router = APIRouter(prefix="/api/v1")
protected = [Depends(get_current_user)]

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(shelves.router, prefix="/shelves", tags=["shelves"], dependencies=protected)
api_router.include_router(tanks.router, prefix="/tanks", tags=["tanks"], dependencies=protected)
api_router.include_router(devices.router, prefix="/devices", tags=["devices"], dependencies=protected)
api_router.include_router(motion.router, prefix="/motion", tags=["motion"], dependencies=protected)
api_router.include_router(camera.router, prefix="/camera", tags=["camera"], dependencies=protected)
api_router.include_router(detections.router, prefix="/detections", tags=["detections"], dependencies=protected)
api_router.include_router(harvest.router, prefix="/harvest", tags=["harvest"], dependencies=protected)
api_router.include_router(scan_schedules.router, prefix="/scan-schedules", tags=["scan-schedules"], dependencies=protected)
api_router.include_router(scans.router, prefix="/scans", tags=["scans"], dependencies=protected)
api_router.include_router(scan_jobs.router, prefix="/scan-jobs", tags=["scan-jobs"], dependencies=protected)
api_router.include_router(sensor_types.router, prefix="/sensor-types", tags=["sensor-types"], dependencies=protected)
api_router.include_router(sensors.router, prefix="/sensors", tags=["sensors"], dependencies=protected)
api_router.include_router(sensor_readings.router, prefix="/sensor-readings", tags=["sensor-readings"], dependencies=protected)
api_router.include_router(sensor_alert_rules.router, prefix="/sensor-alert-rules", tags=["sensor-alert-rules"], dependencies=protected)
api_router.include_router(sensor_alerts.router, prefix="/sensor-alerts", tags=["sensor-alerts"], dependencies=protected)
api_router.include_router(recheck_tasks.router, prefix="/recheck-tasks", tags=["recheck-tasks"], dependencies=protected)
api_router.include_router(mqtt_logs.router, prefix="/mqtt-logs", tags=["mqtt-logs"], dependencies=protected)
api_router.include_router(mqtt_console.router, prefix="/mqtt", tags=["mqtt"], dependencies=protected)
api_router.include_router(ai.router, prefix="/ai", tags=["ai"], dependencies=protected)
api_router.include_router(training_samples.router, prefix="/training-samples", tags=["training-samples"], dependencies=protected)
api_router.include_router(training_samples.router, prefix="/datasets", tags=["datasets"], dependencies=protected)
