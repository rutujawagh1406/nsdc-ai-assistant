from pathlib import Path

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.chatbot import get_response 
from app.course_catalog import get_course, load_courses



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger(__name__)

# ----------------------------------------------------
# App Configuration
# ----------------------------------------------------

app = FastAPI(title="NSDC AI Assistant")

BASE_DIR = Path(__file__).resolve().parent.parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# ----------------------------------------------------
# Request Schema
# ----------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    category: Optional[str] = None

# ----------------------------------------------------
# Routes
# ----------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/health")
async def health():
    return {
        "status": "running",
        "project": "NSDC AI Assistant V1"
    }

@app.post("/chat")
async def chat(data: ChatRequest):
    return await get_response(data.message, data.category)

@app.get("/courses", response_class=HTMLResponse)
async def courses(request: Request):
    return templates.TemplateResponse(
        "courses.html",
        {"request": request, "courses": load_courses()},
    )

@app.get("/course/{course_id}", response_class=HTMLResponse)
async def course_detail(request: Request, course_id: str):
    course = get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return templates.TemplateResponse(
        "course_detail.html",
        {"request": request, "course": course},
    )