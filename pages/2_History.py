from __future__ import annotations

import streamlit as st

from db.queries import delete_post, get_posts, update_post_status

st.set_page_config(page_title="History — Content Team", page_icon="📋", layout="wide")

st.title("📋 History")

# ── status tabs ───────────────────────────────────────────────────────────────

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


def _render_posts(filter_status: str | None) -> None:
    posts = get_posts(status=filter_status)
    if not posts:
        st.info("No posts found.")
        return

    for post in posts:
        date_str  = post.created_at[:10] if post.created_at else "—"
        badge     = _STATUS_BADGE.get(post.status, post.status)
        preview   = (post.content_en[:100] + "…") if len(post.content_en) > 100 else post.content_en

        with st.expander(f"**{date_str}** · {post.topic[:60]} · {badge}", expanded=False):
            # Full editable post content
            edited_content = st.text_area(
                "Post content",
                value=post.content_en,
                height=260,
                key=f"hist_edit_{post.id}",
            )

            col_save, col_pub, col_copy, col_del, _ = st.columns([1, 1, 1, 1, 4])

            # Save edits
            if col_save.button("💾 Save edits", key=f"save_{post.id}"):
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
            if col_pub.button("🚀 Publish", key=f"pub_{post.id}", disabled=post.status == "published"):
                update_post_status(post.id, "published")
                st.success("Marked as published.")
                st.rerun()

            # Copy helper
            if col_copy.button("📋 Copy", key=f"copy_{post.id}"):
                st.code(post.content_en, language=None)

            # Delete
            if col_del.button("🗑️ Delete", key=f"del_{post.id}"):
                delete_post(post.id)
                st.warning("Post deleted.")
                st.rerun()

            st.caption(f"Post ID: {post.id} · Run: {post.run_id or '—'}")


with tab_all:
    _render_posts(None)

with tab_approved:
    _render_posts("approved")

with tab_edited:
    _render_posts("edited")

with tab_published:
    _render_posts("published")

