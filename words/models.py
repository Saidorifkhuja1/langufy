from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import uuid
from database import Base


class Category(Base):
    __tablename__ = 'categories'

    uid = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship with Words
    words = relationship("Words", back_populates="category")


class Words(Base):
    __tablename__ = 'words'

    uid = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    uzbek = Column(String(255), nullable=False)
    english = Column(String(255), nullable=False)
    definition = Column(Text, nullable=True)
    category_uid = Column(PGUUID(as_uuid=True), ForeignKey('categories.uid'), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship with Category
    category = relationship("Category", back_populates="words")




