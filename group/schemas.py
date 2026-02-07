from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupResponse(GroupBase):
    uid: UUID
    owner_id: UUID
    members_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupWithMembers(GroupResponse):
    members: List[dict]  # Basic user info for members

    class Config:
        from_attributes = True


class GroupMemberAdd(BaseModel):
    user_id: UUID


class GroupMemberRemove(BaseModel):
    user_id: UUID
