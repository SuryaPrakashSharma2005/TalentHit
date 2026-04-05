from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ..database.mongodb import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


@router.post("/register")
async def register_user(data: UserCreate):

    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = {
        "name": data.name,
        "email": data.email,
        "password": data.password,  # hash later
        "skills": [],
        "experience": 0,
        "resume_url": None,
        "created_at": datetime.utcnow()
    }

    result = await db.users.insert_one(user)

    return {
        "id": str(result.inserted_id),
        "name": data.name,
        "email": data.email
    }

@router.get("/{user_id}/applications")
async def get_user_applications(user_id: str):

    applications = await db.applications.find(
        {"user_id": user_id}
    ).to_list(100)

    for app in applications:
        app["_id"] = str(app["_id"])

    return applications