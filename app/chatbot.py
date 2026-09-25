import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List

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

try:
    with open(BASE_DIR / "data" / "knowledge.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)

        #Supports both old and new formats of knowledge.json
        if isinstance(raw_data, dict):
            KNOWLEDGE = raw_data.get("entries", [])
        elif isinstance(raw_data, list):
            KNOWLEDGE = raw_data
        else: 
            KNOWLEDGE = []

    logger.info(f"Loaded {len(KNOWLEDGE)} knowledge documents.")

except Exception as e:
    logger.exception("Failed to load knowledge base.")
    KNOWLEDGE = []
    

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
    course_terms = ("course", "courses", "program", "programs", "browse", "recommend")
    category_terms = {
        "ai": "Artificial Intelligence",
        "artificial intelligence": "Artificial Intelligence",
        "animation": "Animation",
        "vfx": "Animation",
        "filmmaking": "Filmmaking",
        "film": "Filmmaking",
        "creative technology": "Creative Technology",
        "design": "Creative Technology",
        "digital skills": "Digital Skills",
        "web development": "Digital Skills",
    }

    has_category = any(term in normalized for term in category_terms)
    if not any(term in normalized for term in course_terms) and not has_category:
        return []

    selected_categories = {
        category for term, category in category_terms.items() if term in normalized
    }
    matches = [
        course for course in COURSES
        if not selected_categories or course["category"] in selected_categories
    ]
    return [course_card(course) for course in matches[:6]]

# =====================================================
# Weighted Retrieval Engine
# =====================================================

def retrieve(question: str) -> List[Dict]:

    question = normalize(question)
    question_words = set(question.split())

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
Category: {doc['category']}

Title: {doc['title']}

Content:
{doc['content']}

Source:
{doc['source']}

Page:
{doc['page']}
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

    except Exception as e:
        logger.exception("OpenRouter Error")

        return {
            "answer": f"DEBUG: {str(e)}",
            "source": None,
            "page": None,
            "category": None
        }