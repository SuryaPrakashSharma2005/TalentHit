from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError
from bson import ObjectId
import os

from ..database.mongodb import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not configured")


async def get_current_user(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # ✅ Read token from Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        # ============================
        # STRICT PAYLOAD VALIDATION
        # ============================

        user_id = payload.get("sub")
        token_role = payload.get("role")
        token_type = payload.get("type")

        if not user_id or not token_role or not token_type:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # 🔒 Ensure only ACCESS tokens are allowed here
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Validate ObjectId safely
        try:
            object_id = ObjectId(user_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid user ID")

        user = await db["users"].find_one({"_id": object_id})

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # 🔒 Prevent role tampering
        if user["role"] != token_role:
            raise HTTPException(status_code=401, detail="Token role mismatch")

        return {
            "id": str(user["_id"]),
            "role": user["role"]
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")