from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not configured")

if not REFRESH_SECRET_KEY:
    raise ValueError("REFRESH_SECRET_KEY is not configured")

ACCESS_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


# ======================================================
# PASSWORD UTILITIES
# ======================================================

def hash_password(password: str) -> str:
    password = str(password).strip()
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)


# ======================================================
# TOKEN GENERATION
# ======================================================

def create_access_token(user_id: str, role: str):
    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",        # ✅ token type protection
        "iat": now,              # ✅ issued at
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str):
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "type": "refresh",       # ✅ token type protection
        "iat": now,
        "exp": expire
    }

    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)