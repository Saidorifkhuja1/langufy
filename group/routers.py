from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from database import get_db
from user.models import Users, UserRole
from .models import Group, group_members
from .schemas import GroupCreate, GroupUpdate, GroupResponse, GroupWithMembers, GroupMemberAdd, GroupMemberRemove


# Import get_current_user here to avoid circular imports
def get_current_user_dependency():
    from user.jwt_auth import get_current_user
    return get_current_user

group_router = APIRouter(prefix="/groups", tags=["Groups"])


async def check_teacher_or_admin(current_user: Users):
    """Check if user has teacher, admin, or superadmin role"""
    if not current_user.has_permission(UserRole.TEACHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers, admins, and superadmins can create groups"
        )


async def check_group_access(group_id: UUID, current_user: Users, db: AsyncSession):
    """Check if user can access the group (owner or member)"""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.members))
        .where(Group.uid == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if user is owner or member
    if not (group.is_owner(current_user.id) or group.is_member(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this group"
        )
    
    return group


async def check_group_ownership(group_id: UUID, current_user: Users, db: AsyncSession):
    """Check if user is the group owner"""
    result = await db.execute(select(Group).where(Group.uid == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if not group.is_owner(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owner can perform this action"
        )
    
    return group


# CREATE Group (only teacher/admin/superadmin)
@group_router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: GroupCreate,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    await check_teacher_or_admin(current_user)
    
    group = Group(
        name=group_in.name,
        description=group_in.description,
        owner_id=current_user.id
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return group


# READ ALL Groups (only groups where user is member)
@group_router.get("/", response_model=List[GroupResponse])
async def get_user_groups(
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.members))
        .where(
            (Group.owner_id == current_user.id) |
            (Group.members.any(id=current_user.id))
        )
    )
    groups = result.scalars().all()
    return groups


# READ ONE Group
@group_router.get("/{group_uid}", response_model=GroupWithMembers)
async def get_group(
    group_uid: UUID,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    group = await check_group_access(group_uid, current_user, db)
    
    # Load members with basic info
    result = await db.execute(
        select(Users).where(Users.id.in_([member.id for member in group.members]))
    )
    members = result.scalars().all()
    
    return {
        **group.__dict__,
        "members": [{"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role} for m in members]
    }


# UPDATE Group (only owner)
@group_router.put("/{group_uid}", response_model=GroupResponse)
async def update_group(
    group_uid: UUID,
    group_in: GroupUpdate,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    group = await check_group_ownership(group_uid, current_user, db)
    
    if group_in.name is not None:
        group.name = group_in.name
    if group_in.description is not None:
        group.description = group_in.description
    
    await db.commit()
    await db.refresh(group)
    
    return group


# DELETE Group (only owner)
@group_router.delete("/{group_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_uid: UUID,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    group = await check_group_ownership(group_uid, current_user, db)
    
    await db.delete(group)
    await db.commit()
    
    return None


# ADD MEMBER (only owner)
@group_router.post("/{group_uid}/members", response_model=GroupResponse)
async def add_member(
    group_uid: UUID,
    member_in: GroupMemberAdd,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    group = await check_group_ownership(group_uid, current_user, db)
    
    # Check if user exists
    result = await db.execute(select(Users).where(Users.id == member_in.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a member
    if group.is_member(member_in.user_id):
        raise HTTPException(status_code=400, detail="User is already a member")
    
    # Add member
    group.members.append(user)
    group.members_count = len(group.members)
    
    await db.commit()
    await db.refresh(group)
    
    return group


# REMOVE MEMBER (only owner)
@group_router.delete("/{group_uid}/members", response_model=GroupResponse)
async def remove_member(
    group_uid: UUID,
    member_in: GroupMemberRemove,
    current_user: Users = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db)
):
    group = await check_group_ownership(group_uid, current_user, db)
    
    # Check if user is a member
    if not group.is_member(member_in.user_id):
        raise HTTPException(status_code=404, detail="User is not a member")
    
    # Remove member
    group.members = [m for m in group.members if m.id != member_in.user_id]
    group.members_count = len(group.members)
    
    await db.commit()
    await db.refresh(group)
    
    return group
