"""
LearnHub — Streamlit Admin Dashboard
====================================
Manage institute branding, faculty, courses, admissions, notifications and view
analytics backed by Supabase (service-role key — server-side only).

Credentials are read from environment variables first, then Streamlit
secrets. Provide:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

import os
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from supabase import create_client

# ----------------------------------------------------------------------
# Configuration & client
# ----------------------------------------------------------------------

TABLES = {
    "admissions": "admissions",
    "courses": "courses",
    "notifications": "notifications",
    "profiles": "profiles",
    "support_tickets": "support_tickets",
    "system_settings": "system_settings",
    "teachers": "teachers",
}

STORAGE_BUCKET = "media"


def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error(
            "Missing credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "as environment variables or in Streamlit secrets."
        )
        return None
    return create_client(url, key)


def query(client, table: str):
    """Run a full select and return a DataFrame (or empty on error)."""
    try:
        res = client.table(table).select("*").execute()
        return pd.DataFrame(res.data or [])
    except Exception as exc:  # pragma: no cover
        st.error(f"Query failed on `{table}`: {exc}")
        return pd.DataFrame()


def upload_media(client, file_obj, folder: str = "uploads") -> str:
    """
    Upload an uploaded file object directly to Supabase Storage bucket 'media'
    and return the public URL.
    """
    if file_obj is None:
        return ""
    try:
        file_bytes = file_obj.getvalue()
        file_ext = file_obj.name.split(".")[-1].lower() if "." in file_obj.name else "png"
        timestamp = int(time.time() * 1000)
        file_path = f"{folder}/{timestamp}_{file_obj.name}"
        content_type = file_obj.type or f"image/{file_ext}"

        # Upload file bytes to Supabase storage
        client.storage.from_(STORAGE_BUCKET).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        # Get the public URL
        res = client.storage.from_(STORAGE_BUCKET).get_public_url(file_path)
        return res
    except Exception as exc:
        st.error(f"Storage upload error: {exc}. If bucket '{STORAGE_BUCKET}' does not exist, create it as Public in Supabase Storage dashboard.")
        return ""


# ----------------------------------------------------------------------
# Analytics
# ----------------------------------------------------------------------

def render_analytics(client):
    st.subheader("Analytics Overview")

    students = query(client, "profiles")
    active_courses = query(client, "courses")
    admission_rows = query(client, "admissions")
    tickets = query(client, "support_tickets")

    student_count = len(students[students.get("role") == "student"]) if not students.empty and "role" in students.columns else len(students)
    admission_count = len(admission_rows)
    courses_active = (
        len(active_courses[active_courses.get("status") == "published"])
        if not active_courses.empty and "status" in active_courses.columns
        else len(active_courses)
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

    # Admissions distribution (pie)
    with col_l:
        if not admission_rows.empty and "status" in admission_rows.columns:
            dist = admission_rows["status"].value_counts().reset_index()
            dist.columns = ["status", "count"]
            fig = go.Figure(
                go.Pie(
                    labels=dist["status"],
                    values=dist["count"],
                    hole=0.45,
                    marker=dict(colors=["#6366F1", "#8B5CF6", "#10B981", "#F43F5E", "#F59E0B"]),
                )
            )
            fig.update_layout(
                title="Admissions by status",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No admissions data yet.")

    # Course pricing (bar)
    with col_r:
        if not active_courses.empty and "title" in active_courses.columns and "price" in active_courses.columns:
            bar = active_courses[["title", "price"]].dropna()
            fig = go.Figure(
                go.Bar(
                    x=bar["title"].astype(str),
                    y=bar["price"],
                    marker_color="#6366F1",
                    hovertemplate="%{x}<br>$%{y:.2f}<extra></extra>",
                )
            )
            fig.update_layout(
                title="Course pricing",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                xaxis=dict(tickangle=-30),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No courses to display pricing.")


# ----------------------------------------------------------------------
# Institute branding
# ----------------------------------------------------------------------

def render_branding(client):
    st.subheader("Institute Branding")

    rows = query(client, "system_settings")
    if rows.empty:
        st.warning("No `system_settings` row found. Creating default settings row...")
        if st.button("Initialize system settings"):
            try:
                client.table("system_settings").insert({
                    "id": 1,
                    "institute_name": "LearnHub",
                    "footer_text": "© LearnHub. All rights reserved.",
                    "contact_email": "admin@learnhub.com",
                }).execute()
                st.success("System settings initialized.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to initialize: {exc}")
        return

    settings = rows.iloc[0].to_dict()

    with st.form("branding_form"):
        institute_name = st.text_input("Institute name", value=settings.get("institute_name") or "")
        footer_text = st.text_input("Footer text", value=settings.get("footer_text") or "")
        contact_email = st.text_input("Contact email", value=settings.get("contact_email") or "")
        submitted = st.form_submit_button("Save branding", type="primary")

    if submitted:
        try:
            client.table("system_settings").update({
                "institute_name": institute_name,
                "footer_text": footer_text,
                "contact_email": contact_email,
            }).eq("id", settings.get("id", 1)).execute()
            st.success("Branding updated.")
        except Exception as exc:  # pragma: no cover
            st.error(f"Update failed: {exc}")


# ----------------------------------------------------------------------
# Faculty management (CRUD + File Upload)
# ----------------------------------------------------------------------

def render_faculty(client):
    st.subheader("Faculty Management")
    df = query(client, "teachers")

    tab_view, tab_add = st.tabs(["View / Edit / Delete", "Add New Teacher"])

    # Determine image field in table (avatar_url or image_url)
    img_col = "avatar_url" if (not df.empty and "avatar_url" in df.columns) else "image_url"

    with tab_view:
        if df.empty:
            st.info("No teachers found.")
        else:
            cols_to_show = [c for c in ["id", "name", "role", "subject", "bio", img_col] if c in df.columns]
            st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True)

            st.divider()
            teachers_by_id = df.set_index("id").to_dict("index")
            pick = st.selectbox(
                "Select teacher to edit",
                options=list(teachers_by_id.keys()),
                format_func=lambda i: f"{teachers_by_id[i].get('name', 'Unnamed')} (id {i})",
            )
            row = teachers_by_id[pick]

            current_img = row.get(img_col) or row.get("avatar_url") or row.get("image_url") or ""
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
                    key=f"teacher_edit_file_{pick}",
                )
                manual_img_url = st.text_input(
                    "Or Image URL (Fallback)",
                    value=current_img,
                    help="Will be used if no new file is uploaded.",
                )

                c_save, c_del = st.columns([1, 1])
                with c_save:
                    save = st.form_submit_button("Update teacher", type="primary", use_container_width=True)
                with c_del:
                    delete = st.form_submit_button("Delete teacher", use_container_width=True)

            if save:
                final_img_url = manual_img_url
                if uploaded_file is not None:
                    with st.spinner("Uploading image to media bucket..."):
                        uploaded_url = upload_media(client, uploaded_file, folder="teachers")
                        if uploaded_url:
                            final_img_url = uploaded_url

                update_payload = {
                    "name": name,
                    "role": role,
                    "subject": subject,
                    "bio": bio,
                    "avatar_url": final_img_url,
                    "image_url": final_img_url,
                }
                # Filter to columns that exist if known, or send standard
                try:
                    client.table("teachers").update(update_payload).eq("id", pick).execute()
                    st.success("Teacher updated.")
                    st.rerun()
                except Exception as exc:
                    # Retry with avatar_url only if image_url column doesn't exist
                    try:
                        update_payload.pop("image_url", None)
                        client.table("teachers").update(update_payload).eq("id", pick).execute()
                        st.success("Teacher updated.")
                        st.rerun()
                    except Exception as e2:
                        st.error(f"Update failed: {e2}")

            if delete:
                try:
                    client.table("teachers").delete().eq("id", pick).execute()
                    st.success("Teacher deleted.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")

    with tab_add:
        with st.form("add_teacher"):
            name = st.text_input("Name *")
            role = st.text_input("Role (e.g. Senior Instructor)")
            subject = st.text_input("Subject (e.g. Full Stack Development)")
            bio = st.text_area("Bio")

            uploaded_file = st.file_uploader(
                "Upload Photo (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
                key="teacher_add_file",
            )
            fallback_img_url = st.text_input("Or Image URL (Fallback)")

            submitted = st.form_submit_button("Add Teacher", type="primary")

        if submitted:
            if not name.strip():
                st.warning("Name is required.")
            else:
                final_img_url = fallback_img_url.strip() or None
                if uploaded_file is not None:
                    with st.spinner("Uploading image to media bucket..."):
                        uploaded_url = upload_media(client, uploaded_file, folder="teachers")
                        if uploaded_url:
                            final_img_url = uploaded_url

                insert_payload = {
                    "name": name.strip(),
                    "role": role.strip() or None,
                    "subject": subject.strip() or None,
                    "bio": bio.strip() or None,
                    "avatar_url": final_img_url,
                    "image_url": final_img_url,
                }
                try:
                    client.table("teachers").insert(insert_payload).execute()
                    st.success("Teacher added successfully.")
                    st.rerun()
                except Exception as exc:
                    # Retry without image_url if schema only has avatar_url
                    try:
                        insert_payload.pop("image_url", None)
                        client.table("teachers").insert(insert_payload).execute()
                        st.success("Teacher added successfully.")
                        st.rerun()
                    except Exception as e2:
                        st.error(f"Failed to add teacher: {e2}")


# ----------------------------------------------------------------------
# Course management (CRUD + File Upload)
# ----------------------------------------------------------------------

def render_courses(client):
    st.subheader("Course Management")

    courses_df = query(client, "courses")
    teachers_df = query(client, "teachers")

    tab_view, tab_add = st.tabs(["View / Edit / Delete Courses", "Add New Course"])

    # Prepare teachers lookup
    teacher_options = {}
    if not teachers_df.empty and "id" in teachers_df.columns:
        for _, t in teachers_df.iterrows():
            label = f"{t.get('name', 'Teacher')} ({t.get('subject') or 'General'})"
            teacher_options[t["id"]] = label

    thumb_col = "thumbnail_url" if (not courses_df.empty and "thumbnail_url" in courses_df.columns) else "image_url"

    with tab_view:
        if courses_df.empty:
            st.info("No courses created yet.")
        else:
            cols_to_show = [c for c in ["id", "title", "category", "price", "duration_weeks", "status", "teacher_id", thumb_col] if c in courses_df.columns]
            st.dataframe(courses_df[cols_to_show], use_container_width=True, hide_index=True)

            st.divider()
            courses_by_id = courses_df.set_index("id").to_dict("index")
            pick_id = st.selectbox(
                "Select course to edit",
                options=list(courses_by_id.keys()),
                format_func=lambda i: f"{courses_by_id[i].get('title', 'Untitled')} (ID: {i})",
            )
            course_row = courses_by_id[pick_id]

            current_img = course_row.get(thumb_col) or course_row.get("thumbnail_url") or course_row.get("image_url") or ""
            if current_img:
                st.image(current_img, caption="Course Thumbnail", width=220)

            with st.form("edit_course_form"):
                title = st.text_input("Title *", value=course_row.get("title") or "")
                description = st.text_area("Description", value=course_row.get("description") or "")
                category = st.text_input("Category", value=course_row.get("category") or "Development")

                c1, c2, c3 = st.columns(3)
                with c1:
                    price_val = float(course_row.get("price") or 0.0)
                    price = st.number_input("Price ($)", min_value=0.0, step=5.0, value=price_val)
                with c2:
                    dur_val = int(course_row.get("duration_weeks") or 4)
                    duration = st.number_input("Duration (Weeks)", min_value=1, step=1, value=dur_val)
                with c3:
                    curr_status = str(course_row.get("status") or "published").lower()
                    status_idx = 0 if curr_status == "published" else 1
                    status = st.selectbox("Status", options=["published", "draft"], index=status_idx)

                # Teacher selection
                teacher_ids = list(teacher_options.keys())
                curr_t_id = course_row.get("teacher_id")
                curr_t_idx = teacher_ids.index(curr_t_id) if curr_t_id in teacher_ids else 0

                teacher_id = None
                if teacher_ids:
                    selected_teacher_id = st.selectbox(
                        "Instructor / Teacher",
                        options=teacher_ids,
                        index=curr_t_idx,
                        format_func=lambda tid: teacher_options.get(tid, f"ID {tid}"),
                    )
                    teacher_id = selected_teacher_id
                else:
                    st.info("No teachers found in database. Add a teacher in Faculty Management first.")

                uploaded_file = st.file_uploader(
                    "Upload New Course Image (JPG, PNG, WEBP)",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"course_edit_file_{pick_id}",
                )
                manual_img_url = st.text_input(
                    "Or Image / Thumbnail URL (Fallback)",
                    value=current_img,
                    help="Used if no new file is uploaded.",
                )

                c_save, c_del = st.columns([1, 1])
                with c_save:
                    save = st.form_submit_button("Update Course", type="primary", use_container_width=True)
                with c_del:
                    delete = st.form_submit_button("Delete Course", use_container_width=True)

            if save:
                final_img_url = manual_img_url
                if uploaded_file is not None:
                    with st.spinner("Uploading course thumbnail to media bucket..."):
                        uploaded_url = upload_media(client, uploaded_file, folder="courses")
                        if uploaded_url:
                            final_img_url = uploaded_url

                update_payload = {
                    "title": title.strip(),
                    "description": description.strip() or None,
                    "category": category.strip() or None,
                    "price": price,
                    "duration_weeks": int(duration),
                    "status": status,
                    "teacher_id": teacher_id,
                    "thumbnail_url": final_img_url,
                    "image_url": final_img_url,
                }
                try:
                    client.table("courses").update(update_payload).eq("id", pick_id).execute()
                    st.success("Course updated successfully.")
                    st.rerun()
                except Exception as exc:
                    # If column like 'category' or 'image_url' doesn't exist, try minimal payload
                    try:
                        update_payload.pop("image_url", None)
                        client.table("courses").update(update_payload).eq("id", pick_id).execute()
                        st.success("Course updated successfully.")
                        st.rerun()
                    except Exception as e2:
                        try:
                            update_payload.pop("category", None)
                            client.table("courses").update(update_payload).eq("id", pick_id).execute()
                            st.success("Course updated successfully.")
                            st.rerun()
                        except Exception as e3:
                            st.error(f"Failed to update course: {e3}")

            if delete:
                try:
                    client.table("courses").delete().eq("id", pick_id).execute()
                    st.success("Course deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")

    with tab_add:
        with st.form("add_course_form"):
            title = st.text_input("Course Title *")
            description = st.text_area("Description")
            category = st.text_input("Category", value="Web Development")

            c1, c2, c3 = st.columns(3)
            with c1:
                price = st.number_input("Price ($)", min_value=0.0, step=5.0, value=49.99)
            with c2:
                duration = st.number_input("Duration (Weeks)", min_value=1, step=1, value=6)
            with c3:
                status = st.selectbox("Status", options=["published", "draft"])

            teacher_ids = list(teacher_options.keys())
            teacher_id = None
            if teacher_ids:
                teacher_id = st.selectbox(
                    "Assign Teacher",
                    options=teacher_ids,
                    format_func=lambda tid: teacher_options.get(tid, f"ID {tid}"),
                )
            else:
                st.caption("No teachers available yet. You can assign one later.")

            uploaded_file = st.file_uploader(
                "Upload Course Thumbnail (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
                key="course_add_file",
            )
            fallback_img_url = st.text_input("Or Thumbnail URL (Fallback)")

            submitted = st.form_submit_button("Add Course", type="primary")

        if submitted:
            if not title.strip():
                st.warning("Course title is required.")
            else:
                final_img_url = fallback_img_url.strip() or None
                if uploaded_file is not None:
                    with st.spinner("Uploading course thumbnail to media bucket..."):
                        uploaded_url = upload_media(client, uploaded_file, folder="courses")
                        if uploaded_url:
                            final_img_url = uploaded_url

                insert_payload = {
                    "title": title.strip(),
                    "description": description.strip() or None,
                    "category": category.strip() or None,
                    "price": price,
                    "duration_weeks": int(duration),
                    "status": status,
                    "teacher_id": teacher_id,
                    "thumbnail_url": final_img_url,
                    "image_url": final_img_url,
                }
                try:
                    client.table("courses").insert(insert_payload).execute()
                    st.success("Course created successfully.")
                    st.rerun()
                except Exception as exc:
                    try:
                        insert_payload.pop("image_url", None)
                        client.table("courses").insert(insert_payload).execute()
                        st.success("Course created successfully.")
                        st.rerun()
                    except Exception as e2:
                        try:
                            insert_payload.pop("category", None)
                            client.table("courses").insert(insert_payload).execute()
                            st.success("Course created successfully.")
                            st.rerun()
                        except Exception as e3:
                            st.error(f"Failed to create course: {e3}")


# ----------------------------------------------------------------------
# Admissions + push notifications
# ----------------------------------------------------------------------

ADMISSION_STATUSES = ["Pending", "Approved", "Rejected"]


def render_admissions(client):
    st.subheader("Admissions & Push Notifications")

    admissions = query(client, "admissions")
    if admissions.empty:
        st.info("No admissions yet.")
    else:
        edit_cols = ["id", "status"]
        disabled = [c for c in admissions.columns if c not in edit_cols]
        orig_map = dict(zip(admissions["id"], admissions["status"]))

        edited = st.data_editor(
            admissions,
            use_container_width=True,
            hide_index=True,
            disabled=disabled,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Status", options=ADMISSION_STATUSES, required=True,
                ),
            },
        )

        if st.button("Save status changes", type="primary"):
            changes = 0
            for _, r in edited.iterrows():
                if r["status"] != orig_map.get(r["id"]):
                    client.table("admissions").update({"status": r["status"]}).eq("id", r["id"]).execute()
                    changes += 1
            if changes:
                st.success(f"{changes} admission(s) updated.")
            else:
                st.info("No changes.")

    st.divider()

    # ---- Push notifications ----
    st.markdown("#### Broadcast push notification")
    students = query(client, "profiles")
    if not students.empty and "role" in students.columns:
        students = students[students["role"] == "student"]

    if students.empty:
        st.info("No student profiles available to notify.")
        return

    student_map = students.set_index("id").to_dict("index")
    options = list(student_map.keys())

    all_toggle = st.checkbox("Select all students")
    selected = st.multiselect(
        "Recipients",
        options=options,
        default=options if all_toggle else None,
        format_func=lambda uid: student_map[uid].get("full_name") or student_map[uid].get("email") or uid,
    )

    with st.form("push_notification"):
        title = st.text_input("Title", placeholder="New course available")
        message = st.text_area("Message", placeholder="We've launched a new course you might like!")
        push = st.form_submit_button("Send notification", type="primary")

    if push:
        if not selected:
            st.warning("Select at least one student.")
        elif not title.strip():
            st.warning("Title is required.")
        else:
            rows = [
                {"user_id": uid, "title": title.strip(), "message": message.strip(), "is_read": False}
                for uid in selected
            ]
            try:
                client.table("notifications").insert(rows).execute()
                st.success(f"Notification sent to {len(rows)} student(s).")
            except Exception as exc:
                st.error(f"Failed to send notification: {exc}")


# ----------------------------------------------------------------------
# App shell
# ----------------------------------------------------------------------

def main():
    st.set_page_config(page_title="LearnHub Admin", page_icon="🎓", layout="wide")
    st.markdown(
        "<h1 style='margin-bottom:0'>🎓 LearnHub <span style='color:#6366F1'>Admin</span></h1>",
        unsafe_allow_html=True,
    )

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
        render_courses(client)
    else:
        render_admissions(client)


if __name__ == "__main__":
    main()
