"""apps/admin/subagents.py

Groq-powered subagents for the Streamlit admin dashboard.

This file intentionally keeps Supabase access and Groq access separate:
- Supabase client is passed in to subagent functions.
- Groq client is initialized from st.secrets.

Subagents implemented:
1) Course Content Creator
2) Analytics Agent
3) Support Lead Assistant
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from supabase import Client

from groq import Groq


MODEL_NAME = "llama-3.3-70b-versatile"


def get_groq_client() -> Optional[Groq]:
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("Missing GROQ_API_KEY in Streamlit secrets.")
        return None
    return Groq(api_key=api_key)


def _safe_json_loads(text: str) -> Dict[str, Any]:
    """Attempt to parse JSON from model output.

    Accepts either raw JSON or JSON embedded in a larger text.
    """
    text = text.strip()

    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract first JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("Model did not return valid JSON")


def _chat_json(prompt: str) -> Dict[str, Any]:
    client = get_groq_client()
    if client is None:
        return {}

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI assistant. You MUST respond with ONLY valid JSON. "
                    "Do not wrap in markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    content = resp.choices[0].message.content or "{}"
    return _safe_json_loads(content)


# ----------------------------------------------------------------------
# 1) Course Content Creator
# ----------------------------------------------------------------------


def course_content_creator(topic: str) -> Dict[str, Any]:
    """Generate course JSON for a given topic."""

    prompt = f"""
Generate a high-quality online course for the topic: "{topic}".

Return ONLY this JSON schema:
{{
  "title": string,
  "description": string,
  "outline": [string],
  "price": number,            -- in PKR
  "duration": string,       -- e.g., "8 weeks"
  "duration_weeks": number, -- integer
  "image_keyword": string   -- keyword for Unsplash/royalty-free search
}}

Rules:
- duration_weeks must be a positive integer.
- outline must be 8-15 bullet strings.
- price must be between 50000 and 250000 (PKR).
"""

    data = _chat_json(prompt)
    return data


def publish_course_to_supabase(
    client: Client,
    course_json: Dict[str, Any],
    teacher_id: Optional[int] = None,
    status: str = "draft",
    image_keyword_to_url: Optional[str] = None,
) -> None:
    """Publish course into Supabase.

    The dashboard can either provide an image_url directly or use an image
    keyword to craft an Unsplash URL externally.
    """

    title = course_json.get("title")
    description = course_json.get("description")
    duration_weeks = course_json.get("duration_weeks")
    price = course_json.get("price")

    if not title or not description or duration_weeks is None or price is None:
        raise ValueError("Course JSON missing required fields")

    # Store image_url/thumbnail_url. Your schema varies; we try thumbnail_url first.
    thumbnail_url = image_keyword_to_url

    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
        "price": price,
        "duration_weeks": int(duration_weeks),
        "status": status,
        "teacher_id": teacher_id,
        "thumbnail_url": thumbnail_url,
        # some schemas might prefer image_url
        "image_url": thumbnail_url,
    }

    # Filter out None values to reduce column errors.
    payload = {k: v for k, v in payload.items() if v is not None}

    # Try insert; on schema mismatch, retry with a reduced payload.
    try:
        client.table("courses").insert(payload).execute()
    except Exception:
        reduced = payload.copy()
        reduced.pop("image_url", None)
        client.table("courses").insert(reduced).execute()


# ----------------------------------------------------------------------
# 2) Analytics Agent
# ----------------------------------------------------------------------


def analytics_agent(client: Client) -> Dict[str, Any]:
    """Calculate revenue potential + metrics for courses and teachers."""

    courses = client.table("courses").select("id, price, duration_weeks, status, teacher_id").execute()
    teachers = client.table("teachers").select("id, name, subject").execute()

    courses_data = courses.data or []
    teachers_data = teachers.data or []

    published = [c for c in courses_data if (c.get("status") or "").lower() == "published"]
    active = [c for c in courses_data if (c.get("status") or "").lower() == "active"]

    def _sum(key: str, rows: List[Dict[str, Any]]) -> float:
        return float(sum((r.get(key) or 0) for r in rows))

    total_potential_revenue = _sum("price", published) + _sum("price", active)

    avg_price = float(_sum("price", courses_data) / len(courses_data)) if courses_data else 0.0
    course_count = len(courses_data)
    teacher_count = len(teachers_data)

    return {
        "course_count": course_count,
        "teacher_count": teacher_count,
        "published_count": len(published),
        "active_count": len(active),
        "total_potential_revenue": total_potential_revenue,
        "avg_price": avg_price,
    }


# ----------------------------------------------------------------------
# 3) Support Lead Assistant
# ----------------------------------------------------------------------


def support_lead_assistant(client: Client, limit: int = 10) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Draft AI replies for unread support messages.

    Returns: (messages, drafts)
    """

    msgs = client.table("support_messages").select("id, name, email, message, status").order("created_at", desc=True).limit(limit).execute()
    messages = msgs.data or []

    drafted: List[Dict[str, Any]] = []

    for m in messages:
        msg_id = m.get("id")
        name = m.get("name")
        email = m.get("email")
        text = m.get("message")

        prompt = f"""
You are a helpful customer support assistant for LearnHub.

Incoming inquiry:
- Name: {name}
- Email: {email}
- Message: {text}

Draft a concise, friendly, and actionable reply.

Return ONLY this JSON:
{{
  "reply": string,
  "next_status": "Open" | "Drafted" | "Replied"
}}
"""

        draft = _chat_json(prompt)
        drafted.append({"id": msg_id, "reply": draft.get("reply"), "next_status": draft.get("next_status")})

    return messages, drafted
