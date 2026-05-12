from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.motion import GCodeRequest, MotionCommandRead, MoveToTankRequest
from app.services import motion_service

router = APIRouter()


@router.post("/home", response_model=MotionCommandRead)
async def home(db: AsyncSession = Depends(get_db)):
    return await motion_service.home(db)


@router.post("/move-to-tank/{tank_id}", response_model=MotionCommandRead)
async def move_to_tank(tank_id: UUID, data: MoveToTankRequest | None = None, db: AsyncSession = Depends(get_db)):
    speed = data.speed if data is not None else 3000
    return await motion_service.move_to_tank(db, tank_id, speed=speed)


@router.post("/gcode", response_model=MotionCommandRead)
async def gcode(data: GCodeRequest, db: AsyncSession = Depends(get_db)):
    return await motion_service.send_gcode(db, data)


@router.post("/emergency-stop", response_model=MotionCommandRead)
async def emergency_stop(db: AsyncSession = Depends(get_db)):
    return await motion_service.emergency_stop(db)


@router.get("/commands", response_model=list[MotionCommandRead])
async def list_commands(db: AsyncSession = Depends(get_db)):
    return await motion_service.list_commands(db)


@router.get("/commands/{cmd_id}", response_model=MotionCommandRead)
async def get_command(cmd_id: str, db: AsyncSession = Depends(get_db)):
    return await motion_service.get_command_by_cmd_id(db, cmd_id)
