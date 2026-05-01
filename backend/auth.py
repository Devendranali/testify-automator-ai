from datetime import datetime, timedelta
import os
from jose import jwt

# IMPORTANT: This secret key must be provided via environment variable.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or not SECRET_KEY.strip():
    raise RuntimeError("JWT_SECRET_KEY is required for JWT signing and validation.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
