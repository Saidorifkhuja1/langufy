from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class CategoryResponse(CategoryBase):
    uid: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordsBase(BaseModel):
    uzbek: str = Field(..., min_length=1, max_length=255)
    english: str = Field(..., min_length=1, max_length=255)
    definition: Optional[str] = None
    category_uid: UUID


class WordsCreate(WordsBase):
    pass


class WordsUpdate(BaseModel):
    uzbek: Optional[str] = Field(None, min_length=1, max_length=255)
    english: Optional[str] = Field(None, min_length=1, max_length=255)
    definition: Optional[str] = None
    category_uid: Optional[UUID] = None


class WordsResponse(WordsBase):
    uid: UUID
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


class WordsWithCategory(WordsResponse):
    """Words with full category information"""
    category: CategoryResponse

    class Config:
        from_attributes = True

