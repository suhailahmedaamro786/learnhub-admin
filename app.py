"""
LearnHub — Streamlit Admin Dashboard
====================================
Manage institute branding, faculty, admissions, notifications and view
analytics backed by Supabase (service-role key — server-side only).

Credentials are read from environment variables first, then Streamlit
secrets. Provide:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

import os

import pandas as pd
import plotly.express as px  # noqa: F401  (kept for extension)
import plotly.graph_objects as go
import streamlit as st

try:
    import extra_streamlit_components as stx  # noqa: F401
    HAS_STX = True
except Exception:  # pragma: no cover - optional dependency
    HAS_STX = False

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


def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error("Missing credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                 "as environment variables or in Streamlit secrets.")
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


# ----------------------------------------------------------------------
# Analytics
# ----------------------------------------------------------------------

def render_analytics(client):
    st.subheader("Analytics Overview")

    students = query(client, "profiles")
    active_courses = query(client, "courses")
    admission_rows = query(client, "admissions")
    tickets = query(client, "support_tickets")

    student_count = len(students[students.get("role") == "student"]) if not students.empty else 0
    admission_count = len(admission_rows)
    courses_active = len(active_courses[active_courses.get("status") == "published"]) if not active_courses.empty else 0
    open_tickets = len(tickets[tickets.get("status").isin(["open", "in_progress"])]) if not tickets.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Students", student_count)
    c2.metric("Total Admissions", admission_count)
    c3.metric("Active Courses", courses_active)
    c4.metric("Open Support Tickets", open_tickets)

    col_l, col_r = st.columns(2)

    # Admissions distribution (pie)
    with col_l:
        if not admission_rows.empty:
            dist = admission_rows["status"].value_counts().reset_index()
            dist.columns = ["status", "count"]
            fig = go.Figure(go.Pie(
                labels=dist["status"],
                values=dist["count"],
                hole=0.45,
                marker=dict(colors=["#6366F1", "#8B5CF6", "#10B981", "#F43F5E", "#F59E0B"]),
            ))
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
        if not active_courses.empty:
            bar = active_courses[["title", "price"]].dropna()
            fig = go.Figure(go.Bar(
                x=bar["title"].astype(str),
                y=bar["price"],
                marker_color="#6366F1",
                hovertemplate="%{x}<br>$%{y:.2f}<extra></extra>",
            ))
            fig.update_layout(
                title="Course pricing (published)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                xaxis=dict(tickangle=-30),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No published courses to price.")


# ----------------------------------------------------------------------
# Institute branding
# ----------------------------------------------------------------------

def render_branding(client):
    st.subheader("Institute Branding")

    rows = query(client, "system_settings")
    if rows.empty:
        st.warning("No `system_settings` row found. Create row id=1 first.")
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
            }).eq("id", 1).execute()
            st.success("Branding updated.")
        except Exception as exc:  # pragma: no cover
            st.error(f"Update failed: {exc}")


# ----------------------------------------------------------------------
# Faculty management (CRUD)
# ----------------------------------------------------------------------

def render_faculty(client):
    st.subheader("Faculty Management")
    df = query(client, "teachers")

    tab_view, tab_add = st.tabs(["View / Edit / Delete", "Add new teacher"])

    with tab_view:
        if df.empty:
            st.info("No teachers yet.")
        else:
            view = df[["id", "name", "role", "subject", "bio", "avatar_url"]]
            st.dataframe(view, use_container_width=True, hide_index=True)

            st.divider()
            # Edit
            teachers_by_id = df.set_index("id").to_dict("index")
            pick = st.selectbox("Select teacher to edit", options=list(teachers_by_id.keys()),
                                format_func=lambda i: f"{teachers_by_id[i].get('name')} (id {i})")
            row = teachers_by_id[pick]

            with st.form("edit_teacher"):
                name = st.text_input("Name", value=row.get("name") or "")
                role = st.text_input("Role", value=row.get("role") or "")
                subject = st.text_input("Subject", value=row.get("subject") or "")
                bio = st.text_area("Bio", value=row.get("bio") or "")
                avatar_url = st.text_input("Avatar URL", value=row.get("avatar_url") or "")
                save = st.form_submit_button("Update teacher", type="primary")
                delete = st.form_submit_button("Delete teacher")

            if save:
                client.table("teachers").update({
                    "name": name, "role": role, "subject": subject,
                    "bio": bio, "avatar_url": avatar_url,
                }).eq("id", pick).execute()
                st.success("Teacher updated.")
                st.rerun()
            if delete:
                client.table("teachers").delete().eq("id", pick).execute()
                st.success("Teacher deleted.")
                st.rerun()

    with tab_add:
        with st.form("add_teacher"):
            name = st.text_input("Name")
            role = st.text_input("Role")
            subject = st.text_input("Subject")
            bio = st.text_area("Bio")
            avatar_url = st.text_input("Avatar URL")
            submitted = st.form_submit_button("Add teacher", type="primary")

        if submitted and name.strip():
            client.table("teachers").insert({
                "name": name.strip(), "role": role.strip() or None,
                "subject": subject.strip() or None, "bio": bio.strip() or None,
                "avatar_url": avatar_url.strip() or None,
            }).execute()
            st.success("Teacher added.")
            st.rerun()
        elif submitted:
            st.warning("Name is required.")


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
        # Datatable with an editable status dropdown (Pending -> Approved/Rejected).
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
            st.success(f"{changes} admission(s) updated.") if changes else st.info("No changes.")

    st.divider()

    # ---- Push notifications ----
    st.markdown("#### Broadcast push notification")
    students = query(client, "profiles")
    students = students[students.get("role") == "student"] if not students.empty else students

    if students.empty:
        st.info("No students available to notify.")
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
            client.table("notifications").insert(rows).execute()
            st.success(f"Notification sent to {len(rows)} student(s).")


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
            "Admissions & Notifications",
        ],
    )

    if menu == "Analytics Overview":
        render_analytics(client)
    elif menu == "Institute Branding":
        render_branding(client)
    elif menu == "Faculty Management":
        render_faculty(client)
    else:
        render_admissions(client)


if __name__ == "__main__":
    main()
