from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from schemas import PostCreate
from db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions 
import shutil
import os
import uuid
import tempfile
from users import auth_backend, current_active_user, fastapi_users
from schemas import UserRead, UserCreate, UserUpdate
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
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
        # 1. Create a temporary file to store the upload
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
            
        # 2. Upload to ImageKit (Open the actual path, not the string "temp_file_path")
        with open(temp_file_path, "rb") as file_to_upload:
            upload_result = imagekit.upload_file(
                file=file_to_upload,
                file_name=file.filename,
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=["backend-upload"]
                )
            )
            
        # 3. Check if upload was successful (ImageKit usually returns 200)
        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                # Fixed typo: file.content_type (one 't')
                file_type="video" if file.content_type.startswith("video/") else "image",
                file_name=upload_result.name
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
        else:
            raise HTTPException(status_code=500, detail="Failed to upload to ImageKit")

    except Exception as e:
        # This block now correctly catches errors inside the 'try'
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # This block always runs to clean up files
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        await file.close() # Best practice to close the UploadFile

@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]
    
    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}
    
    posts_data = []
    for post in posts:
        posts_data.append({
            "id": str(post.id),
            "user_id": str(post.user_id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),
            "is_owner": post.user_id == user.id, 
            "email": user_dict.get(post.user_id, "unknown")
        })
    return {"posts": posts_data}

@app.delete("/post/{post_id}")
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user),):
    try:
        post_uuid = uuid.UUID(post_id)
        
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()
        
        if not post: 
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        await session.delete(post)
        await session.commit()
        
        return{"Success": True, "message": "post deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
      