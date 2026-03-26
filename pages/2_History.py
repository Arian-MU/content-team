from __future__ import annotations

import streamlit as st

from db.gdrive_sync import export_all_approved_to_drive, export_post_to_drive, is_gdrive_enabled
from db.queries import delete_post, get_posts, update_post_status

st.set_page_config(page_title="History — Content Team", page_icon="📋", layout="wide")

st.title("📋 History")

# ── Google Drive bulk export ──────────────────────────────────────────────────

if is_gdrive_enabled():
    with st.container():
        col_drive, col_info = st.columns([2, 8])
        with col_drive:
            if st.button("☁️ Export all to Drive", type="secondary"):
                with st.spinner("Uploading to Google Drive…"):
                    try:
                        result = export_all_approved_to_drive()
                        st.success(f"Exported {result['exported']} post(s) to Drive.")
                        if result["errors"]:
                            for err in result["errors"]:
                                st.warning(err)
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Drive export failed: {exc}")
        with col_info:
            st.caption("Exports all approved / edited / published posts as .txt files to your configured Drive folder.")
    st.divider()

tab_all, tab_approved, tab_edited, tab_published = st.tabs(
    ["All", "Approved", "Edited", "Published"]
)

_VISIBLE_STATUSES = {
    "All":       None,
    "Approved":  "approved",
    "Edited":    "edited",
    "Published": "published",
}

_STATUS_BADGE = {
    "draft":     "🟡 Draft",
    "approved":  "✅ Approved",
    "edited":    "✏️ Edited",
    "published": "🚀 Published",
}


def _render_posts(filter_status: str | None, tab: str) -> None:
    """Render posts for a given status filter.

    `tab` is a short unique string used as a key prefix so widgets
    across tabs never share the same Streamlit element key.
    """
    posts = get_posts(status=filter_status)
    if not posts:
        st.info("No posts found.")
        return

    for post in posts:
        date_str = post.created_at[:10] if post.created_at else "—"
        badge    = _STATUS_BADGE.get(post.status, post.status)

        with st.expander(f"**{date_str}** · {post.topic[:60]} · {badge}", expanded=False):
            # Full editable post content
            edited_content = st.text_area(
                "Post content",
                value=post.content_en,
                height=260,
                key=f"{tab}_edit_{post.id}",
            )

            col_save, col_pub, col_copy, col_del, col_drive, _ = st.columns([1, 1, 1, 1, 1, 3])

            # Save edits
            if col_save.button("💾 Save edits", key=f"{tab}_save_{post.id}"):
                import db.database as _db
                with _db.get_connection() as _conn:
                    new_status = "edited" if post.status not in ("published",) else post.status
                    _conn.execute(
                        "UPDATE posts SET content_en = ?, status = ? WHERE id = ?",
                        (edited_content, new_status, post.id),
                    )
                    _conn.commit()
                st.success("Saved.")
                st.rerun()

            # Mark published
            if col_pub.button("🚀 Publish", key=f"{tab}_pub_{post.id}", disabled=post.status == "published"):
                update_post_status(post.id, "published")
                st.success("Marked as published.")
                st.rerun()

            # Copy helper
            if col_copy.button("📋 Copy", key=f"{tab}_copy_{post.id}"):
                st.code(post.content_en, language=None)

            # Delete
            if col_del.button("🗑️ Delete", key=f"{tab}_del_{post.id}"):
                delete_post(post.id)
                st.warning("Post deleted.")
                st.rerun()

            # Export to Drive (only shown when Drive is enabled)
            if is_gdrive_enabled():
                if col_drive.button("☁️ Drive", key=f"{tab}_drive_{post.id}"):
                    with st.spinner("Uploading…"):
                        try:
                            url = export_post_to_drive(post.id)
                            st.success(f"Uploaded. [Open in Drive]({url})")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Upload failed: {exc}")

            st.caption(f"Post ID: {post.id} · Run: {post.run_id or '—'}")


with tab_all:
    _render_posts(None, "all")

with tab_approved:
    _render_posts("approved", "approved")

with tab_edited:
    _render_posts("edited", "edited")

with tab_published:
    _render_posts("published", "published")

