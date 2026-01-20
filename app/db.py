import uuid
from datetime import datetime
from collections.abc import AsyncGenerator

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, relationship # Added relationship
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from fastapi import Depends

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# ✅ Base
class Base(DeclarativeBase):
    pass

# ✅ User Model
class User(SQLAlchemyBaseUserTableUUID, Base):
    # Added relationship back to Post
    posts = relationship("Post", back_populates="user")

# ✅ Post Model
class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Ensure this matches the table name of the User model (usually "user")
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(String(500))
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Corrected the 'argument:' syntax error
    user = relationship("User", back_populates="posts")

# ✅ Engine & Session (Keep these at the top level, NOT inside classes)
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False
)

# ✅ DB Creation Helper
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ✅ Dependencies
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)