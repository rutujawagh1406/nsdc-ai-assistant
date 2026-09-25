from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.chatbot import get_response
from app.course_catalog import COURSES, get_course

app = FastAPI(title="EROS AI Vidya")

BASE_DIR = Path(__file__).resolve().parent.parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

class ChatRequest(BaseModel):
    message: str
    category: Optional[str] = None


# ---------- HOME ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# ---------- COURSES ----------
@app.get("/courses", response_class=HTMLResponse)
async def courses(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="courses.html",
        context={"courses": COURSES}
    )


# ---------- COURSE DETAIL ----------
@app.get("/course/{course_id}", response_class=HTMLResponse)
async def course_detail(request: Request, course_id: str):
    course = get_course(course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return templates.TemplateResponse(
        request=request,
        name="course_detail.html",
        context={"course": course}
    )


# ---------- HEALTH ----------
@app.get("/health")
async def health():
    return {"status": "running"}


# ---------- CHAT ----------
@app.post("/chat")
async def chat(data: ChatRequest):
    return await get_response(data.message, data.category)