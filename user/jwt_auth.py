import time
import jwt
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Request, Depends
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from .models import Users
from settings import settings


logger = logging.getLogger(__name__)


class JWTAuth:
    def __init__(self, secret_key: str = settings.SECRET_KEY, algorithm: str = settings.ALGORITHM,
                 access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES,
                 refresh_token_expire_minutes: int = settings.REFRESH_TOKEN_EXPIRE_MINUTES):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_minutes = refresh_token_expire_minutes

    def login_jwt(self, user_id: str):

        access_payload = {
            "user_id": user_id,
            "expire": time.time() + self.access_token_expire_minutes
        }
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)



        refresh_payload = {
            "user_id": user_id,
            "expire": time.time() + self.refresh_token_expire_minutes
        }
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        }

    def new_refresh_token(self, user_id: str, role: str, expire_time: float):
        new_access_token = jwt.encode(
            {"user_id": user_id, "role": role, "expire": expire_time},
            self.secret_key,
            algorithm=self.algorithm,
        )

        return {"access_token": new_access_token, "token_type": "Bearer"}

    def decode_token(self, token: str):
        try:
            decoded_token = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if decoded_token["expire"] >= time.time():
                return decoded_token
        except Exception as err:
            logger.info(err)
            pass


class JWTBearer(HTTPBearer):
    def __init__(self, jwt_auth: JWTAuth, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.jwt_auth = jwt_auth
        self.credentials_exception = HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            logger.debug(f"Credentials are provided: {credentials}")
            if credentials.scheme != "Bearer":
                logger.debug("Scheme is not Bearer")
                raise self.credentials_exception

            if not self.verify_jwt(credentials.credentials):
                logger.debug("Token verification failed")
                raise self.credentials_exception

            return credentials.credentials
        else:
            logger.debug("Credentials are not provided")
            raise self.credentials_exception

    def verify_jwt(self, jwt_token: str):
        payload = self.jwt_auth.decode_token(jwt_token)
        if payload:
            logger.info("Payload is valid")
            return True
        else:
            logger.debug("Payload is not valid")
            return False


async def get_current_user(
    token: str = Depends(JWTBearer(JWTAuth())),
    db: AsyncSession = Depends(get_db)
) -> Users:
    """Get current authenticated user from JWT token"""
    try:
        # Decode token
        jwt_auth = JWTAuth()
        payload = jwt_auth.decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user ID from payload
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user from database
        result = await db.execute(select(Users).where(Users.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if user.is_active == 'inactive':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )