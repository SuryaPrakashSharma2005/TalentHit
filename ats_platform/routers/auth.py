from fastapi import APIRouter, Depends, HTTPException, Response, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from jose import jwt, JWTError
import httpx
import os

from ..database.mongodb import get_db
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from ..core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ================= ENV CONFIG =================

IS_PRODUCTION = True

COOKIE_SECURE = True if IS_PRODUCTION else False
COOKIE_SAMESITE = "none" if IS_PRODUCTION else "lax"

REFRESH_SECRET = os.getenv("REFRESH_SECRET_KEY")

if not REFRESH_SECRET:
    raise ValueError("REFRESH_SECRET_KEY is not configured")


# ================= COOKIE HANDLER =================

def set_auth_cookies(response: Response, access: str, refresh: str | None = None):
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite=False,
        domain=".talenthit.in",
        max_age=60 * 60 * 24,
        path="/"
    )

    if refresh:
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=60 * 60 * 7,
            path="/"
        )


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ================= REGISTER =================

@router.post("/register")
async def register(payload: dict,
                   response: Response,
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
        raise HTTPException(400, "Password must be at least 6 characters")

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

    set_auth_cookies(response, access, refresh)

    return {"message": "Registered successfully"}


# ================= LOGIN =================

@router.post("/login")
async def login(payload: dict,
                response: Response,
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
        raise HTTPException(400, "Use Google login for this account")

    if not verify_password(password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token(str(user["_id"]), user["role"])
    refresh = create_refresh_token(str(user["_id"]))

    set_auth_cookies(response, access, refresh)

    return {"message": "Login successful"}


# ================= GOOGLE LOGIN =================

@router.post("/google")
async def google_login(payload: dict,
                       response: Response,
                       db: AsyncIOMotorDatabase = Depends(get_db)):

    access_token = payload.get("token")
    role = payload.get("role", "applicant")

    if not access_token:
        raise HTTPException(400, "Missing token")

    if role not in ["company", "applicant"]:
        role = "applicant"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if r.status_code != 200:
                raise HTTPException(400, "Invalid Google token")
            idinfo = r.json()

        email = idinfo.get("email", "").strip().lower()
        name = idinfo.get("name", email.split("@")[0])

        if not email:
            raise HTTPException(400, "Could not get email from Google")

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

            if role == "applicant":
                await db["candidates"].insert_one({
                    "_id": result.inserted_id,
                    "name": name,
                    "email": email,
                    "skills": [],
                    "experience_years": 0,
                    "education": {},
                    "created_at": datetime.utcnow()
                })
        else:
            user_id = str(user["_id"])
            role = user["role"]

        access = create_access_token(user_id, role)
        refresh = create_refresh_token(user_id)

        set_auth_cookies(response, access, refresh)

        return {"message": "Google login successful"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Google login failed: {str(e)}")


# ================= REFRESH =================

@router.post("/refresh")
async def refresh_token(request: Request,
                        response: Response,
                        db: AsyncIOMotorDatabase = Depends(get_db)):

    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(401, "No refresh token")

    try:
        payload = jwt.decode(
            token,
            REFRESH_SECRET,
            algorithms=["HS256"]
        )

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise HTTPException(401, "Invalid refresh token")

        try:
            object_id = ObjectId(user_id)
        except:
            raise HTTPException(401, "Invalid user ID")

        user = await db["users"].find_one({"_id": object_id})
        if not user:
            raise HTTPException(401, "User not found")

        access = create_access_token(str(user["_id"]), user["role"])

        set_auth_cookies(response, access)

        return {"message": "Token refreshed"}

    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")


# ================= LOGOUT =================

@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logged out"}


# ================= ME =================

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user