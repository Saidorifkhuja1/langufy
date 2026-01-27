# category/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

from database import get_db
from .models import Category,Words
from .schemas import CategoryCreate, CategoryUpdate, CategoryResponse, WordsCreate, WordsUpdate, WordsResponse, WordsWithCategory

# Gemini API configuration
AI_API_TOKEN = os.getenv("AI_API_TOKEN")
AI_API_URL = os.getenv("AI_API_URL")
if not AI_API_TOKEN or not AI_API_URL:
    raise RuntimeError("AI_API_TOKEN or AI_API_URL is not set in .env file")

category_router = APIRouter(prefix="/categories", tags=["Categories"])
words_router = APIRouter(prefix="/words", tags=["Words"])


# CREATE
@category_router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(category_in: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(name=category_in.name)
    db.add(category)
    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    return category


# READ ALL
@category_router.get("/", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return categories


# READ ONE
@category_router.get("/{category_uid}", response_model=CategoryResponse)
async def get_category(category_uid: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.uid == category_uid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# UPDATE
@category_router.put("/{category_uid}", response_model=CategoryResponse)
async def update_category(category_uid: UUID, category_in: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.uid == category_uid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category_in.name is not None:
        category.name = category_in.name

    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    return category


# DELETE
@category_router.delete("/{category_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_uid: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.uid == category_uid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()
    return None




# CREATE
@words_router.post("/", response_model=WordsResponse, status_code=status.HTTP_201_CREATED)
async def create_word(word_in: WordsCreate, db: AsyncSession = Depends(get_db)):
    # Check if category exists
    result = await db.execute(select(Category).where(Category.uid == word_in.category_uid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    word = Words(
        uzbek=word_in.uzbek,
        english=word_in.english,
        definition=word_in.definition,
        category_uid=word_in.category_uid
    )
    db.add(word)
    await db.commit()
    await db.refresh(word)
    # Attach category info
    word.category = category
    return word


# READ ALL
@words_router.get("/", response_model=List[WordsWithCategory])
async def get_words(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Words).options(selectinload(Words.category))
    )
    return result.scalars().all()


# READ ONE
@words_router.get("/{word_uid}", response_model=WordsWithCategory)
async def get_word(word_uid: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Words)
        .where(Words.uid == word_uid)
        .options(selectinload(Words.category))
    )
    word = result.scalar_one_or_none()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return word


# UPDATE
@words_router.put("/{word_uid}", response_model=WordsWithCategory)
async def update_word(word_uid: UUID, word_in: WordsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Words).where(Words.uid == word_uid))
    word = result.scalar_one_or_none()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if word_in.uzbek is not None:
        word.uzbek = word_in.uzbek
    if word_in.english is not None:
        word.english = word_in.english
    if word_in.definition is not None:
        word.definition = word_in.definition
    if word_in.category_uid is not None:
        # Check if new category exists
        result = await db.execute(select(Category).where(Category.uid == word_in.category_uid))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        word.category_uid = word_in.category_uid

    await db.commit()
    await db.refresh(word)
    result = await db.execute(
        select(Words)
        .where(Words.uid == word_uid)
        .options(selectinload(Words.category))
    )
    return result.scalar_one()


# DELETE
@words_router.delete("/{word_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_word(word_uid: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Words).where(Words.uid == word_uid))
    word = result.scalar_one_or_none()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    await db.delete(word)
    await db.commit()
    return None

@category_router.get("/{category_uid}/words", response_model=List[WordsWithCategory])
async def get_words_by_category(category_uid: UUID, db: AsyncSession = Depends(get_db)):
    # Category mavjudligini tekshirish
    result = await db.execute(select(Category).where(Category.uid == category_uid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # So'zlarni olish
    result = await db.execute(
        select(Words)
        .where(Words.category_uid == category_uid)
        .options(selectinload(Words.category))
    )
    return result.scalars().all()


@words_router.get("/search/", response_model=List[WordsWithCategory])
async def search_words(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db)
):
    """
    Search words from database by English word
    """
    result = await db.execute(
        select(Words)
        .where(Words.english.ilike(f"%{q}%"))
        .options(selectinload(Words.category))
    )
    words = result.scalars().all()
    if words:
        return words

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{AI_API_URL}?key={AI_API_TOKEN}",
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"""
Explain the English word \"{q}\".
Return ONLY valid JSON in this format:

{{
  \"uzbek\": \"...\",
  \"definition\": \"...\"
}}
"""
                            }
                        ]
                    }
                ]
            }
        )

    if response.status_code != 200:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Gemini service error",
                "status_code": response.status_code,
                "response": error_payload,
            },
        )

    data = response.json()

    try:
        ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(ai_text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Invalid Gemini response format",
                "response": data,
            },
        )

    result = await db.execute(
        select(Category).where(Category.name == "Gemini Generated")
    )
    category = result.scalar_one_or_none()

    if not category:
        category = Category(name="Gemini Generated")
        db.add(category)
        await db.commit()
        await db.refresh(category)

    new_word = Words(
        english=q,
        uzbek=parsed.get("uzbek"),
        definition=parsed.get("definition"),
        category_uid=category.uid,
    )

    db.add(new_word)
    await db.commit()
    await db.refresh(new_word)

    new_word.category = category
    return [new_word]

