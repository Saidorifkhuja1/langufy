from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy import func
from database import get_db
from .models import Users, pwd_context, UserRole
from .schemas import UserCreate, UserAuth, UserBase, UserPassword
from fastapi.encoders import jsonable_encoder
from .jwt_auth import JWTAuth, JWTBearer
from fastapi.responses import JSONResponse

router = APIRouter()
jwt_auth = JWTAuth()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""

    # Count users (limit 3)
    result = await db.execute(select(func.count()).select_from(Users))
    user_count = result.scalar()
    if user_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is closed. Only 3 users are allowed.",
        )

    # Check if email exists
    result = await db.execute(select(Users).where(Users.email == user.email))
    if result.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Check if username exists
    result = await db.execute(select(Users).where(Users.user_name == user.user_name))
    if result.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken.",
        )

    # Hash password
    hashed_password = Users.get_password_hash(user.password)

    # Create new user
    new_user = Users(
        email=user.email,
        user_name=user.user_name,
        full_name=user.full_name,
        phone_number=user.phone_number,
        password=hashed_password,
        role=user.role,
        is_active='active',
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Generate JWT tokens
        tokens = JWTAuth().login_jwt(user_id=str(new_user.id))

        # Prepare user data (without password)
        user_data = jsonable_encoder(new_user)
        user_data.pop('password', None)

        return {
            "message": "User registered successfully.",
            "user": user_data,
            "tokens": tokens,
        }
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again later.",
        ) from e


@router.post('/user_login')
async def user_login(user_data: UserAuth, db: AsyncSession = Depends(get_db)):
    """Login with email and password"""

    result = await db.execute(select(Users).where(Users.email == user_data.email))
    user = result.scalar()

    # Check credentials
    if not user or not pwd_context.verify(user_data.password, user.password):
        return JSONResponse(
            content={"error": "Email or password incorrect"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if account is active
    if user.is_active == 'inactive':
        return JSONResponse(
            content={"error": "Account is disabled"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Generate JWT token
    jwt_token = JWTAuth().login_jwt(str(user.id))
    return jwt_token


@router.get('/user_detail', dependencies=[Depends(JWTBearer(JWTAuth()))])
async def user_detail(db: AsyncSession = Depends(get_db), jwt_token: str = Depends(JWTBearer(JWTAuth()))):
    """Get current user details"""

    decoded_token = JWTAuth().decode_token(jwt_token)
    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_uuid = decoded_token.get("user_id")
    result = await db.execute(select(Users).where(Users.id == user_uuid))
    user = result.scalar()

    if not user:
        return JSONResponse(
            content={"error": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Return user data without password
    user_data = user.__dict__
    user_data.pop("password", None)
    user_data.pop("_sa_instance_state", None)  # Remove SQLAlchemy internal state
    return user_data


@router.patch("/update_user", dependencies=[Depends(JWTBearer(JWTAuth()))])
async def update_user(user_data: UserBase, db: AsyncSession = Depends(get_db),
                      jwt_token: str = Depends(JWTBearer(JWTAuth()))):
    """Update current user information"""

    decoded_token = JWTAuth().decode_token(jwt_token)
    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_uuid = decoded_token.get("user_id")
    result = await db.execute(select(Users).where(Users.id == user_uuid))
    user = result.scalar()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness (if changing)
    if user_data.email != user.email:
        existing_user_result = await db.execute(select(Users).where(Users.email == user_data.email))
        existing_user = existing_user_result.scalar()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

    # Check username uniqueness (if changing)
    if user_data.user_name != user.user_name:
        existing_user_result = await db.execute(select(Users).where(Users.user_name == user_data.user_name))
        existing_user = existing_user_result.scalar()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Update user fields
    user.full_name = user_data.full_name
    user.phone_number = user_data.phone_number
    user.email = user_data.email
    user.user_name = user_data.user_name
    user.role = user_data.role

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Return updated user data
        user_dict = user.__dict__
        user_dict.pop("password", None)
        user_dict.pop("_sa_instance_state", None)
        return user_dict

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user. Please try again later."
        ) from e


@router.patch("/update_password", dependencies=[Depends(JWTBearer(JWTAuth()))])
async def update_password(user_data: UserPassword, db: AsyncSession = Depends(get_db),
                          jwt_token: str = Depends(JWTBearer(JWTAuth()))):
    """Change user password"""

    decoded_token = JWTAuth().decode_token(jwt_token)
    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_uuid = decoded_token.get("user_id")
    result = await db.execute(select(Users).where(Users.id == user_uuid))
    user = result.scalar()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify old password
    if not pwd_context.verify(user_data.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )

    # Hash new password
    new_hashed_password = pwd_context.hash(user_data.new_password)
    user.password = new_hashed_password

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"message": "Password updated successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again later."
        ) from e


@router.delete("/delete_user", dependencies=[Depends(JWTBearer(JWTAuth()))])
async def delete_user(db: AsyncSession = Depends(get_db), jwt_token: str = Depends(JWTBearer(JWTAuth()))):
    """Delete current user account"""

    decoded_token = JWTAuth().decode_token(jwt_token)
    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_uuid = decoded_token.get("user_id")
    result = await db.execute(select(Users).where(Users.id == user_uuid))
    user = result.scalar()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        await db.delete(user)
        await db.commit()
        return {"message": "User deleted successfully."}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user. Please try again later."
        ) from e