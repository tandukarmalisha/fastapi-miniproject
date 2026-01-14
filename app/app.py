from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from schemas import CreatePost
from db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

text_posts = {
    1: {"title": "The Art of Coding", "content": "Exploring the beauty behind clean and efficient code."},
    2: {"title": "Morning Routine", "content": "How starting your day at 5 AM can double your productivity."},
    3: {"title": "Travel Tips", "content": "Top 10 hidden gems to visit in South East Asia this year."},
    4: {"title": "Healthy Living", "content": "A simple guide to meal prepping for a busy work week."},
    5: {"title": "Tech Trends 2026", "content": "What to expect from the next generation of AI and robotics."},
    6: {"title": "Minimalist Lifestyle", "content": "Decluttering your digital space for a clearer mind."},
    7: {"title": "Photography Basics", "content": "Mastering manual mode on your DSLR for better lighting."},
    8: {"title": "Financial Freedom", "content": "The basics of compound interest and early investing."},
    9: {"title": "Space Exploration", "content": "Recent discoveries on Mars that suggest ancient water flows."},
    10: {"title": "Home Gardening", "content": "The best indoor plants for low-light apartments."}
}

@app.get("/posts")
def get_all_posts(limit: int):
    if limit:
        return list(text_posts.values())[:limit]
    return text_posts

@app.get("/posts/{id}")
def get_post(id:int):
    if id not in text_posts:
        raise HTTPException(status_code=404, detail="post not found")
    return text_posts.get(id)

@app.post("/posts")
def create_post(post: CreatePost)-> CreatePost:
    new_post = {"title": post.title, "content": post.content}
    text_posts[len(text_posts)+1] = new_post
    return new_post

@app.delete("/post/{id}")
def delete_post(id: int):
    if id in text_posts:
       del text_posts[id]
       return {"message": "post deleted successfully"}
    raise HTTPException(status_code=404, detail="post not found")

