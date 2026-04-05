from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..database.mongodb import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db")
async def check_db(db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        # ping MongoDB
        await db.command("ping")
        return {"status": "MongoDB connected successfully ✅"}
    except Exception as e:
        return {"status": "MongoDB connection failed ❌", "error": str(e)}
