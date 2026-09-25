import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Union

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.course_catalog import COURSES, course_card

# =====================================================
# Configuration
# =====================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# =====================================================
# Load Knowledge Base
# =====================================================

def load_knowledge(path: Union[str, Path]) -> List[Dict]:
    try:
        with Path(path).open(encoding="utf-8") as knowledge_file:
            raw_data = json.load(knowledge_file)
    except (OSError, json.JSONDecodeError):
        return []

    entries = raw_data.get("entries", []) if isinstance(raw_data, dict) else raw_data
    if not isinstance(entries, list):
        return []

    required_fields = ("category", "title", "content", "keywords", "source")
    return [
        entry for entry in entries
        if isinstance(entry, dict)
        and all(field in entry for field in required_fields)
        and isinstance(entry["keywords"], list)
    ]


KNOWLEDGE = load_knowledge(BASE_DIR / "data" / "knowledge.json")
logger.info("Loaded %d knowledge documents.", len(KNOWLEDGE))
    

# =====================================================
# OpenRouter Client
# =====================================================

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1"
    )
)

MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "meta-llama/llama-3.3-70b-instruct"
)

# =====================================================
# System Prompt
# =====================================================

SYSTEM_PROMPT = """
You are NSDC AI Assistant.

You help Learners, Universities,
Training Partners and Employers.

Rules:

1. Answer ONLY using the provided context.
2. Never invent eligibility, fees or policies.
3. Use simple English.
4. Keep responses below 150 words.
5. Use bullet points whenever explaining steps.
6. Never ask for Aadhaar number, OTP or passwords.
7. If the answer is unavailable, clearly mention that the information is not available in the current NSDC knowledge base.
"""

# =====================================================
# Text Normalization
# =====================================================

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def find_course_cards(question: str) -> List[Dict[str, str]]:
    normalized = normalize(question)
    question_words = set(normalized.split())
    course_terms = ("course", "courses", "program", "programs", "browse", "recommend")
    course_topics = (
        "ai", "animation", "vfx", "film", "filmmaking", "acting", "music",
        "sound", "script", "editor", "creator", "influencer", "avatar", "ar",
        "vr", "design",
    )

    selected_topics = [topic for topic in course_topics if topic in question_words]
    has_category = bool(selected_topics)
    if not any(term in normalized for term in course_terms) and not has_category:
        return []

    matches = []
    for course in COURSES:
        title = normalize(course["title"])
        if not selected_topics or any(
            topic in title
            or topic == "animation" and "animator" in title
            or topic == "film" and "filmmaking" in title
            for topic in selected_topics
        ):
            matches.append(course)
    return [course_card(course) for course in matches[:6]]

# =====================================================
# Weighted Retrieval Engine
# =====================================================

def retrieve(question: str) -> List[Dict]:

    question = normalize(question)
    stop_words = {
        "a", "an", "and", "are", "can", "do", "for", "how", "i", "in",
        "is", "it", "me", "my", "of", "on", "or", "the", "to", "what",
        "with", "you", "your",
    }
    question_words = set(question.split()) - stop_words

    scored_docs = []

    for doc in KNOWLEDGE:

        score = 0

        title = normalize(doc.get("title", ""))
        category = normalize(doc.get("category", ""))
        content = normalize(doc.get("content", ""))


        keywords = doc.get("keywords", [])

        # ---------- Title ----------
        for word in question_words:
            if word in title:
                score += 5

        # ---------- Category ----------
        if category in question:
            score += 3

        # ---------- Keywords ----------
        for keyword in keywords:
            keyword = normalize(keyword)

            if keyword in question:
                score += 4

            elif any(word in keyword for word in question_words):
                score += 2

        # ---------- Content ----------
        for word in question_words:
            if word in content:
                score += 1

        if score > 0:
            scored_docs.append(
                {
                    "score": score,
                    "doc": doc
                }
            )

    scored_docs.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    logger.info(
        f"Retrieved {len(scored_docs[:3])} documents for '{question}'"
    )

    return [x["doc"] for x in scored_docs[:3]]

# =====================================================
# Build Context
# =====================================================

def build_context(docs: List[Dict]) -> str:

    sections = []

    for doc in docs:

        sections.append(
            f"""
Category: {doc.get('category', 'Unknown')}

Title: {doc.get('title', 'Untitled')}

Content:
{doc.get('content', '')}

Source:
{doc.get('source', 'Unknown')}

Page:
{doc.get('page', '')}
"""
        )

    return "\n\n".join(sections)

# =====================================================
# OpenRouter LLM
# =====================================================

async def ask_llm(question: str, docs: List[Dict]) -> str:

    context = build_context(docs)

    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
Context:

{context}

Question:

{question}
"""
            }
        ]
    )

    return response.choices[0].message.content

# =====================================================
# Main Chat Function
# =====================================================

async def get_response(question: str, category: str = None):

    course_cards = find_course_cards(question)
    if course_cards:
        category_label = course_cards[0]["category"] if len(course_cards) == 1 else "Courses"
        return {
            "answer": "Here are our Eros AIVidya programs. Open a course to explore its curriculum and career outcomes.",
            "source": "Eros AIVidya Course Catalogue",
            "page": "/courses",
            "category": category_label,
            "course_cards": course_cards,
        }

    if not KNOWLEDGE:
        return {
            "answer": "Knowledge base is currently unavailable.",
            "source": None,
            "page": None,
            "category": None
        }

    docs = retrieve(question)

    # Optional category filter
    if category:
        docs = [d for d in docs if d["category"].lower() == category.lower()] or docs

    if len(docs) == 0:
        return {
            "answer": "I couldn't find verified information for that in the current NSDC knowledge base.",
            "source": None,
            "page": None,
            "category": None
        }

    try:
        answer = await ask_llm(question, docs)

        top = docs[0]

        return {
            "answer": answer,
            "source": top["source"],
            "page": top["page"],
            "category": top["category"]
        }

    except Exception:
        logger.exception("OpenRouter Error")

        return {
            "answer": "The assistant is temporarily unavailable. Please try again shortly.",
            "source": None,
            "page": None,
            "category": None
        }