# routers/notification.py

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from ..database.mongodb import get_db
from ..core.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ======================================================
# CREATE NOTIFICATION (INTERNAL USE)
# ======================================================

async def create_notification(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    title: str,
    message: str,
    metadata: dict = None
):
    notification = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "metadata": metadata or {},
        "is_read": False,
        "created_at": datetime.utcnow()
    }

    await db["notifications"].insert_one(notification)


# ======================================================
# GET NOTIFICATIONS
# ======================================================

@router.get("/")
async def get_notifications(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_object_id = ObjectId(current_user["id"])

    notifications = await db["notifications"].find(
        {"user_id": user_object_id}
    ).sort("created_at", -1).to_list(50)

    result = []

    for n in notifications:
        result.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "message": n.get("message"),
            "metadata": n.get("metadata", {}),
            "is_read": n.get("is_read", False),
            "created_at": n.get("created_at")
        })

    return result


# ======================================================
# MARK SINGLE NOTIFICATION AS READ
# ======================================================

@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        notification_object_id = ObjectId(notification_id)
    except:
        raise HTTPException(400, "Invalid notification ID")

    user_object_id = ObjectId(current_user["id"])

    result = await db["notifications"].update_one(
        {
            "_id": notification_object_id,
            "user_id": user_object_id
        },
        {
            "$set": {"is_read": True}
        }
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Notification not found")

    return {"message": "Notification marked as read"}


# ======================================================
# MARK ALL AS READ
# ======================================================

@router.patch("/mark-all-read")
async def mark_all_read(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_object_id = ObjectId(current_user["id"])

    await db["notifications"].update_many(
        {"user_id": user_object_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

    return {"message": "All notifications marked as read"}


# ======================================================
# GET UNREAD COUNT
# ======================================================

@router.get("/unread-count")
async def get_unread_count(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_object_id = ObjectId(current_user["id"])

    count = await db["notifications"].count_documents({
        "user_id": user_object_id,
        "is_read": False
    })

    return {"unread_count": count}