import csv
import hmac
import html
import io
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

APP_TITLE = "StudyRoom Admin"
DB_PATH = Path(os.getenv("STUDY_ROOM_DB", "study_room.db"))
PRESENCE_TIMEOUT_MINUTES = 3
JST = timezone(timedelta(hours=9))

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
)


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def safe_text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_admin_password() -> str:
    env_password = os.getenv("STUDY_ROOM_ADMIN_PASSWORD", "").strip()
    if env_password:
        return env_password
    try:
        return str(st.secrets.get("STUDY_ROOM_ADMIN_PASSWORD", "")).strip()
    except Exception:
        return ""


def csv_safe(value) -> str:
    text = str(value or "")
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS participants (
                session_id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                avatar TEXT,
                comment TEXT,
                activity TEXT NOT NULL,
                detail TEXT,
                mood TEXT,
                joined_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                nickname TEXT,
                activity TEXT,
                detail TEXT,
                category TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS presence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                session_id TEXT NOT NULL,
                nickname TEXT,
                activity TEXT,
                detail TEXT,
                comment TEXT,
                mood TEXT,
                room_count INTEGER NOT NULL,
                total_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(presence_events)").fetchall()}
        if "comment" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN comment TEXT")
        if "mood" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN mood TEXT")


def log_presence_event(conn, event_type, row):
    activity = row["activity"]
    room_count = conn.execute(
        "SELECT COUNT(*) FROM participants WHERE activity = ?",
        (activity,),
    ).fetchone()[0]
    total_count = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
    conn.execute(
        """
        INSERT INTO presence_events
            (event_type, session_id, nickname, activity, detail, comment, mood, room_count, total_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            row["session_id"],
            row["nickname"],
            row["activity"],
            row["detail"],
            row["comment"],
            row["mood"],
            room_count,
            total_count,
            now_iso(),
        ),
    )


def cleanup_stale():
    cutoff = (datetime.now(JST) - timedelta(minutes=PRESENCE_TIMEOUT_MINUTES)).isoformat(timespec="seconds")
    with get_conn() as conn:
        stale_rows = conn.execute("SELECT * FROM participants WHERE last_seen < ?", (cutoff,)).fetchall()
        conn.execute("DELETE FROM participants WHERE last_seen < ?", (cutoff,))
        for row in stale_rows:
            log_presence_event(conn, "自動退室", row)


def fetch_feedback(limit=500):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def fetch_presence_events(limit=500):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM presence_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def feedback_csv(rows) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "category", "nickname", "activity", "detail", "body"])
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["created_at"],
                csv_safe(row["category"]),
                csv_safe(row["nickname"]),
                csv_safe(row["activity"]),
                csv_safe(row["detail"]),
                csv_safe(row["body"]),
            ]
        )
    return output.getvalue()


def presence_events_csv(rows) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "event_type",
            "nickname",
            "activity",
            "detail",
            "comment",
            "mood",
            "room_count",
            "total_count",
            "session_id",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["created_at"],
                csv_safe(row["event_type"]),
                csv_safe(row["nickname"]),
                csv_safe(row["activity"]),
                csv_safe(row["detail"]),
                csv_safe(row["comment"]),
                csv_safe(row["mood"]),
                row["room_count"],
                row["total_count"],
                row["session_id"],
            ]
        )
    return output.getvalue()


def fetch_admin_stats():
    cleanup_stale()
    with get_conn() as conn:
        current_total = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
        feedback_total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        event_total = conn.execute("SELECT COUNT(*) FROM presence_events").fetchone()[0]
        active_rooms = conn.execute(
            "SELECT activity, COUNT(*) AS count FROM participants GROUP BY activity ORDER BY count DESC, activity"
        ).fetchall()
        join_counts = conn.execute(
            """
            SELECT activity, COUNT(*) AS count
            FROM presence_events
            WHERE event_type = '入室'
            GROUP BY activity
            ORDER BY count DESC, activity
            """
        ).fetchall()
    return current_total, feedback_total, event_total, active_rooms, join_counts


def check_password():
    admin_password = get_admin_password()
    if not admin_password:
        st.error("STUDY_ROOM_ADMIN_PASSWORD を設定してから起動してください。")
        st.stop()
    if len(admin_password) < 12:
        st.warning("管理者パスワードは12文字以上の強い文字列を推奨します。")

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if st.session_state.admin_authenticated:
        return

    st.title("StudyRoom Admin")
    entered_password = st.text_input("管理者パスワード", type="password")
    if st.button("ログイン", type="primary"):
        if hmac.compare_digest(entered_password, admin_password):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()


def render_admin_dashboard():
    st.title("StudyRoom Admin")
    st.caption("この画面は管理者用です。通常の自習室アプリからはリンクしていません。")

    if st.button("ログアウト"):
        st.session_state.admin_authenticated = False
        st.rerun()

    current_total, feedback_total, event_total, active_rooms, join_counts = fetch_admin_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("現在の入室者", f"{current_total}人")
    c2.metric("意見・要望", f"{feedback_total}件")
    c3.metric("入退室履歴", f"{event_total}件")

    overview_tab, events_tab, feedback_tab = st.tabs(["利用状況", "入退室履歴", "意見・要望"])

    with overview_tab:
        left, right = st.columns(2)
        with left:
            st.subheader("現在の部屋別人数")
            if active_rooms:
                st.dataframe(
                    [{"部屋": row["activity"], "人数": row["count"]} for row in active_rooms],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("現在の入室者はいません。")
        with right:
            st.subheader("累計入室数（部屋別）")
            if join_counts:
                st.dataframe(
                    [{"部屋": row["activity"], "入室数": row["count"]} for row in join_counts],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("入室履歴はまだありません。")

    with events_tab:
        event_rows = fetch_presence_events(limit=500)
        st.download_button(
            "入退室履歴CSVをダウンロード",
            data="\ufeff" + presence_events_csv(event_rows),
            file_name="studyroom_presence_events.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if event_rows:
            st.dataframe(
                [
                    {
                        "日時": row["created_at"],
                        "種別": row["event_type"],
                        "ニックネーム": row["nickname"] or "",
                        "部屋": row["activity"] or "",
                        "授業回": row["detail"] or "",
                        "コメント": row["comment"] or "",
                        "状態": row["mood"] or "",
                        "部屋人数": row["room_count"],
                        "全体人数": row["total_count"],
                    }
                    for row in event_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("入退室履歴はまだありません。")

    with feedback_tab:
        feedback_rows = fetch_feedback(limit=500)
        st.download_button(
            "意見・要望CSVをダウンロード",
            data="\ufeff" + feedback_csv(feedback_rows),
            file_name="studyroom_feedback.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if feedback_rows:
            for row in feedback_rows[:50]:
                st.markdown(
                    f"**{safe_text(row['category'])}** "
                    f"<span style='opacity:.65'>{safe_text(row['created_at'])}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{row['nickname'] or '未入室'} / {row['activity'] or '-'} / {row['detail'] or '-'}"
                )
                st.write(row["body"])
        else:
            st.caption("意見・要望はまだありません。")


init_db()
check_password()
render_admin_dashboard()
