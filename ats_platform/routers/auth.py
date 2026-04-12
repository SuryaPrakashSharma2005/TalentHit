from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from jose import jwt, JWTError
import httpx
import os
import traceback

from ..database.mongodb import get_db
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from ..core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_SECRET = os.getenv("REFRESH_SECRET_KEY")

if not REFRESH_SECRET:
    raise ValueError("REFRESH_SECRET_KEY is not configured")


# ================= REGISTER =================

@router.post("/register")
async def register(payload: dict,
                   db: AsyncIOMotorDatabase = Depends(get_db)):

    email = payload.get("email")
    password = payload.get("password")
    role = payload.get("role")

    if not email or not password or not role:
        raise HTTPException(400, "Missing required fields")

    email = email.strip().lower()

    if role not in ["company", "applicant"]:
        raise HTTPException(400, "Invalid role")

    if len(password) < 6:
        raise HTTPException(400, "Password too short")

    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(400, "Email already exists")

    user = {
        "email": email,
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.utcnow()
    }

    result = await db["users"].insert_one(user)

    if role == "applicant":
        await db["candidates"].insert_one({
            "_id": result.inserted_id,
            "name": email.split("@")[0],
            "email": email,
            "skills": [],
            "experience_years": 0,
            "education": {},
            "created_at": datetime.utcnow()
        })

    access = create_access_token(str(result.inserted_id), role)
    refresh = create_refresh_token(str(result.inserted_id))

    return {
        "message": "Registered successfully",
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }


# ================= LOGIN =================

@router.post("/login")
async def login(payload: dict,
                db: AsyncIOMotorDatabase = Depends(get_db)):

    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise HTTPException(400, "Missing credentials")

    email = email.strip().lower()

    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not user.get("password"):
        raise HTTPException(400, "Use Google login")

    if not verify_password(password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token(str(user["_id"]), user["role"])
    refresh = create_refresh_token(str(user["_id"]))

    return {
        "message": "Login successful",
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "role": user["role"]
        }
    }


# ================= GOOGLE LOGIN =================

@router.post("/google")
async def google_login(payload: dict,
                       db: AsyncIOMotorDatabase = Depends(get_db)):

    access_token = payload.get("token")
    role = payload.get("role", "applicant")

    if not access_token:
        raise HTTPException(400, "Missing token")

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # 🔴 DEBUG
            print("GOOGLE STATUS:", r.status_code)
            print("GOOGLE RESPONSE TEXT:", r.text)

            if r.status_code != 200:
                raise HTTPException(400, f"Invalid Google token: {r.text}")

            # ✅ SAFE JSON PARSE
            try:
                idinfo = r.json()
            except Exception:
                traceback.print_exc() 
                raise HTTPException(400, "Google response is not valid JSON")

        # ✅ SAFE EMAIL
        email = idinfo.get("email")
        if not email:
            raise HTTPException(400, "Google account email not available")

        email = email.strip().lower()
        name = idinfo.get("name") or email.split("@")[0]

        user = await db["users"].find_one({"email": email})

        if not user:
            new_user = {
                "email": email,
                "name": name,
                "role": role,
                "google_id": idinfo.get("sub"),
                "created_at": datetime.utcnow()
            }
            result = await db["users"].insert_one(new_user)
            user_id = str(result.inserted_id)
        else:
            user_id = str(user["_id"])
            role = user["role"]

        access = create_access_token(user_id, role)
        refresh = create_refresh_token(user_id)

        return {
            "message": "Google login successful",
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "role": role
            }
        }

    except Exception as e:
        print("🔥 GOOGLE AUTH ERROR:", str(e))
        raise HTTPException(400, f"Google login failed: {str(e)}")

# ================= REFRESH =================

@router.post("/refresh")
async def refresh_token(request: Request,
                        db: AsyncIOMotorDatabase = Depends(get_db)):

    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "No refresh token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            REFRESH_SECRET,
            algorithms=["HS256"]
        )

        user_id = payload.get("sub")

        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(401, "User not found")

        access = create_access_token(str(user["_id"]), user["role"])

        return {
            "access_token": access,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")


# ================= LOGOUT =================

@router.post("/logout")
async def logout():
    return {"message": "Logged out"}


# ================= ME =================

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user