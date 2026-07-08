import csv
import hmac
import html
import io
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

APP_TITLE = "StudyRoom"
DB_PATH = Path(os.getenv("STUDY_ROOM_DB", "study_room.db"))
PRESENCE_TIMEOUT_MINUTES = 3
NICKNAME_MAX_WIDTH = 20
COMMENT_MAX_WIDTH = 40
FEEDBACK_MAX_CHARS = 1000
FEEDBACK_COOLDOWN_SECONDS = 30
JST = timezone(timedelta(hours=9))
ACTIVITY_OPTIONS = [
    "情報基礎A・B",
    "インターネット技術Ⅰ・Ⅱ",
    "データ構造とアルゴリズムⅠ・Ⅱ",
    "実践プログラミングⅠ・Ⅱ",
    "初級セキュアプログラミング",
    "基礎ゼミA・B",
    "資格勉強",
    "その他",
]
DETAIL_OPTIONS = [f"第{i}回" for i in range(1, 9)] + ["その他"]
MOOD_OPTIONS = ["集中して学習中", "ゆっくり学習中", "小テスト実施中", "休憩中", "もうひと頑張り"]
AVATAR_OPTIONS = ["🧑‍💻", "📖", "✏️", "🎧", "💻", "📝", "🧠", "☕"]

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📚",
    layout="wide",
)

CUSTOM_CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stSidebar"] .block-container {
    padding-top: .9rem;
}
.sidebar-brand {
    margin-bottom: .8rem;
}
.sidebar-brand h1 {
    font-size: 2rem;
    margin: 0;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 0;
}
.sidebar-brand p {
    margin: .35rem 0 0 0;
    opacity: .75;
    font-size: .88rem;
}
.sidebar-notice {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 8px;
    padding: 8px 10px;
    margin: .75rem 0 1rem 0;
    background: rgba(128,128,128,.045);
    font-size: .78rem;
    line-height: 1.45;
}
.sidebar-notice strong {
    display: block;
    font-size: .82rem;
    margin-bottom: 2px;
}
.sidebar-stats {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    margin: .75rem 0 1rem 0;
}
.sidebar-stat {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 8px;
    padding: 7px 6px;
    background: rgba(128,128,128,.045);
}
.sidebar-stat-label {
    font-size: .68rem;
    opacity: .68;
    line-height: 1.2;
}
.sidebar-stat-value {
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.25;
    margin-top: 2px;
}
.sidebar-credit {
    opacity: .55;
    font-size: .74rem;
    margin-top: 1.25rem;
    text-align: center;
}
.room-card {
    position: relative;
    border: 1px solid rgba(128,128,128,.26);
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 0;
    background:
        linear-gradient(180deg, #f8faf9 0 52px, #ffffff 52px),
        #ffffff;
    min-height: 112px;
    box-shadow: inset 0 -3px 0 rgba(128,128,128,.14);
}
.avatar {
    font-size: 1.5rem;
    width: 38px;
    height: 38px;
    min-width: 38px;
    flex: 0 0 38px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius: 12px;
    background: rgba(100,120,255,.13);
    border: 1px solid rgba(128,128,128,.18);
}
.card-top {
    display:flex;
    align-items:center;
    gap: 8px;
}
.profile-comment {
    min-width: 0;
    font-size: .68rem;
    line-height: 1.3;
    opacity: .74;
    overflow-wrap: anywhere;
}
.participant-name {
    margin-top: 8px;
    font-size: .9rem;
    line-height: 1.25;
}
.participant-detail {
    margin-top: 5px;
    font-size: .82rem;
    line-height: 1.25;
}
.desk-line {
    height: 6px;
    border-radius: 999px;
    background: rgba(128,128,128,.14);
    margin: 8px 0 6px 0;
}
.small-muted {opacity:.70; font-size:.78rem; line-height:1.25;}
.online-dot {
    display:inline-block;
    width:10px;
    height:10px;
    border-radius:50%;
    background:#2ecc71;
    margin-right:6px;
}
.activity-room {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 12px;
    padding: 14px 14px 4px 14px;
    margin: 16px 0 14px 0;
    background:
        linear-gradient(rgba(128,128,128,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(128,128,128,.028) 1px, transparent 1px),
        rgba(128,128,128,.03);
    background-size: 28px 28px;
}
.activity-room.mine {
    border-color: rgba(46,204,113,.55);
    background:
        linear-gradient(rgba(46,204,113,.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(46,204,113,.05) 1px, transparent 1px),
        rgba(46,204,113,.08);
    background-size: 28px 28px;
}
.activity-room.empty {
    opacity: .7;
}
.empty-room {
    border: 1px solid rgba(128,128,128,.18);
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
    background: rgba(128,128,128,.025);
}
.empty-room-title {
    margin: 0;
    font-size: .86rem;
    line-height: 1.25;
    font-weight: 600;
}
.empty-room-count {
    opacity: .65;
    font-size: .72rem;
    margin-top: 3px;
}
.activity-room-header {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 12px;
    padding: 12px 14px;
    margin-top: 16px;
    background: rgba(128,128,128,.035);
}
.room-desk-area {
    border: 0;
    border-radius: 0;
    padding: 8px 0 0 0;
    margin-bottom: 14px;
    background: transparent;
}
.room-heading {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom: 10px;
}
.room-heading h3 {
    margin:0;
    font-size:1.1rem;
}
.room-count {
    border: 1px solid rgba(128,128,128,.26);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: .82rem;
    opacity: .78;
    white-space: nowrap;
}
.room-tags {
    display:flex;
    align-items:center;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: flex-end;
}
.room-tag {
    border-radius: 999px;
    padding: 2px 9px;
    font-size: .78rem;
    background: rgba(99,102,241,.12);
    white-space: nowrap;
}
.room-tag.mine {
    background: rgba(46,204,113,.18);
}
.room-members {
    display:grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 14px;
}
@media (max-width: 1280px) {
    .room-members {grid-template-columns: repeat(4, minmax(0, 1fr));}
}
@media (max-width: 980px) {
    .room-members {grid-template-columns: repeat(3, minmax(0, 1fr));}
}
@media (max-width: 760px) {
    .room-members {grid-template-columns: repeat(2, minmax(0, 1fr));}
}
@media (max-width: 380px) {
    .room-members {grid-template-columns: 1fr;}
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


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
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(participants)").fetchall()}
        if "avatar" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN avatar TEXT")
        if "comment" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN comment TEXT")
        event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(presence_events)").fetchall()}
        if "comment" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN comment TEXT")
        if "mood" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN mood TEXT")


def cleanup_stale():
    cutoff = (datetime.now(JST) - timedelta(minutes=PRESENCE_TIMEOUT_MINUTES)).isoformat(timespec="seconds")
    with get_conn() as conn:
        stale_rows = conn.execute("SELECT * FROM participants WHERE last_seen < ?", (cutoff,)).fetchall()
        conn.execute("DELETE FROM participants WHERE last_seen < ?", (cutoff,))
        for row in stale_rows:
            log_presence_event(
                conn,
                "自動退室",
                row["session_id"],
                row["nickname"],
                row["activity"],
                row["detail"],
                row["comment"],
                row["mood"],
            )


def log_presence_event(conn, event_type, session_id, nickname, activity, detail, comment, mood):
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
        (event_type, session_id, nickname, activity, detail, comment, mood, room_count, total_count, now_iso()),
    )


def upsert_presence(session_id, nickname, avatar, comment, activity, detail, mood, event_type=None):
    current = now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO participants
                (session_id, nickname, avatar, comment, activity, detail, mood, joined_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                nickname=excluded.nickname,
                avatar=excluded.avatar,
                comment=excluded.comment,
                activity=excluded.activity,
                detail=excluded.detail,
                mood=excluded.mood,
                last_seen=excluded.last_seen
            """,
            (session_id, nickname, avatar, comment, activity, detail, mood, current, current),
        )
        if event_type:
            log_presence_event(conn, event_type, session_id, nickname, activity, detail, comment, mood)


def leave_room(session_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM participants WHERE session_id = ?", (session_id,)).fetchone()
        conn.execute("DELETE FROM participants WHERE session_id = ?", (session_id,))
        if row:
            log_presence_event(
                conn,
                "退室",
                row["session_id"],
                row["nickname"],
                row["activity"],
                row["detail"],
                row["comment"],
                row["mood"],
            )


def fetch_participants():
    cleanup_stale()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM participants ORDER BY activity, joined_at"
        ).fetchall()


def add_feedback(session_id, nickname, activity, detail, category, body):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO feedback
                (session_id, nickname, activity, detail, category, body, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, nickname, activity, detail, category, body[:1000], now_iso()),
        )


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


def safe_text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def text_width(value) -> int:
    return sum(1 if ord(char) <= 0x7F else 2 for char in value)


def validate_nickname(value) -> str | None:
    if not value:
        return "ニックネームを入力してください。"
    if text_width(value) > NICKNAME_MAX_WIDTH:
        return "ニックネームは全角10文字、または半角20文字以内にしてください。"
    return None


def validate_comment(value) -> str | None:
    if text_width(value) > COMMENT_MAX_WIDTH:
        return "コメントは全角20文字、または半角40文字以内にしてください。"
    return None


def validate_feedback(value) -> str | None:
    if not value:
        return "内容を入力してください。"
    if len(value) > FEEDBACK_MAX_CHARS:
        return f"内容は{FEEDBACK_MAX_CHARS}文字以内にしてください。"
    return None


def room_sort_key(activity, members):
    if st.session_state.joined and activity == st.session_state.activity:
        return (0, 0)
    if members:
        return (1, ACTIVITY_OPTIONS.index(activity) if activity in ACTIVITY_OPTIONS else 999)
    return (2, ACTIVITY_OPTIONS.index(activity) if activity in ACTIVITY_OPTIONS else 999)


def participant_sort_key(participant):
    detail = participant["detail"]
    detail_index = DETAIL_OPTIONS.index(detail) if detail in DETAIL_OPTIONS else len(DETAIL_OPTIONS)
    return (detail_index, participant["joined_at"])


def is_admin_route() -> bool:
    return st.query_params.get("admin") == "1"


def render_admin_dashboard():
    admin_password = get_admin_password()
    if not admin_password:
        st.error("管理者パスワードが設定されていません。")
        st.caption("Streamlit Community CloudのSecretsに STUDY_ROOM_ADMIN_PASSWORD を設定してください。")
        st.stop()

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.title("StudyRoom Admin")
        entered_password = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン", type="primary"):
            if hmac.compare_digest(entered_password, admin_password):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違います。")
        st.stop()

    st.title("StudyRoom Admin")
    st.caption("この画面は管理者用です。通常画面からはリンクしていません。")

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

if is_admin_route():
    render_admin_dashboard()
    st.stop()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "joined" not in st.session_state:
    st.session_state.joined = False
if "nickname" not in st.session_state:
    st.session_state.nickname = ""
if "avatar" not in st.session_state:
    st.session_state.avatar = AVATAR_OPTIONS[0]
if "comment" not in st.session_state:
    st.session_state.comment = ""
if "activity" not in st.session_state:
    st.session_state.activity = ACTIVITY_OPTIONS[0]
if "detail" not in st.session_state:
    st.session_state.detail = "第1回"
if "mood" not in st.session_state:
    st.session_state.mood = "集中して学習中"
if "last_feedback_at" not in st.session_state:
    st.session_state.last_feedback_at = None

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <h1>📚 StudyRoom</h1>
          <p>みんなのオンライン自習室</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sidebar_status = st.empty()
    st.caption("顔出し不要。今、一緒に学んでいる仲間の気配だけを感じられる場所です。")
    st.markdown(
        """
        <div class="sidebar-notice">
          <strong>試験運用中です</strong>
          表示名やコメントに、本名・学籍番号・メールアドレスなどの個人情報を書かないでください。
          ブラウザを閉じるなどして更新が止まった場合、3分後に自動退室扱いになります。
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    st.header("入室設定")
    st.caption("画面にはニックネーム、アイコン、コメント、学習中の科目が表示されます。")
    nickname = st.text_input(
        "ニックネーム",
        value=st.session_state.nickname,
        max_chars=20,
        placeholder="例：でこぴん",
        help="本名や学籍番号は入力しない運用を想定しています。全角10文字、または半角20文字以内です。",
    )
    avatar = st.selectbox(
        "アイコン",
        AVATAR_OPTIONS,
        index=AVATAR_OPTIONS.index(st.session_state.avatar)
        if st.session_state.avatar in AVATAR_OPTIONS else 0,
    )
    comment = st.text_input(
        "コメント",
        value=st.session_state.comment,
        max_chars=COMMENT_MAX_WIDTH,
        placeholder="例：試験前です",
        help="参加者カードのアイコン横に表示されます。全角20文字、または半角40文字以内です。",
    )

    activity = st.selectbox(
        "今取り組んでいること",
        ACTIVITY_OPTIONS,
        index=ACTIVITY_OPTIONS.index(st.session_state.activity)
        if st.session_state.activity in ACTIVITY_OPTIONS else 0,
    )
    detail = st.selectbox(
        "授業回",
        DETAIL_OPTIONS,
        index=DETAIL_OPTIONS.index(st.session_state.detail)
        if st.session_state.detail in DETAIL_OPTIONS else 0,
    )
    mood = st.selectbox(
        "ひとこと状態",
        MOOD_OPTIONS,
        index=MOOD_OPTIONS.index(st.session_state.mood)
        if st.session_state.mood in MOOD_OPTIONS else 0,
    )

    if not st.session_state.joined:
        if st.button("入室する", type="primary", use_container_width=True):
            cleaned = nickname.strip()
            cleaned_comment = comment.strip()
            nickname_error = validate_nickname(cleaned)
            comment_error = validate_comment(cleaned_comment)
            if nickname_error:
                st.error(nickname_error)
            elif comment_error:
                st.error(comment_error)
            else:
                st.session_state.nickname = cleaned
                st.session_state.avatar = avatar
                st.session_state.comment = cleaned_comment
                st.session_state.activity = activity
                st.session_state.detail = detail
                st.session_state.mood = mood
                st.session_state.joined = True
                upsert_presence(
                    st.session_state.session_id,
                    cleaned,
                    avatar,
                    cleaned_comment,
                    activity,
                    detail,
                    mood,
                    event_type="入室",
                )
                st.rerun()
    else:
        if st.button("学習内容を更新", use_container_width=True):
            cleaned = nickname.strip() or st.session_state.nickname
            cleaned_comment = comment.strip()
            nickname_error = validate_nickname(cleaned)
            comment_error = validate_comment(cleaned_comment)
            if nickname_error:
                st.error(nickname_error)
            elif comment_error:
                st.error(comment_error)
            else:
                st.session_state.nickname = cleaned
                st.session_state.avatar = avatar
                st.session_state.comment = cleaned_comment
                st.session_state.activity = activity
                st.session_state.detail = detail
                st.session_state.mood = mood
                upsert_presence(
                    st.session_state.session_id,
                    cleaned,
                    avatar,
                    cleaned_comment,
                    activity,
                    detail,
                    mood,
                    event_type="更新",
                )
                st.success("表示を更新しました。")

        if st.button("退室する", use_container_width=True):
            leave_room(st.session_state.session_id)
            st.session_state.joined = False
            st.rerun()

    st.divider()
    st.subheader("意見・要望")
    st.caption(
        "このフォームはプロトタイプ改善のためのものです。"
        "授業内容の質問や緊急の連絡には使用しないでください。"
    )
    with st.form("feedback_form", clear_on_submit=True):
        feedback_category = st.selectbox(
            "種類",
            ["使いやすさ", "機能要望", "不具合", "その他"],
        )
        feedback_body = st.text_area(
            "内容",
            max_chars=FEEDBACK_MAX_CHARS,
            placeholder="気づいたこと、ほしい機能、使いにくい点など",
            height=110,
        )
        feedback_submitted = st.form_submit_button("送信する", use_container_width=True)

    if feedback_submitted:
        cleaned_feedback = feedback_body.strip()
        feedback_error = validate_feedback(cleaned_feedback)
        now = datetime.now(JST)
        last_feedback_at = st.session_state.last_feedback_at
        if feedback_error:
            st.error(feedback_error)
        elif last_feedback_at and (now - last_feedback_at).total_seconds() < FEEDBACK_COOLDOWN_SECONDS:
            st.error("連続送信は少し時間をおいてからお願いします。")
        else:
            add_feedback(
                st.session_state.session_id,
                st.session_state.nickname if st.session_state.joined else "",
                st.session_state.activity if st.session_state.joined else "",
                st.session_state.detail if st.session_state.joined else "",
                feedback_category,
                cleaned_feedback,
            )
            st.session_state.last_feedback_at = now
            st.success("送信しました。ありがとうございます。")

    st.divider()
    st.markdown('<div class="sidebar-credit">Copyright 2026 Yosuke Tsuchiya</div>', unsafe_allow_html=True)


@st.fragment(run_every="10s")
def live_area():
    if st.session_state.joined:
        upsert_presence(
            st.session_state.session_id,
            st.session_state.nickname,
            st.session_state.avatar,
            st.session_state.comment,
            st.session_state.activity,
            st.session_state.detail,
            st.session_state.mood,
        )

    participants = fetch_participants()
    unique_activities = len({p["activity"] for p in participants})

    with sidebar_status.container():
        st.markdown(
            f"""
            <div class="sidebar-stats">
              <div class="sidebar-stat">
                <div class="sidebar-stat-label">学習中</div>
                <div class="sidebar-stat-value">{len(participants)}人</div>
              </div>
              <div class="sidebar-stat">
                <div class="sidebar-stat-label">部屋</div>
                <div class="sidebar-stat-value">{unique_activities}</div>
              </div>
              <div class="sidebar-stat">
                <div class="sidebar-stat-label">あなた</div>
                <div class="sidebar-stat-value">{"入室中" if st.session_state.joined else "未入室"}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("学習中の部屋")
    st.caption("ここには入室中の参加者のニックネーム、コメント、授業回、状態が表示されます。")
    if not participants:
        st.info("現在はまだ誰もいません。最初の一人として入室してみてください。")

    members_by_activity = {activity: [] for activity in ACTIVITY_OPTIONS}
    for participant in participants:
        members_by_activity.setdefault(participant["activity"], []).append(participant)

    active_rooms = [
        (activity, members)
        for activity, members in members_by_activity.items()
        if members or (st.session_state.joined and activity == st.session_state.activity)
    ]
    empty_rooms = [
        (activity, members)
        for activity, members in members_by_activity.items()
        if not members and not (st.session_state.joined and activity == st.session_state.activity)
    ]
    active_rooms.sort(key=lambda item: room_sort_key(item[0], item[1]))

    for activity, room_members in active_rooms:
        room_members = sorted(room_members, key=participant_sort_key)
        activity_text = safe_text(activity)
        is_my_room = st.session_state.joined and activity == st.session_state.activity
        room_classes = "activity-room mine" if is_my_room else "activity-room"
        room_count_text = f"{len(room_members)}人が学習中"
        tags = [f'<span class="room-count">{room_count_text}</span>']
        if is_my_room:
            tags.append('<span class="room-tag mine">あなたの部屋</span>')
        tags_html = "".join(tags)
        member_cards = []
        for p in room_members:
            mine = p["session_id"] == st.session_state.session_id
            label = f'{p["nickname"]}（あなた）' if mine else p["nickname"]
            label = safe_text(label)
            avatar_text = safe_text(p["avatar"] if p["avatar"] in AVATAR_OPTIONS else AVATAR_OPTIONS[0])
            comment_text = safe_text(p["comment"] or "一緒に学習中")
            detail_text = safe_text(p["detail"] or "学習中")
            mood_text = safe_text(p["mood"] or "学習中")
            member_cards.append(
                '<div class="room-card">'
                '<div class="card-top">'
                f'<div class="avatar">{avatar_text}</div>'
                f'<div class="profile-comment">{comment_text}</div>'
                '</div>'
                f'<div class="participant-name"><span class="online-dot"></span><strong>{label}</strong></div>'
                '<div class="desk-line"></div>'
                f'<div class="participant-detail">🗂️ {detail_text}</div>'
                f'<div class="small-muted">💬 {mood_text}</div>'
                '</div>'
            )

        members_html = "".join(member_cards)
        room_html = (
            f'<section class="{room_classes}">'
            '<div class="room-heading">'
            f'<h3>📘 {activity_text}</h3>'
            f'<div class="room-tags">{tags_html}</div>'
            '</div>'
            f'<div class="room-members">{members_html}</div>'
            '</section>'
        )
        if is_my_room:
            st.markdown(room_html, unsafe_allow_html=True)
        else:
            with st.expander(f"📘 {activity}　{room_count_text}", expanded=False):
                st.markdown(
                    f'<div class="room-desk-area"><div class="room-members">{members_html}</div></div>',
                    unsafe_allow_html=True,
                )

    if empty_rooms:
        with st.expander("空き部屋を見る", expanded=False):
            cols = st.columns(3)
            for i, (activity, _) in enumerate(empty_rooms):
                activity_text = safe_text(activity)
                with cols[i % 3]:
                    st.markdown(
                        (
                            '<section class="empty-room">'
                            f'<div class="empty-room-title">📘 {activity_text}</div>'
                            '<div class="empty-room-count">空き部屋</div>'
                            '</section>'
                        ),
                        unsafe_allow_html=True,
                    )

    st.caption("表示は10秒ごとに更新されます。顔・音声・学籍番号は表示しません。")


live_area()
