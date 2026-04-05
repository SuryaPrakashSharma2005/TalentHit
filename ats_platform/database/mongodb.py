from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import logging

# ======================================================
# LOAD ENV VARIABLES
# ======================================================

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "ats_db")

if not MONGO_URL:
    raise ValueError("MONGO_URL is not set in environment variables")

# ======================================================
# CREATE CLIENT (Production Tuned)
# ======================================================

client = AsyncIOMotorClient(
    MONGO_URL,
    uuidRepresentation="standard",
    serverSelectionTimeoutMS=5000,
    maxPoolSize=50,
    minPoolSize=5,
    retryWrites=True
)

db = client[DB_NAME]


# ======================================================
# CONNECTION CHECK
# ======================================================

async def check_mongo_connection():
    try:
        await client.admin.command("ping")
        logging.info("✅ MongoDB connected successfully")
    except Exception as e:
        logging.error("❌ MongoDB connection failed")
        raise e


# ======================================================
# INDEX CREATION (CRITICAL FOR SCALE)
# ======================================================

async def create_indexes():
    try:
        # USERS
        await db["users"].create_index("email", unique=True, background=True)

        # CANDIDATES
        await db["candidates"].create_index("email", background=True)

        # JOBS
        await db["jobs"].create_index("company_id", background=True)
        await db["jobs"].create_index("status", background=True)
        await db["jobs"].create_index(
            [("company_id", 1), ("status", 1)],
            background=True
        )

        # APPLICATIONS
        await db["applications"].create_index("company_id", background=True)
        await db["applications"].create_index("candidate_id", background=True)
        await db["applications"].create_index("job_id", background=True)
        await db["applications"].create_index("stage", background=True)

        # 🔥 Prevent duplicate applications per job
        await db["applications"].create_index(
            [("job_id", 1), ("candidate_id", 1)],
            unique=True,
            background=True
        )

        # 🔥 Optimize dashboard queries
        await db["applications"].create_index(
            [("company_id", 1), ("stage", 1)],
            background=True
        )

        # NOTIFICATIONS
        await db["notifications"].create_index(
            [("user_id", 1), ("created_at", -1)],
            background=True
        )

        logging.info("✅ MongoDB indexes ensured")

    except Exception as e:
        logging.error(f"❌ Index creation failed: {str(e)}")
        raise e


# ======================================================
# DEPENDENCY
# ======================================================

async def get_db():
    yield db