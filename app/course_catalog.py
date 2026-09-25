import json
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
COURSES_PATH = BASE_DIR / "data" / "courses.json"


def load_courses() -> List[Dict[str, Any]]:
    try:
        with COURSES_PATH.open(encoding="utf-8") as course_file:
            courses = json.load(course_file)
        return courses if isinstance(courses, list) else []
    except (OSError, json.JSONDecodeError):
        return []


COURSES = load_courses()
COURSES_BY_ID = {course["id"]: course for course in COURSES if course.get("id")}


def get_course(course_id: str) -> Optional[Dict[str, Any]]:
    return COURSES_BY_ID.get(course_id)


def course_card(course: Dict[str, Any]) -> Dict[str, str]:
    return {
        "id": course["id"],
        "title": course["title"],
        "duration": course["duration"],
        "category": course["category"],
        "level": course["level"],
    }
