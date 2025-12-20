"""
JWT 인증 모듈
API 엔드포인트에서 사용할 JWT 검증 의존성을 제공합니다.
"""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
from dotenv import load_dotenv

from core.database import get_db
from models.user import User

load_dotenv()

security = HTTPBearer()

# JWT 설정
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    JWT 토큰을 검증하고 payload를 반환합니다.
    
    Args:
        credentials: HTTP Bearer 토큰
        
    Returns:
        dict: JWT payload (username 등의 정보 포함)
        
    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


def get_current_user(
    payload: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자를 반환합니다.
    
    Args:
        payload: JWT payload
        db: 데이터베이스 세션
        
    Returns:
        User: 현재 사용자 객체
        
    Raises:
        HTTPException: 사용자를 찾을 수 없는 경우
    """
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="토큰에 사용자 정보가 없습니다")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    return user
