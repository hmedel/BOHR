from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db, User
from .config import settings
import hashlib
import bcrypt
import logging

logger = logging.getLogger(__name__)

# JWT secret leído del .env — nunca hardcodeado
SECRET_KEY = settings.JWT_SECRET_KEY
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY no está configurada en .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

def _prehash(password: str) -> bytes:
    """Pre-hash SHA-256 → 64 hex chars (< 72 bytes), elimina el límite de bcrypt."""
    return hashlib.sha256(password.encode()).hexdigest().encode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña: SHA-256 pre-hash + bcrypt con salt.
    Mantiene compatibilidad con hashes SHA-256 legacy (sin bcrypt).
    """
    # Hashes legacy: 64 chars hex, no empiezan con $2 (bcrypt)
    if len(hashed_password) == 64 and not hashed_password.startswith("$2"):
        logger.warning("Hash legacy SHA-256 detectado para login — se migrará a bcrypt en el próximo registro")
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
    return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode())

def get_password_hash(password: str) -> str:
    """Hash seguro: SHA-256 pre-hash + bcrypt con salt aleatorio."""
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
