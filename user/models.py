from sqlalchemy import Column, String, DateTime, func, Integer, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
import uuid
import enum
from database import Base

# Import group_members for relationship
from group.models import group_members

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# User role enum
class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Users(Base):
    __tablename__ = 'users'

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    user_name = Column(String(255), unique=True, nullable=False)  # Unique username
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(255), nullable=False)

    # Role-based status instead of boolean
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)

    # Active status (account enabled/disabled)
    is_active = Column(SQLEnum('active', 'inactive', name='user_status'), default='active', nullable=False)

    password = Column(String(60), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owned_groups = relationship("Group", back_populates="owner")
    joined_groups = relationship("Group", secondary="group_members", back_populates="members")

    @staticmethod
    def verify_password(plain_password, hashed_password):
        """Verify if a plain password matches the hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        """Hash the password using bcrypt."""
        return pwd_context.hash(password)

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level"""
        role_hierarchy = {
            UserRole.STUDENT: 1,
            UserRole.TEACHER: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPERADMIN: 4
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)

    def is_admin_or_above(self) -> bool:
        """Check if user is admin or superadmin"""
        return self.role in [UserRole.ADMIN, UserRole.SUPERADMIN]