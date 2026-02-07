from sqlalchemy import Column, String, DateTime, func, Integer, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import uuid
from database import Base

# Association table for group members
group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', PGUUID(as_uuid=True), ForeignKey('groups.uid'), primary_key=True),
    Column('user_id', PGUUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)

# Export group_members for import in user models
__all__ = ['Group', 'group_members']


class Group(Base):
    __tablename__ = 'groups'

    uid = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Owner reference (teacher/admin/superadmin who created the group)
    owner_id = Column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Members count (calculated field)
    members_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("Users", back_populates="owned_groups")
    members = relationship("Users", secondary=group_members, back_populates="joined_groups")

    def is_owner(self, user_id: uuid.UUID) -> bool:
        """Check if user is the group owner"""
        return self.owner_id == user_id

    def is_member(self, user_id: uuid.UUID) -> bool:
        """Check if user is a member of the group"""
        return any(member.id == user_id for member in self.members)
