from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from jose import jwt
import random
import os
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models.models import User
from app.utils.email_service import send_otp_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
# Use pbkdf2_sha256 as the long-password-safe default.
# Keep bcrypt in the schemes list so existing bcrypt hashes can still be verified.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key_change_in_production")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_admin_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or insufficient permissions",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role != "admin":
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

class EmailRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class SetPasswordRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/request-otp")
async def request_otp(payload: EmailRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    otp_code = str(random.randint(100000, 999999))
    
    if not user:
        user = User(
            email=payload.email,
            password_hash="",
            is_verified=False,
            otp_code=otp_code
        )
        db.add(user)
    else:
        user.otp_code = otp_code
        
    await db.commit()
    
    send_otp_email(payload.email, otp_code)
    
    return {"status": "SUCCESS", "message": "OTP sent to email"}

@router.post("/forgot-password-otp")
async def forgot_password_otp(payload: EmailRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # 404 indicates user doesn't exist; frontend will catch this and redirect to Create Account
        raise HTTPException(status_code=404, detail="Account not found. Please create an account.")
        
    otp_code = str(random.randint(100000, 999999))
    user.otp_code = otp_code
    await db.commit()
    
    send_otp_email(payload.email, otp_code)
    
    return {"status": "SUCCESS", "message": "OTP sent to email"}
@router.post("/verify-otp")
async def verify_otp(payload: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or user.otp_code != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    user.otp_code = None
    user.is_verified = True
    await db.commit()
    
    return {"status": "SUCCESS", "message": "OTP verified successfully"}

@router.post("/set-password")
async def set_password(payload: SetPasswordRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_verified:
        raise HTTPException(status_code=400, detail="User not verified")
        
    user.password_hash = pwd_context.hash(payload.password)
    await db.commit()
    
    return {"status": "SUCCESS", "message": "Password set successfully. You can now login."}

@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
        
    if user.approval_status == "PENDING":
        raise HTTPException(status_code=403, detail="Your account is awaiting Admin approval.")
    elif user.approval_status == "REJECTED":
        raise HTTPException(status_code=403, detail="Your account access has been rejected by the Admin.")
    elif user.approval_status == "PAUSED":
        raise HTTPException(status_code=403, detail="Your account access is currently paused by the Admin.")
        
    access_token = jwt.encode(
        {"sub": user.email, "role": user.role.value, "exp": datetime.utcnow() + timedelta(hours=24)}, 
        SECRET_KEY, 
        algorithm=ALGORITHM
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "role": user.role.value}}
