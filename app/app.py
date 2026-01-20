from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from contextlib import asynccontextmanager
import shutil, os, uuid, tempfile

from db import Post, User, create_db_and_tables, get_async_session
from users import auth_backend, current_active_user, fastapi_users
from schemas import UserRead, UserCreate, UserUpdate
from images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Allow Streamlit to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Routers
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

@app.post("/upload")
async def upload_post(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    temp_file_path = None
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.upload_file(
                file=f, file_name=file.filename,
                options=UploadFileRequestOptions(use_unique_file_name=True)
            )

        post = Post(
            user_id=user.id, caption=caption, url=upload_result.url,
            file_type="video" if file.content_type.startswith("video/") else "image",
            file_name=upload_result.name
        )
        session.add(post)
        await session.commit()
        return {"status": "success"}
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    # Using joinedload to fetch user details with the post
    result = await session.execute(
        select(Post).options(joinedload(Post.user)).order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    
    return {"posts": [{
        "id": str(p.id),
        "caption": p.caption,
        "url": p.url,
        "file_type": p.file_type,
        "email": p.user.email if p.user else "Unknown",
        "is_owner": p.user_id == user.id,
        "created_at": p.created_at.isoformat()
    } for p in posts]}

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    post_uuid = uuid.UUID(post_id)
    result = await session.execute(select(Post).where(Post.id == post_uuid))
    post = result.scalars().first()
    if post and post.user_id == user.id:
        await session.delete(post)
        await session.commit()
        return {"success": True}
    raise HTTPException(status_code=403)