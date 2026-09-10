"""apps/admin/app.py

LearnHub — Streamlit Admin Dashboard
====================================
Secure Streamlit admin dashboard backed by Supabase.

Groq-powered subagents are integrated via `apps/admin/subagents.py`.
All Groq calls are triggered ONLY by explicit button clicks.

Auth:
- Streamlit Secrets (fallback defaults)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

from subagents import (
    MODEL_NAME,
    analytics_agent,
    course_content_creator,
    publish_course_to_supabase,
    support_lead_assistant,
    get_groq_client,
)

# ----------------------------------------------------------------------
# Configuration & Supabase client
# ----------------------------------------------------------------------

TABLES = {
    "admissions": "admissions",
    "courses": "courses",
    "notifications": "notifications",
    "profiles": "profiles",
    "support_tickets": "support_tickets",
    "support_messages": "support_messages",
    "system_settings": "system_settings",
    "teachers": "teachers",
}

STORAGE_BUCKET = "media"


def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    )

    if not url or not key:
        st.error(
            "Missing credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "as environment variables or in Streamlit secrets."
        )
        return None

    return create_client(url, key)


def query_df(client, table: str, select: str = "*") -> pd.DataFrame:
    try:
        res = client.table(table).select(select).execute()
        return pd.DataFrame(res.data or [])
    except Exception as exc:  # pragma: no cover
        st.error(f"Query failed on `{table}`: {exc}")
        return pd.DataFrame()


def upload_media(client, file_obj, folder: str = "uploads") -> str:
    if file_obj is None:
        return ""

    try:
        file_bytes = file_obj.getvalue()
        file_ext = file_obj.name.split(".")[-1].lower() if "." in file_obj.name else "png"
        timestamp = int(time.time() * 1000)
        file_path = f"{folder}/{timestamp}_{file_obj.name}"
        content_type = file_obj.type or f"image/{file_ext}"

        client.storage.from_(STORAGE_BUCKET).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        return client.storage.from_(STORAGE_BUCKET).get_public_url(file_path)
    except Exception as exc:
        st.error(
            f"Storage upload error: {exc}. "
            f"If bucket '{STORAGE_BUCKET}' does not exist, create it as Public."
        )
        return ""


# ----------------------------------------------------------------------
# Security: Admin login gate
# ----------------------------------------------------------------------

ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", "aamrosk519@gmail.com")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "#Suhail#12")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

st.set_page_config(page_title="LearnHub Admin", page_icon="🎓", layout="wide")
st.markdown(
    "<h1 style='margin-bottom:0'>🎓 LearnHub <span style='color:#6366F1'>Admin</span></h1>",
    unsafe_allow_html=True,
)

if not st.session_state["authenticated"]:
    st.markdown(
        """
        <div style='display:flex; justify-content:center; align-items:center; padding-top:40px;'>
          <div style='width:520px; border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:24px; background:rgba(255,255,255,0.03);'>
            <h2 style='margin-bottom:4px;'>Admin Login</h2>
            <p style='margin-top:0; opacity:0.8;'>Please sign in to access the dashboard.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        identity = st.text_input("Email / Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary")

    if submitted:
        if identity == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid email or password")

    st.stop()

# Logout button
with st.sidebar:
    if st.button("Logout", type="secondary"):
        st.session_state["authenticated"] = False
        st.rerun()


# ----------------------------------------------------------------------
# Modules (Analytics / Branding / Faculty / Courses / Admissions)
# ----------------------------------------------------------------------


def render_analytics(client):
    st.subheader("Analytics Overview")

    profiles = query_df(client, "profiles")
    courses = query_df(client, "courses")
    admissions = query_df(client, "admissions")
    tickets = query_df(client, "support_tickets")

    student_count = (
        len(profiles[profiles.get("role") == "student"])
        if not profiles.empty and "role" in profiles.columns
        else len(profiles)
    )
    admission_count = len(admissions)
    courses_active = (
        len(courses[courses.get("status") == "published"])
        if not courses.empty and "status" in courses.columns
        else len(courses)
    )
    open_tickets = (
        len(tickets[tickets.get("status").isin(["open", "in_progress"])])
        if not tickets.empty and "status" in tickets.columns
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Profiles", student_count)
    c2.metric("Total Admissions", admission_count)
    c3.metric("Active Courses", courses_active)
    c4.metric("Open Support Tickets", open_tickets)

    col_l, col_r = st.columns(2)
    with col_l:
        if not admissions.empty and "status" in admissions.columns:
            dist = admissions["status"].value_counts().reset_index()
            dist.columns = ["status", "count"]
            fig = go.Figure(
                go.Pie(
                    labels=dist["status"],
                    values=dist["count"],
                    hole=0.45,
                )
            )
            fig.update_layout(template="plotly_dark", height=360)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No admissions data yet.")

    with col_r:
        if not courses.empty and "title" in courses.columns and "price" in courses.columns:
            bar = courses[["title", "price"]].dropna()
            fig = go.Figure(
                go.Bar(
                    x=bar["title"].astype(str),
                    y=bar["price"],
                    marker_color="#6366F1",
                )
            )
            fig.update_layout(template="plotly_dark", height=360)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No courses to display pricing.")


def render_branding(client):
    st.subheader("Institute Branding")
    rows = query_df(client, "system_settings")

    if rows.empty:
        st.warning("No `system_settings` row found.")
        return

    settings = rows.iloc[0].to_dict()

    with st.form("branding_form"):
        institute_name = st.text_input(
            "Institute name", value=settings.get("institute_name") or ""
        )
        footer_text = st.text_input(
            "Footer text", value=settings.get("footer_text") or ""
        )
        contact_email = st.text_input(
            "Contact email", value=settings.get("contact_email") or ""
        )
        submitted = st.form_submit_button("Save branding", type="primary")

    if submitted:
        try:
            client.table("system_settings").update(
                {
                    "institute_name": institute_name,
                    "footer_text": footer_text,
                    "contact_email": contact_email,
                }
            ).eq("id", settings.get("id", 1)).execute()
            st.success("Branding updated.")
            st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Update failed: {exc}")


def render_faculty(client):
    st.subheader("Faculty Management")
    df = query_df(client, "teachers")

    tab_view, tab_add = st.tabs(["View / Edit / Delete", "Add new teacher"])

    with tab_view:
        if df.empty:
            st.info("No teachers yet.")
            return

        view_cols = [
            c for c in ["id", "name", "role", "subject", "bio", "avatar_url", "image_url"] if c in df.columns
        ]
        st.dataframe(df[view_cols], use_container_width=True, hide_index=True)

        teachers_by_id = df.set_index("id").to_dict("index")
        pick = st.selectbox(
            "Select teacher to edit",
            options=list(teachers_by_id.keys()),
            format_func=lambda i: f"{teachers_by_id[i].get('name')} (id {i})",
        )
        row = teachers_by_id[pick]

        img_col = "avatar_url" if "avatar_url" in row else "image_url"
        current_img = row.get(img_col) or ""
        if current_img:
            st.image(current_img, caption="Current Photo", width=120)

        with st.form("edit_teacher"):
            name = st.text_input("Name", value=row.get("name") or "")
            role = st.text_input("Role", value=row.get("role") or "")
            subject = st.text_input("Subject", value=row.get("subject") or "")
            bio = st.text_area("Bio", value=row.get("bio") or "")
            uploaded_file = st.file_uploader(
                "Upload New Photo (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
            )
            fallback_img_url = st.text_input("Or Image URL (Fallback)", value=current_img)
            save = st.form_submit_button("Update teacher", type="primary")
            delete = st.form_submit_button("Delete teacher")

        if save:
            final_img_url = (fallback_img_url or "").strip() or None
            if uploaded_file is not None:
                with st.spinner("Uploading image..."):
                    uploaded_url = upload_media(client, uploaded_file, folder="teachers")
                    if uploaded_url:
                        final_img_url = uploaded_url

            payload = {
                "name": name,
                "role": role,
                "subject": subject,
                "bio": bio,
                "avatar_url": final_img_url,
                "image_url": final_img_url,
            }
            try:
                client.table("teachers").update(payload).eq("id", pick).execute()
            except Exception:
                payload.pop("image_url", None)
                client.table("teachers").update(payload).eq("id", pick).execute()

            st.success("Teacher updated.")
            st.rerun()

        if delete:
            client.table("teachers").delete().eq("id", pick).execute()
            st.success("Teacher deleted.")
            st.rerun()

    with tab_add:
        with st.form("add_teacher"):
            name = st.text_input("Name *")
            role = st.text_input("Role")
            subject = st.text_input("Subject")
            bio = st.text_area("Bio")
            uploaded_file = st.file_uploader(
                "Upload Photo (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
            )
            fallback_img_url = st.text_input("Or Image URL (Fallback)")
            submitted = st.form_submit_button("Add Teacher", type="primary")

        if submitted:
            if not name.strip():
                st.warning("Name is required.")
                return

            final_img_url = fallback_img_url.strip() or None
            if uploaded_file is not None:
                with st.spinner("Uploading image..."):
                    uploaded_url = upload_media(client, uploaded_file, folder="teachers")
                    if uploaded_url:
                        final_img_url = uploaded_url

            payload = {
                "name": name.strip(),
                "role": role.strip() or None,
                "subject": subject.strip() or None,
                "bio": bio.strip() or None,
                "avatar_url": final_img_url,
                "image_url": final_img_url,
            }
            try:
                client.table("teachers").insert(payload).execute()
            except Exception:
                payload.pop("image_url", None)
                client.table("teachers").insert(payload).execute()

            st.success("Teacher added successfully.")
            st.rerun()


def _course_price_pkr(v: Any) -> str:
    try:
        num = float(v)
        return f"PKR {num:,.0f}" if num.is_integer() else f"PKR {num:,.2f}"
    except Exception:
        return "PKR 0"


def render_courses_horizontal(client):
    st.subheader("Course Management")

    courses = query_df(client, "courses")
    teachers = query_df(client, "teachers")

    teacher_lookup: Dict[Any, Dict[str, Any]] = {}
    if not teachers.empty and "id" in teachers.columns:
        teacher_lookup = teachers.set_index("id").to_dict("index")

    if courses.empty:
        st.info("No courses found.")
        return

    # Normalize column fallbacks
    def get_col(row, *cols):
        for c in cols:
            if c in row and row.get(c) not in [None, ""]:
                return row.get(c)
        return None

    # Cards
    for _, r in courses.iterrows():
        course_id = r.get("id")
        title = get_col(r, "title") or "Untitled course"
        description = get_col(r, "description") or ""
        price = r.get("price")
        duration = r.get("duration_weeks") or r.get("duration")
        status = (str(get_col(r, "status") or "draft")).lower()
        badge = "Published" if status in ["published", "active"] else "Draft"

        thumb = get_col(r, "thumbnail_url", "image_url")

        teacher_id = r.get("teacher_id")
        instructor_name = None
        if teacher_id in teacher_lookup:
            instructor_name = teacher_lookup[teacher_id].get("name") or teacher_lookup[teacher_id].get("designation")
        instructor_name = instructor_name or r.get("instructor") or ""

        st.markdown("---")
        c_img, c_mid, c_right = st.columns([1, 4, 2])

        with c_img:
            if thumb:
                st.image(thumb, width=140, caption="")
            else:
                st.write("")

        with c_mid:
            st.markdown(f"### {title}")
            st.caption(f"Instructor: {instructor_name}")
            st.write(f"**{_course_price_pkr(price)}**")
            st.write(f"**Duration:** {duration} weeks")
            if description:
                st.caption(description)

        with c_right:
            st.success(badge) if badge == "Published" else st.warning(badge)

            edit_key = f"edit_{course_id}"
            del_key = f"del_{course_id}"

            if st.button("Edit", key=edit_key):
                # Simple edit flow: show a form for this course id.
                with st.form(f"edit_form_{course_id}"):
                    new_title = st.text_input("Title", value=title)
                    new_description = st.text_area("Description", value=description)
                    new_price = st.number_input("Price", min_value=0.0, value=float(price or 0))
                    new_duration = st.number_input(
                        "Duration (weeks)", min_value=1, step=1, value=int(duration or 1)
                    )
                    new_status = st.selectbox(
                        "Status", options=["published", "draft"], index=0 if badge == "Published" else 1
                    )
                    submitted = st.form_submit_button("Save")
                if submitted:
                    payload = {
                        "title": new_title,
                        "description": new_description,
                        "price": new_price,
                        "duration_weeks": int(new_duration),
                        "status": new_status,
                    }
                    client.table("courses").update(payload).eq("id", course_id).execute()
                    st.success("Course updated.")
                    st.rerun()

            if st.button("Delete", key=del_key):
                client.table("courses").delete().eq("id", course_id).execute()
                st.success("Course deleted.")
                st.rerun()


def render_ai_copilot(client):
    st.subheader("AI Co-Pilot & Subagents")

    tab_creator, tab_analytics, tab_support = st.tabs(
        ["Course Content Creator", "Analytics Agent", "Support Lead Assistant"]
    )

    with tab_creator:
        topic = st.text_input("Course topic")
        if st.button("Generate Course JSON", type="primary"):
            st.session_state["generated_course_json"] = course_content_creator(topic or "")

        gen = st.session_state.get("generated_course_json")
        if gen:
            st.json(gen)

            publish = st.button("Publish directly to Supabase", type="secondary")
            if publish:
                try:
                    # Optional: map teacher_id later (left as None).
                    publish_course_to_supabase(
                        client=client,
                        course_json=gen,
                        teacher_id=None,
                        status="draft",
                        image_keyword_to_url=None,
                    )
                    st.success("Course published.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Publish failed: {exc}")

    with tab_analytics:
        if st.button("Run Analytics", type="primary"):
            with st.spinner("Calculating..."):
                metrics = analytics_agent(client)
            st.success("Done")
            st.json(metrics)

    with tab_support:
        if st.button("Draft Support Replies", type="primary"):
            with st.spinner("Drafting..."):
                messages, drafts = support_lead_assistant(client)
            st.write(f"Messages found: {len(messages)}")
            st.write("Drafts")
            for d in drafts:
                st.markdown(f"**Message ID:** {d.get('id')}\n\n{d.get('reply')}")


# ----------------------------------------------------------------------
# Admissions & Push notifications
# (kept from existing implementation)
# ----------------------------------------------------------------------


def render_admissions(client):
    st.subheader("Admissions & Push Notifications")

    admissions = query_df(client, "admissions")
    if admissions.empty:
        st.info("No admissions yet.")
    else:
        if "status" in admissions.columns and "id" in admissions.columns:
            edited = st.data_editor(
                admissions,
                use_container_width=True,
                hide_index=True,
                disabled=[c for c in admissions.columns if c not in ["id", "status"]],
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Pending", "Approved", "Rejected"],
                        required=True,
                    )
                },
            )

            if st.button("Save status changes", type="primary"):
                for _, r in edited.iterrows():
                    client.table("admissions").update({"status": r["status"]}).eq(
                        "id", r["id"]
                    ).execute()
                st.success("Admissions updated.")
                st.rerun()

    st.divider()
    st.markdown("#### Broadcast push notification")

    students = query_df(client, "profiles")
    if not students.empty and "role" in students.columns:
        students = students[students["role"] == "student"]

    if students.empty or "id" not in students.columns:
        st.info("No student profiles available to notify.")
        return

    student_map = students.set_index("id").to_dict("index")
    options = list(student_map.keys())
    all_toggle = st.checkbox("Select all students")
    selected = st.multiselect(
        "Recipients",
        options=options,
        default=options if all_toggle else None,
        format_func=lambda uid: student_map[uid].get("full_name")
        or student_map[uid].get("email")
        or str(uid),
    )

    with st.form("push_notification"):
        title = st.text_input("Title", placeholder="New course available")
        message = st.text_area(
            "Message", placeholder="We've launched a new course you might like!"
        )
        push = st.form_submit_button("Send notification", type="primary")

    if push:
        if not selected:
            st.warning("Select at least one student.")
        elif not title.strip():
            st.warning("Title is required.")
        else:
            rows = [
                {
                    "user_id": uid,
                    "title": title.strip(),
                    "message": message.strip(),
                    "is_read": False,
                }
                for uid in selected
            ]
            client.table("notifications").insert(rows).execute()
            st.success(f"Notification sent to {len(rows)} student(s).")


# ----------------------------------------------------------------------
# Main routing
# ----------------------------------------------------------------------


def main():
    client = get_supabase()
    if client is None:
        st.stop()

    menu = st.sidebar.radio(
        "Modules",
        [
            "Analytics Overview",
            "Institute Branding",
            "Faculty Management",
            "Course Management",
            "AI Co-Pilot & Subagents",
            "Admissions & Notifications",
        ],
    )

    if menu == "Analytics Overview":
        render_analytics(client)
    elif menu == "Institute Branding":
        render_branding(client)
    elif menu == "Faculty Management":
        render_faculty(client)
    elif menu == "Course Management":
        render_courses_horizontal(client)
    elif menu == "AI Co-Pilot & Subagents":
        render_ai_copilot(client)
    else:
        render_admissions(client)


if __name__ == "__main__":
    main()
