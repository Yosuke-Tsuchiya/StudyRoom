import csv
import hmac
import html
import io
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_TITLE = "StudyRoom"
DB_PATH = Path(os.getenv("STUDY_ROOM_DB", "study_room.db"))
PREFERENCES_COOKIE_NAME = "studyroom_preferences"
PRESENCE_TIMEOUT_MINUTES = 3
QUICK_JOIN_TIMEOUT_MINUTES = 60
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
DEFAULT_COMMENT = "一緒に学習中"
DEFAULT_AVATAR = "🧑‍💻"
DEFAULT_MOOD = "集中して学習中"
DEFAULT_DIFFICULTY = "表示なし"
DIFFICULTY_OPTIONS = ["表示なし", "ふつう", "やさしい", "むずかしい"]
DIFFICULTY_META = {
    "やさしい": {"score": 1, "label": "やさしい", "class": "easy"},
    "ふつう": {"score": 2, "label": "ふつう", "class": "normal"},
    "むずかしい": {"score": 3, "label": "むずかしめ", "class": "hard"},
}
QUICK_JOIN_NICKNAME = "匿名学生さん"
QUICK_JOIN_AVATAR = "📖"
QUICK_JOIN_COMMENT = DEFAULT_COMMENT
QUICK_JOIN_MOOD = DEFAULT_MOOD
QUICK_JOIN_DIFFICULTY = "表示なし"
QUICK_COURSE_CODES = {
    "info-basic": "情報基礎A・B",
    "internet-tech": "インターネット技術Ⅰ・Ⅱ",
    "data-algorithms": "データ構造とアルゴリズムⅠ・Ⅱ",
    "programming": "実践プログラミングⅠ・Ⅱ",
    "secure-programming": "初級セキュアプログラミング",
    "seminar": "基礎ゼミA・B",
    "certification": "資格勉強",
    "other": "その他",
}

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📚",
    layout="wide",
)

CUSTOM_CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(255,250,239,.94) 0 72%, rgba(236,221,195,.92) 72%),
        repeating-linear-gradient(90deg, rgba(139,96,54,.045) 0 1px, transparent 1px 34px),
        #fff8ea;
}
[data-testid="stSidebar"] .block-container {
    padding-top: .9rem;
}
.sidebar-brand {
    position: relative;
    margin: .1rem 0 .85rem 0;
    padding: 12px 13px 13px 13px;
    border: 1px solid rgba(139,96,54,.28);
    border-radius: 10px;
    background:
        linear-gradient(180deg, rgba(255,255,255,.16), rgba(104,68,32,.10)),
        linear-gradient(90deg, #c8945d, #e2bc84 42%, #c2874d);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.36),
        0 6px 14px rgba(91,62,35,.12);
    color: #3f2b1a;
}
.sidebar-brand h1 {
    font-size: 2.05rem;
    margin: 0;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 0;
    text-shadow: 0 1px 0 rgba(255,255,255,.30);
}
.sidebar-brand p {
    margin: .35rem 0 0 0;
    opacity: .82;
    font-size: .88rem;
}
.sidebar-notice {
    border: 1px solid rgba(139,96,54,.20);
    border-radius: 8px;
    padding: 9px 10px;
    margin: .75rem 0 1rem 0;
    background:
        linear-gradient(180deg, rgba(255,255,255,.78), rgba(255,252,244,.84)),
        #fffdf7;
    font-size: .78rem;
    line-height: 1.45;
    box-shadow: 0 2px 8px rgba(91,62,35,.06);
}
.sidebar-notice strong {
    display: block;
    font-size: .82rem;
    margin-bottom: 2px;
    color: #6f4a27;
}
[data-testid="InputInstructions"] {
    display: none;
}
.room-caption {
    margin: -.2rem 0 .45rem 0;
    color: #667085;
    font-size: .82rem;
    line-height: 1.35;
}
.room-caption div + div {
    margin-top: 1px;
}
.study-summary {
    border: 1px solid rgba(46,204,113,.35);
    border-radius: 8px;
    padding: 9px 10px;
    margin: .75rem 0 1rem 0;
    background: rgba(46,204,113,.08);
    font-size: .78rem;
    line-height: 1.45;
}
.study-summary strong {
    display:block;
    font-size:.86rem;
    margin-bottom:3px;
}
.study-summary ul {
    margin: 6px 0 0 1.1rem;
    padding: 0;
}
.study-summary li {
    margin: 2px 0;
}
.quick-checkin {
    border: 1px solid rgba(47,113,244,.30);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 16px;
    background: rgba(47,113,244,.08);
}
.quick-checkin h2 {
    margin: 0 0 6px 0;
    font-size: 1.35rem;
    line-height: 1.25;
}
.quick-checkin p {
    margin: 6px 0;
    line-height: 1.5;
}
.quick-checkin-subject {
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.25;
    margin: 10px 0 8px 0;
}
.quick-stats {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 12px 0;
}
.quick-recent-title {
    margin: 14px 0 6px 0;
    font-size: .9rem;
    font-weight: 700;
    color: #1f2937;
}
.quick-recent-stats {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 6px 0 12px 0;
}
.quick-stat {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 8px;
    padding: 10px;
    background: rgba(255,255,255,.55);
    color: #1f2937;
}
.quick-stat-label {
    font-size: .78rem;
    opacity: .75;
}
.quick-stat-value {
    font-size: 1.35rem;
    font-weight: 800;
    line-height: 1.2;
    margin-top: 2px;
}
.quick-link {
    display:inline-block;
    margin-top: 8px;
    font-weight: 700;
}
@media (max-width: 640px) {
    .quick-stats {grid-template-columns: 1fr;}
    .quick-recent-stats {grid-template-columns: 1fr;}
}
.sidebar-stats {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    margin: .75rem 0 1rem 0;
}
.sidebar-stat {
    border: 1px solid rgba(139,96,54,.22);
    border-radius: 8px;
    padding: 7px 6px;
    background:
        linear-gradient(180deg, rgba(255,255,255,.80), rgba(255,249,238,.86)),
        #fffaf0;
    box-shadow: 0 2px 7px rgba(91,62,35,.07);
}
.sidebar-stat-label {
    font-size: .68rem;
    color: #7a5a3a;
    line-height: 1.2;
}
.sidebar-stat-value {
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.25;
    margin-top: 2px;
    color: #4d321d;
}
.sidebar-credit {
    color: #8a735c;
    font-size: .74rem;
    margin-top: 1.25rem;
    text-align: center;
}
.room-card {
    position: relative;
    z-index: 0;
    border: 1px solid rgba(135,92,52,.45);
    border-radius: 10px 10px 8px 8px;
    padding: 0;
    margin-bottom: 0;
    background: #fffaf2;
    min-height: 108px;
    box-shadow:
        5px 7px 0 rgba(120,76,38,.18),
        0 12px 18px rgba(75,48,24,.16),
        inset -2px 0 0 rgba(120,76,38,.16),
        inset 0 -4px 0 rgba(120,76,38,.18);
    color: #24303f;
}
.room-card::before,
.room-card::after {
    content: "";
    position: absolute;
    bottom: -11px;
    width: 9px;
    height: 16px;
    border-radius: 999px;
    background:
        linear-gradient(90deg, #6f7680 0%, #a9b0b8 32%, #c8cdd3 48%, #8e98a3 74%, #626b75 100%);
    box-shadow:
        0 2px 3px rgba(52,64,84,.18),
        inset 0 -2px 0 rgba(52,64,84,.18);
    opacity: .72;
    z-index: -1;
}
.room-card::before {
    left: 24px;
}
.room-card::after {
    right: 24px;
}
.room-card.quick-checkin-card {
    border-color: rgba(102,112,133,.46);
    background: #f6f7f9;
    box-shadow:
        5px 7px 0 rgba(102,112,133,.14),
        0 12px 18px rgba(52,64,84,.12),
        inset -2px 0 0 rgba(102,112,133,.14),
        inset 0 -4px 0 rgba(102,112,133,.12);
}
.desk-surface {
    border-radius: 0 0 8px 8px;
    padding: 8px 9px 10px 9px;
    background:
        linear-gradient(180deg, rgba(255,255,255,.10), rgba(0,0,0,.06)),
        #cf8847;
    border-top: 6px solid #bd7433;
}
.quick-checkin-card .desk-surface {
    background:
        linear-gradient(180deg, rgba(255,255,255,.12), rgba(0,0,0,.06)),
        #7f8790;
    border-top-color: #667085;
}
.seat-note {
    box-sizing: border-box;
    height: 58px;
    padding: 7px 9px 6px 9px;
    background: #fffaf2;
    border-radius: 8px 8px 0 0;
    border-bottom: 1px solid rgba(135,92,52,.16);
}
.quick-checkin-card .seat-note {
    background: #f2f2ef;
}
.avatar {
    position: relative;
    font-size: 1.32rem;
    width: 34px;
    height: 34px;
    min-width: 34px;
    flex: 0 0 34px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius: 50%;
    background: #fff7df;
    border: 2px solid rgba(143,96,45,.30);
    box-shadow: 0 2px 0 rgba(143,96,45,.18);
    color: #24303f;
}
.you-badge {
    position: absolute;
    left: 50%;
    bottom: -7px;
    transform: translateX(-50%);
    border: 1px solid rgba(181,118,32,.40);
    border-radius: 999px;
    padding: 0 4px;
    background: #fff1c6;
    color: #8a4b0f;
    font-size: .48rem;
    font-weight: 800;
    line-height: 1.25;
    white-space: nowrap;
    box-shadow: 0 1px 2px rgba(16,24,40,.12);
}
.quick-checkin-card .avatar {
    background: #e7e5df;
    border-color: rgba(92,88,80,.30);
    box-shadow: 0 2px 0 rgba(92,88,80,.14);
}
.card-top {
    display:flex;
    align-items:center;
    gap: 8px;
    height: 100%;
    min-width: 0;
}
.profile-comment {
    position: relative;
    z-index: 1;
    min-width: 0;
    box-sizing: border-box;
    height: 2.55rem;
    display: flex;
    align-items: center;
    font-size: .64rem;
    line-height: 1.3;
    color: #2f241b;
    background: #fffaf2;
    border: 1px solid rgba(101,63,29,.22);
    border-radius: 11px;
    padding: 5px 7px;
    margin-bottom: 6px;
    box-shadow: 0 2px 0 rgba(101,63,29,.10);
    overflow-wrap: anywhere;
    overflow: visible;
}
.profile-comment::before {
    content: "";
    position: absolute;
    left: 15px;
    top: -8px;
    width: 0;
    height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 8px solid #fffaf2;
    z-index: 2;
    filter: drop-shadow(0 -1px 0 rgba(101,63,29,.16));
}
.quick-checkin-card .profile-comment {
    background: #f2f2ef;
}
.quick-checkin-card .profile-comment::before {
    border-bottom-color: #f2f2ef;
}
.participant-name {
    margin: 0;
    padding: 0;
    font-size: .76rem;
    line-height: 1.25;
    color: #241a12;
    text-align: left;
    min-width: 0;
    flex: 1 1 auto;
    overflow-wrap: anywhere;
}
.participant-name strong {
    display: block;
    white-space: normal;
}
.participant-detail {
    font-size: .76rem;
    line-height: 1.25;
    color: #344054;
    min-width: 0;
    overflow-wrap: anywhere;
}
.desk-info-row {
    display: grid;
    grid-template-columns: 1.15rem minmax(0, 1fr);
    align-items: center;
    column-gap: 2px;
    color: #fff8e8;
    font-size: .72rem;
    line-height: 1.25;
    opacity: .96;
    text-shadow: 0 1px 0 rgba(70,38,16,.28);
    min-height: 1.1rem;
}
.desk-info-icon {
    width: 1.15rem;
    text-align: center;
    font-size: .74rem;
    line-height: 1;
}
.desk-info-text {
    min-width: 0;
    overflow-wrap: anywhere;
}
.desk-info-line {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
    min-height: 1.1rem;
}
.desk-line {
    display: none;
}
.small-muted {color: #475467; opacity:.78; font-size:.72rem; line-height:1.25;}
.desk-surface .small-muted,
.desk-surface .participant-detail {
    color: #fff8e8;
    opacity: .96;
    text-shadow: 0 1px 0 rgba(70,38,16,.28);
}
.card-meta-row {
    display:block;
    margin-top: 4px;
}
.card-difficulty {
    display:inline-block;
    flex: 0 0 auto;
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 999px;
    padding: 1px 5px;
    font-size: .58rem;
    font-weight: 700;
    line-height: 1.25;
}
.card-difficulty.placeholder {
    visibility: hidden;
}
.card-difficulty.easy {
    color: #067647;
    background: #d9f8e8;
    border-color: rgba(18,183,106,.30);
}
.card-difficulty.normal {
    color: #175cd3;
    background: #dceaff;
    border-color: rgba(47,113,244,.26);
}
.card-difficulty.hard {
    color: #b42318;
    background: #ffe1de;
    border-color: rgba(240,68,56,.28);
}
.activity-room {
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(104,82,58,.24);
    border-radius: 16px;
    padding: 14px 16px 10px 16px;
    margin: 18px 0 18px 0;
    background:
        linear-gradient(180deg, rgba(247,241,225,.96) 0 260px, rgba(226,199,160,.95) 260px),
        linear-gradient(90deg, rgba(255,255,255,.45) 0 1px, transparent 1px),
        #f6efdd;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.70), 0 12px 28px rgba(65,50,34,.12);
}
.activity-room::before {
    content: "";
    position: absolute;
    top: 18px;
    right: 18px;
    width: min(28%, 190px);
    height: 56px;
    border: 5px solid rgba(255,255,255,.88);
    border-radius: 8px;
    background:
        linear-gradient(90deg, transparent calc(50% - 2px), rgba(255,255,255,.90) calc(50% - 2px) calc(50% + 2px), transparent calc(50% + 2px)),
        linear-gradient(180deg, #c7e8ff 0 48%, #8dc7ef 48% 52%, #d8f0ff 52%);
    box-shadow: 0 4px 10px rgba(91,116,137,.18);
    opacity: .8;
}
.activity-room::after {
    content: "";
    position: absolute;
    left: -8%;
    right: -8%;
    bottom: -28px;
    height: 42%;
    background:
        repeating-linear-gradient(90deg, rgba(128,88,45,.12) 0 2px, transparent 2px 72px),
        linear-gradient(180deg, rgba(205,157,96,.16), rgba(151,93,43,.22));
    transform: perspective(620px) rotateX(58deg);
    transform-origin: bottom;
    pointer-events: none;
}
.activity-room > * {
    position: relative;
    z-index: 1;
}
.activity-room.mine {
    border-color: rgba(181,118,32,.44);
    background:
        linear-gradient(180deg, rgba(250,244,230,.98) 0 260px, rgba(222,199,157,.94) 260px),
        #f7eed8;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.74), 0 14px 30px rgba(120,76,38,.13);
}
.activity-room.empty {
    opacity: .7;
}
.empty-room {
    border: 1px solid rgba(152,162,179,.18);
    border-radius: 8px;
    padding: 7px 9px;
    margin-bottom: 8px;
    background: rgba(152,162,179,.045);
    color: #667085;
}
.empty-room-title {
    margin: 0;
    font-size: .8rem;
    line-height: 1.25;
    font-weight: 500;
}
.empty-room-count {
    opacity: .58;
    font-size: .68rem;
    margin-top: 3px;
}
.activity-room-header {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 12px;
    padding: 12px 14px;
    margin-top: 16px;
    background: rgba(128,128,128,.035);
}
[data-testid="stMain"] [data-testid="stExpander"] details {
    border: 1px solid rgba(115,88,55,.28);
    border-radius: 14px;
    overflow: hidden;
    background:
        linear-gradient(180deg, rgba(238,225,202,.72), rgba(221,203,173,.82)),
        repeating-linear-gradient(90deg, rgba(255,255,255,.22) 0 1px, transparent 1px 42px);
    box-shadow: 0 8px 18px rgba(82,61,38,.10);
}
[data-testid="stMain"] [data-testid="stExpander"] summary {
    min-height: 46px;
    border-left: 12px solid #8c6036;
    background:
        linear-gradient(90deg, #b98248 0 16px, #e7c793 16px 18px, #f3dfbd 18px),
        #f3dfbd;
    color: #3b2a1b;
    font-weight: 700;
}
[data-testid="stMain"] [data-testid="stExpander"] summary:hover {
    background:
        linear-gradient(90deg, #a8733d 0 16px, #e7c793 16px 18px, #f7e7ca 18px),
        #f7e7ca;
}
[data-testid="stMain"] [data-testid="stExpander"] details:has(.empty-rooms-panel) {
    border: 1px solid rgba(152,162,179,.24);
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(248,250,252,.86), rgba(238,242,247,.88));
    box-shadow: 0 6px 14px rgba(52,64,84,.08);
}
[data-testid="stMain"] [data-testid="stExpander"] details:has(.empty-rooms-panel) summary {
    min-height: 42px;
    border-left: 8px solid rgba(102,112,133,.38);
    background: rgba(248,250,252,.94);
    color: #475467;
    font-weight: 650;
}
[data-testid="stMain"] [data-testid="stExpander"] details:has(.empty-rooms-panel) summary:hover {
    background: rgba(242,244,247,.96);
}
.empty-rooms-panel {
    height: 0;
    overflow: hidden;
}
[data-testid="stMain"] [data-testid="stExpander"] details:has(.room-desk-area) {
    background:
        linear-gradient(180deg, rgba(250,246,234,.92) 0 230px, rgba(213,193,161,.48) 230px 233px, rgba(235,222,201,.78) 233px),
        #f6efe1;
}
.room-desk-area {
    position: relative;
    overflow: hidden;
    border: 0;
    border-radius: 0;
    padding: 18px 16px 6px 16px;
    margin: 0 0 14px 0;
    background: transparent;
    box-shadow: none;
}
.room-desk-area::before {
    content: none;
}
.room-desk-area::after {
    content: "";
    position: absolute;
    top: 18px;
    left: 18px;
    right: 18px;
    height: 112px;
    background:
        linear-gradient(90deg, transparent 0 4px, rgba(199,207,216,.92) 4px 124px, transparent 124px),
        linear-gradient(90deg, transparent 0 4px, rgba(174,150,118,.34) 4px 124px, transparent 124px),
        linear-gradient(90deg, rgba(185,196,207,.90) 0 4px, transparent 4px 60px, rgba(185,196,207,.72) 60px 64px, transparent 64px 120px, rgba(185,196,207,.90) 120px 124px, transparent 124px),
        linear-gradient(90deg, transparent 0 4px, rgba(185,196,207,.70) 4px 124px, transparent 124px),
        linear-gradient(115deg, transparent 0 12%, rgba(255,255,255,.38) 12% 18%, transparent 18% 32%, rgba(255,255,255,.26) 32% 38%, transparent 38%),
        radial-gradient(circle at 12% 14%, rgba(255,255,255,.32), transparent 18%),
        linear-gradient(90deg, transparent 0 4px, rgba(222,240,248,.70) 4px 60px, rgba(255,255,255,.38) 60px 68px, rgba(222,240,248,.58) 68px 120px, transparent 120px);
    background-repeat: repeat-x;
    background-size: 158px 6px, 158px 8px, 158px 112px, 158px 4px, 158px 112px, 158px 112px, 158px 112px;
    background-position: 0 0, 0 104px, 0 0, 0 51px, 0 0, 0 0, 0 0;
    filter: drop-shadow(0 8px 12px rgba(73,63,50,.08));
    pointer-events: none;
}
.room-desk-area > * {
    position: relative;
    z-index: 1;
}
.room-desk-area .room-members {
    margin-top: -12px;
}
.room-heading {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom: 14px;
    min-height: 58px;
    padding: 10px 12px;
    border: 6px solid #a67c52;
    border-radius: 12px;
    background:
        linear-gradient(180deg, rgba(255,255,255,.08), rgba(0,0,0,.06)),
        #295f4e;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 5px 0 rgba(96,64,35,.22);
    color: #fff8dc;
}
.room-heading h3 {
    margin:0;
    font-size:1.08rem;
    color: #fff8dc;
    text-shadow: 0 1px 0 rgba(0,0,0,.18);
}
.room-count {
    border: 1px solid rgba(255,255,255,.28);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: .82rem;
    background: rgba(255,255,255,.14);
    color: #fff8dc;
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
    background: rgba(255,255,255,.13);
    color: #fff8dc;
    white-space: nowrap;
}
.room-tag.mine {
    background: rgba(255,236,153,.24);
}
.room-tag.recent {
    background: rgba(255,255,255,.10);
    color: #e6f5ee;
}
.room-members {
    display:grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 16px 10px;
    margin: 18px 0 16px 0;
}
@media (max-width: 1280px) {
    .room-members {grid-template-columns: repeat(4, minmax(0, 1fr));}
}
@media (max-width: 980px) {
    .room-members {grid-template-columns: repeat(3, minmax(0, 1fr));}
}
@media (max-width: 760px) {
    .room-members {grid-template-columns: repeat(2, minmax(0, 1fr));}
    .room-heading {
        align-items:flex-start;
        flex-direction: column;
        gap: 6px;
    }
    .room-heading h3 {
        font-size: 1rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    .room-tags {
        justify-content: flex-start;
    }
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
                difficulty TEXT,
                participation_type TEXT,
                expires_at TEXT,
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
                difficulty TEXT,
                participation_type TEXT,
                room_count INTEGER NOT NULL,
                total_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS study_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                activity TEXT NOT NULL,
                detail TEXT,
                participation_type TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(participants)").fetchall()}
        if "avatar" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN avatar TEXT")
        if "comment" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN comment TEXT")
        if "difficulty" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN difficulty TEXT")
        if "participation_type" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN participation_type TEXT")
        if "expires_at" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN expires_at TEXT")
        event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(presence_events)").fetchall()}
        if "comment" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN comment TEXT")
        if "mood" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN mood TEXT")
        if "difficulty" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN difficulty TEXT")
        if "participation_type" not in event_columns:
            conn.execute("ALTER TABLE presence_events ADD COLUMN participation_type TEXT")


def cleanup_stale():
    cutoff = (datetime.now(JST) - timedelta(minutes=PRESENCE_TIMEOUT_MINUTES)).isoformat(timespec="seconds")
    current = now_iso()
    with get_conn() as conn:
        stale_rows = conn.execute(
            """
            SELECT * FROM participants
            WHERE
                (
                    COALESCE(participation_type, 'regular') = 'quick'
                    AND expires_at IS NOT NULL
                    AND expires_at < ?
                )
                OR
                (
                    COALESCE(participation_type, 'regular') != 'quick'
                    AND last_seen < ?
                )
            """,
            (current, cutoff),
        ).fetchall()
        conn.execute(
            """
            DELETE FROM participants
            WHERE
                (
                    COALESCE(participation_type, 'regular') = 'quick'
                    AND expires_at IS NOT NULL
                    AND expires_at < ?
                )
                OR
                (
                    COALESCE(participation_type, 'regular') != 'quick'
                    AND last_seen < ?
                )
            """,
            (current, cutoff),
        )
        for row in stale_rows:
            segment_ended_at = row["expires_at"] if (row["participation_type"] or "regular") == "quick" else row["last_seen"]
            close_open_study_segment(conn, row["session_id"], segment_ended_at)
            log_presence_event(
                conn,
                "自動退室",
                row["session_id"],
                row["nickname"],
                row["activity"],
                row["detail"],
                row["comment"],
                row["mood"],
                row["difficulty"],
                row["participation_type"] or "regular",
            )


def log_presence_event(
    conn,
    event_type,
    session_id,
    nickname,
    activity,
    detail,
    comment,
    mood,
    difficulty,
    participation_type="regular",
):
    room_count = conn.execute(
        "SELECT COUNT(*) FROM participants WHERE activity = ?",
        (activity,),
    ).fetchone()[0]
    total_count = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
    conn.execute(
        """
        INSERT INTO presence_events
            (
                event_type, session_id, nickname, activity, detail, comment,
                mood, difficulty, participation_type, room_count, total_count, created_at
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            session_id,
            nickname,
            activity,
            detail,
            comment,
            mood,
            difficulty,
            participation_type,
            room_count,
            total_count,
            now_iso(),
        ),
    )


def close_open_study_segment(conn, session_id, ended_at=None):
    conn.execute(
        """
        UPDATE study_segments
        SET ended_at = ?
        WHERE session_id = ? AND ended_at IS NULL
        """,
        (ended_at or now_iso(), session_id),
    )


def start_study_segment(conn, session_id, activity, detail, participation_type="regular", started_at=None):
    conn.execute(
        """
        INSERT INTO study_segments
            (session_id, activity, detail, participation_type, started_at, ended_at)
        VALUES (?, ?, ?, ?, ?, NULL)
        """,
        (
            session_id,
            activity,
            detail,
            participation_type,
            started_at or now_iso(),
        ),
    )


def switch_study_segment(session_id, activity, detail, participation_type="regular"):
    current = now_iso()
    with get_conn() as conn:
        close_open_study_segment(conn, session_id, current)
        start_study_segment(conn, session_id, activity, detail, participation_type, current)


def format_duration_seconds(total_seconds) -> str:
    total_seconds = max(0, int(total_seconds))
    total_minutes = total_seconds // 60
    if total_minutes < 1:
        return "1分未満"
    if total_minutes < 60:
        return f"{total_minutes}分"

    hours, minutes = divmod(total_minutes, 60)
    if minutes == 0:
        return f"{hours}時間"
    return f"{hours}時間{minutes}分"


def study_summary_from_segments(session_id, since) -> dict | None:
    current = now_iso()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT activity, detail, started_at, COALESCE(ended_at, ?) AS ended_at
            FROM study_segments
            WHERE session_id = ? AND started_at >= ?
            ORDER BY started_at
            """,
            (current, session_id, since),
        ).fetchall()

    total_seconds = 0
    breakdown = {}
    for row in rows:
        started_at = parse_iso_datetime(row["started_at"])
        ended_at = parse_iso_datetime(row["ended_at"])
        if not started_at or not ended_at or ended_at < started_at:
            continue
        raw_seconds = (ended_at - started_at).total_seconds()
        if raw_seconds <= 0:
            continue
        seconds = max(1, int(raw_seconds))
        key = (row["activity"], row["detail"] or "学習中")
        breakdown[key] = breakdown.get(key, 0) + seconds
        total_seconds += seconds

    if total_seconds <= 0:
        return None

    return {
        "total_label": format_duration_seconds(total_seconds),
        "items": [
            {
                "activity": activity,
                "detail": detail,
                "duration_label": format_duration_seconds(seconds),
            }
            for (activity, detail), seconds in breakdown.items()
        ],
    }


def upsert_presence(
    session_id,
    nickname,
    avatar,
    comment,
    activity,
    detail,
    mood,
    difficulty,
    event_type=None,
    participation_type="regular",
    expires_at=None,
):
    current = now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO participants
                (
                    session_id, nickname, avatar, comment, activity, detail,
                    mood, difficulty, participation_type, expires_at, joined_at, last_seen
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                nickname=excluded.nickname,
                avatar=excluded.avatar,
                comment=excluded.comment,
                activity=excluded.activity,
                detail=excluded.detail,
                mood=excluded.mood,
                difficulty=excluded.difficulty,
                participation_type=excluded.participation_type,
                expires_at=excluded.expires_at,
                last_seen=excluded.last_seen
            """,
            (
                session_id,
                nickname,
                avatar,
                comment,
                activity,
                detail,
                mood,
                difficulty,
                participation_type,
                expires_at,
                current,
                current,
            ),
        )
        if event_type:
            if event_type == "入室":
                close_open_study_segment(conn, session_id, current)
                start_study_segment(conn, session_id, activity, detail, participation_type, current)
            log_presence_event(
                conn,
                event_type,
                session_id,
                nickname,
                activity,
                detail,
                comment,
                mood,
                difficulty,
                participation_type,
            )


def leave_room(session_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM participants WHERE session_id = ?", (session_id,)).fetchone()
        conn.execute("DELETE FROM participants WHERE session_id = ?", (session_id,))
        if row:
            closed_at = now_iso()
            close_open_study_segment(conn, session_id, closed_at)
            log_presence_event(
                conn,
                "退室",
                row["session_id"],
                row["nickname"],
                row["activity"],
                row["detail"],
                row["comment"],
                row["mood"],
                row["difficulty"],
                row["participation_type"] or "regular",
            )
            conn.commit()
            return study_summary_from_segments(session_id, row["joined_at"])
    return None


def quick_cleanup_where(activity=None, detail=None):
    clauses = ["COALESCE(participation_type, 'regular') = 'quick'"]
    params = []
    if activity:
        clauses.append("activity = ?")
        params.append(activity)
    if detail:
        clauses.append("detail = ?")
        params.append(detail)
    return " AND ".join(clauses), params


def count_quick_participants(activity=None, detail=None):
    where_sql, params = quick_cleanup_where(activity, detail)
    with get_conn() as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM participants WHERE {where_sql}",
            params,
        ).fetchone()[0]


def force_leave_quick_participants(activity=None, detail=None):
    where_sql, params = quick_cleanup_where(activity, detail)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM participants WHERE {where_sql} ORDER BY activity, detail, joined_at",
            params,
        ).fetchall()
        if not rows:
            return 0

        session_ids = [row["session_id"] for row in rows]
        placeholders = ",".join("?" for _ in session_ids)
        conn.execute(
            f"DELETE FROM participants WHERE session_id IN ({placeholders})",
            session_ids,
        )
        closed_at = now_iso()
        for row in rows:
            close_open_study_segment(conn, row["session_id"], closed_at)
            log_presence_event(
                conn,
                "管理者退室",
                row["session_id"],
                row["nickname"],
                row["activity"],
                row["detail"],
                row["comment"],
                row["mood"],
                row["difficulty"],
                row["participation_type"] or "quick",
            )
        return len(rows)


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


def get_config_value(name) -> str:
    env_value = os.getenv(name, "").strip()
    if env_value:
        return env_value
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def send_feedback_webhook(payload) -> tuple[bool, str]:
    webhook_url = get_config_value("FEEDBACK_WEBHOOK_URL")
    if not webhook_url:
        return True, ""

    token = get_config_value("FEEDBACK_WEBHOOK_TOKEN")
    body = dict(payload)
    if token:
        body["token"] = token

    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if 200 <= response.status < 300:
                return True, ""
            return False, f"送信先からエラーが返りました。status={response.status}"
    except urllib.error.URLError as exc:
        return False, f"送信先に接続できませんでした。{exc}"


def get_admin_password() -> str:
    return get_config_value("STUDY_ROOM_ADMIN_PASSWORD")


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
            "difficulty",
            "participation_type",
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
                csv_safe(row["difficulty"]),
                csv_safe(row["participation_type"]),
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
        current_quick = conn.execute(
            "SELECT COUNT(*) FROM participants WHERE COALESCE(participation_type, 'regular') = 'quick'"
        ).fetchone()[0]
        current_regular = current_total - current_quick
        feedback_total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        event_total = conn.execute("SELECT COUNT(*) FROM presence_events").fetchone()[0]
        active_rooms = conn.execute(
            """
            SELECT
                activity,
                COUNT(*) AS count,
                SUM(CASE WHEN COALESCE(participation_type, 'regular') = 'quick' THEN 1 ELSE 0 END) AS quick_count,
                SUM(CASE WHEN COALESCE(participation_type, 'regular') != 'quick' THEN 1 ELSE 0 END) AS regular_count
            FROM participants
            GROUP BY activity
            ORDER BY count DESC, activity
            """
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
    return current_total, current_regular, current_quick, feedback_total, event_total, active_rooms, join_counts


def safe_text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def normalize_difficulty(value) -> str:
    if value == "やさしめ":
        return "やさしい"
    if value in DIFFICULTY_OPTIONS:
        return value
    return DEFAULT_DIFFICULTY


def load_saved_preferences() -> dict:
    context = getattr(st, "context", None)
    cookies = getattr(context, "cookies", {}) if context else {}
    raw_value = cookies.get(PREFERENCES_COOKIE_NAME, "") if cookies else ""
    if not raw_value:
        return {}
    try:
        preferences = json.loads(urllib.parse.unquote(raw_value))
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(preferences, dict):
        return {}
    return preferences


def saved_value(preferences, key, default, allowed=None):
    value = str(preferences.get(key, "") or "")
    if allowed is not None and value not in allowed:
        return default
    return value or default


def persist_preferences_to_browser(preferences):
    payload = json.dumps(preferences, ensure_ascii=False)
    payload_literal = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    cookie_name = json.dumps(PREFERENCES_COOKIE_NAME)
    components.html(
        f"""
        <script>
        const cookieName = {cookie_name};
        const preferences = JSON.parse({payload_literal});
        const encoded = encodeURIComponent(JSON.stringify(preferences));
        document.cookie = `${{cookieName}}=${{encoded}}; max-age=31536000; path=/; SameSite=Lax`;
        </script>
        """,
        height=0,
        width=0,
    )


def current_preferences() -> dict:
    return {
        "session_id": st.session_state.session_id,
        "nickname": st.session_state.nickname,
        "avatar": st.session_state.avatar,
        "comment": st.session_state.comment,
        "activity": st.session_state.activity,
        "detail": st.session_state.detail,
        "mood": st.session_state.mood,
        "difficulty": st.session_state.difficulty,
    }


def query_value(name) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def valid_session_id(value) -> str | None:
    try:
        return str(uuid.UUID(str(value or "")))
    except ValueError:
        return None


def sync_session_id_to_url():
    if query_value("quick").lower() in {"1", "true", "yes"}:
        return
    if query_value("sid") != st.session_state.session_id:
        st.query_params["sid"] = st.session_state.session_id


def lesson_to_detail(value) -> str | None:
    cleaned = value.strip()
    if cleaned.isdigit():
        number = int(cleaned)
        if 1 <= number <= 8:
            return f"第{number}回"
    if cleaned in DETAIL_OPTIONS:
        return cleaned
    if cleaned.lower() in {"other", "etc"}:
        return "その他"
    return None


def get_course_lesson_request() -> dict | None:
    course_code = query_value("course").strip().lower()
    activity = QUICK_COURSE_CODES.get(course_code)
    detail = lesson_to_detail(query_value("lesson"))

    if not course_code and not query_value("lesson"):
        return None

    if not activity or not detail:
        return {
            "error": "リンクの科目または授業回の指定が正しくありません。授業ページのリンクを確認してください。",
        }

    return {
        "course_code": course_code,
        "activity": activity,
        "detail": detail,
    }


def get_quick_join_request() -> dict | None:
    if query_value("quick").lower() not in {"1", "true", "yes"}:
        return None
    request = get_course_lesson_request()
    if request is None:
        return {
            "error": "簡易参加リンクの科目または授業回の指定がありません。授業ページのリンクを確認してください。",
        }
    return request


def build_main_page_url(course_code, detail, takeover_id=None) -> str:
    lesson_value = "other"
    if detail in DETAIL_OPTIONS:
        detail_index = DETAIL_OPTIONS.index(detail)
        if 0 <= detail_index < 8:
            lesson_value = str(detail_index + 1)
    query_params = {"course": course_code, "lesson": lesson_value}
    if takeover_id:
        query_params["takeover"] = takeover_id
    query = urllib.parse.urlencode(query_params)
    return f"/?{query}"


def fetch_activity_detail_counts(activity, detail):
    cleanup_stale()
    with get_conn() as conn:
        total_count = conn.execute(
            "SELECT COUNT(*) FROM participants",
        ).fetchone()[0]
        activity_count = conn.execute(
            "SELECT COUNT(*) FROM participants WHERE activity = ?",
            (activity,),
        ).fetchone()[0]
        detail_count = conn.execute(
            "SELECT COUNT(*) FROM participants WHERE activity = ? AND detail = ?",
            (activity, detail),
        ).fetchone()[0]
    return total_count, activity_count, detail_count


def fetch_recent_activity_entry_counts(activity):
    current = datetime.now(JST)
    cutoffs = {
        "24h": (current - timedelta(hours=24)).isoformat(timespec="seconds"),
        "7d": (current - timedelta(days=7)).isoformat(timespec="seconds"),
    }
    with get_conn() as conn:
        return {
            key: conn.execute(
                """
                SELECT COUNT(*)
                FROM presence_events
                WHERE event_type = '入室'
                  AND activity = ?
                  AND created_at >= ?
                """,
                (activity, cutoff),
            ).fetchone()[0]
            for key, cutoff in cutoffs.items()
        }


def fetch_participant(session_id):
    if not session_id:
        return None
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM participants WHERE session_id = ?",
            (session_id,),
        ).fetchone()


def parse_iso_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def elapsed_study_time(joined_at) -> str:
    joined_dt = parse_iso_datetime(str(joined_at or ""))
    if not joined_dt:
        return "入室から計測中"

    elapsed = datetime.now(JST) - joined_dt
    total_minutes = max(0, int(elapsed.total_seconds() // 60))
    if total_minutes < 1:
        return "入室から1分未満"
    if total_minutes < 60:
        return f"入室から{total_minutes}分"

    hours, minutes = divmod(total_minutes, 60)
    if minutes == 0:
        return f"入室から{hours}時間"
    return f"入室から{hours}時間{minutes}分"


def remaining_checkin_time(expires_at) -> str:
    expires_dt = parse_iso_datetime(str(expires_at or ""))
    if not expires_dt:
        return "残り時間を確認中"

    remaining = expires_dt - datetime.now(JST)
    remaining_seconds = max(0, int(remaining.total_seconds()))
    if remaining_seconds < 60:
        return "あと1分未満"

    total_minutes = (remaining_seconds + 59) // 60
    return f"あと{total_minutes}分"


def render_study_summary(summary):
    if not summary:
        return

    items_html = "".join(
        (
            "<li>"
            f"{safe_text(item['activity'])} {safe_text(item['detail'])}: "
            f"{safe_text(item['duration_label'])}"
            "</li>"
        )
        for item in summary["items"]
    )
    st.markdown(
        f"""
        <div class="study-summary">
          <strong>おつかれさまでした</strong>
          今回は{safe_text(summary["total_label"])}、学習に取り組みました。
          <ul>{items_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quick_checkin_panel(request):
    if not request or request.get("error"):
        return

    activity = request["activity"]
    detail = request["detail"]
    total_count, activity_count, detail_count = fetch_activity_detail_counts(activity, detail)
    recent_counts = fetch_recent_activity_entry_counts(activity)
    main_page_url = build_main_page_url(request["course_code"], detail, st.session_state.session_id)
    st.markdown(
        f"""
        <section class="quick-checkin">
          <h2>チェックインしました</h2>
          <p class="quick-checkin-subject">{safe_text(activity)} {safe_text(detail)}</p>
          <div class="quick-stats">
            <div class="quick-stat">
              <div class="quick-stat-label">StudyRoom全体</div>
              <div class="quick-stat-value">{total_count}人</div>
            </div>
            <div class="quick-stat">
              <div class="quick-stat-label">この科目を学習中</div>
              <div class="quick-stat-value">{activity_count}人</div>
            </div>
            <div class="quick-stat">
              <div class="quick-stat-label">この授業回を学習中</div>
              <div class="quick-stat-value">{detail_count}人</div>
            </div>
          </div>
          <div class="quick-recent-title">この科目の最近の入室</div>
          <div class="quick-recent-stats">
            <div class="quick-stat">
              <div class="quick-stat-label">24時間以内</div>
              <div class="quick-stat-value">{recent_counts["24h"]}人</div>
            </div>
            <div class="quick-stat">
              <div class="quick-stat-label">7日以内</div>
              <div class="quick-stat-value">{recent_counts["7d"]}人</div>
            </div>
          </div>
          <p>{QUICK_JOIN_TIMEOUT_MINUTES}分間、この授業回を学習中の匿名の学生として表示されます。</p>
          <p>授業動画のタブに戻って、学習を続けてください。このタブは閉じても大丈夫です。</p>
          <p>表示名をニックネームに変更したり、学習時間を記録したい場合は、StudyRoomを開いてください。</p>
          <a class="quick-link" href="{safe_text(main_page_url)}" target="_self">StudyRoomを開く</a>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_quick_checkin_page(request, error=None):
    st.markdown(
        """
        <div class="sidebar-brand">
          <h1>📚 StudyRoom</h1>
          <p>みんなのオンライン自習室</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "ここは発言しなくても参加できる自習室です。"
        "顔出し・音声・チャットなしで、同じ時間に学んでいる人の気配だけを感じられます。"
    )
    if error:
        st.error(error)
        return
    render_quick_checkin_panel(request)


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

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        if st.button("最新の状態に更新", type="primary", use_container_width=True):
            st.rerun()
    with action_col2:
        if st.button("ログアウト", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

    current_total, current_regular, current_quick, feedback_total, event_total, active_rooms, join_counts = fetch_admin_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("現在の入室者", f"{current_total}人", f"通常 {current_regular} / 簡易 {current_quick}")
    c2.metric("意見・要望", f"{feedback_total}件")
    c3.metric("入退室履歴", f"{event_total}件")
    cleanup_message = st.session_state.pop("admin_cleanup_message", None)
    if cleanup_message:
        st.success(cleanup_message)

    overview_tab, events_tab, feedback_tab = st.tabs(["利用状況", "入退室履歴", "意見・要望"])

    with overview_tab:
        left, right = st.columns(2)
        with left:
            st.subheader("現在の部屋別人数")
            if active_rooms:
                st.dataframe(
                    [
                        {
                            "部屋": row["activity"],
                            "合計": row["count"],
                            "通常入室": row["regular_count"],
                            "簡易入室": row["quick_count"],
                        }
                        for row in active_rooms
                    ],
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

        st.divider()
        st.subheader("簡易参加の整理")
        st.caption("授業ページからチェックインした匿名学生だけを対象に、強制的に退室扱いにします。通常入室の学生には影響しません。")
        cleanup_scope = st.radio(
            "対象範囲",
            ["すべての簡易参加", "科目を指定", "科目と授業回を指定"],
            horizontal=True,
        )
        cleanup_activity = None
        cleanup_detail = None
        if cleanup_scope in {"科目を指定", "科目と授業回を指定"}:
            cleanup_activity = st.selectbox("科目", ACTIVITY_OPTIONS, key="admin_cleanup_activity")
        if cleanup_scope == "科目と授業回を指定":
            cleanup_detail = st.selectbox("授業回", DETAIL_OPTIONS, key="admin_cleanup_detail")

        target_count = count_quick_participants(cleanup_activity, cleanup_detail)
        st.info(f"対象の簡易参加: {target_count}人")
        confirm_cleanup = st.checkbox(
            "対象の簡易参加を退室させることを確認しました",
            key="admin_cleanup_confirm",
        )
        if st.button(
            "対象の簡易参加を退室させる",
            disabled=(target_count == 0 or not confirm_cleanup),
            use_container_width=True,
        ):
            removed_count = force_leave_quick_participants(cleanup_activity, cleanup_detail)
            st.session_state.admin_cleanup_message = f"{removed_count}人の簡易参加を退室扱いにしました。"
            st.rerun()

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
                        "体感難易度": row["difficulty"] or "",
                        "参加方法": row["participation_type"] or "regular",
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

saved_preferences = load_saved_preferences()
course_lesson_request = get_course_lesson_request()

if "session_id" not in st.session_state:
    query_session_id = valid_session_id(query_value("sid"))
    saved_session_id = valid_session_id(saved_value(saved_preferences, "session_id", ""))
    st.session_state.session_id = query_session_id or saved_session_id or str(uuid.uuid4())
if "joined" not in st.session_state:
    st.session_state.joined = False
if "nickname" not in st.session_state:
    st.session_state.nickname = saved_value(saved_preferences, "nickname", "")
if "avatar" not in st.session_state:
    st.session_state.avatar = saved_value(saved_preferences, "avatar", DEFAULT_AVATAR, AVATAR_OPTIONS)
if "comment" not in st.session_state:
    st.session_state.comment = saved_value(saved_preferences, "comment", DEFAULT_COMMENT)
if "activity" not in st.session_state:
    st.session_state.activity = saved_value(saved_preferences, "activity", ACTIVITY_OPTIONS[0], ACTIVITY_OPTIONS)
if "detail" not in st.session_state:
    st.session_state.detail = saved_value(saved_preferences, "detail", "第1回", DETAIL_OPTIONS)
if "mood" not in st.session_state:
    st.session_state.mood = saved_value(saved_preferences, "mood", DEFAULT_MOOD, MOOD_OPTIONS)
if "difficulty" not in st.session_state:
    st.session_state.difficulty = normalize_difficulty(saved_value(saved_preferences, "difficulty", DEFAULT_DIFFICULTY))
if "participation_type" not in st.session_state:
    st.session_state.participation_type = "regular"
if "expires_at" not in st.session_state:
    st.session_state.expires_at = None
if "quick_join_registered_key" not in st.session_state:
    st.session_state.quick_join_registered_key = None
if "takeover_loaded_id" not in st.session_state:
    st.session_state.takeover_loaded_id = None
if "last_study_summary" not in st.session_state:
    st.session_state.last_study_summary = None
if "last_feedback_at" not in st.session_state:
    st.session_state.last_feedback_at = None

existing_participant = fetch_participant(st.session_state.session_id)
if existing_participant and not st.session_state.joined:
    st.session_state.nickname = existing_participant["nickname"] or st.session_state.nickname
    st.session_state.avatar = existing_participant["avatar"] or st.session_state.avatar
    st.session_state.comment = existing_participant["comment"] or st.session_state.comment
    st.session_state.activity = existing_participant["activity"] or st.session_state.activity
    st.session_state.detail = existing_participant["detail"] or st.session_state.detail
    st.session_state.mood = existing_participant["mood"] or st.session_state.mood
    st.session_state.difficulty = normalize_difficulty(existing_participant["difficulty"])
    st.session_state.participation_type = existing_participant["participation_type"] or "regular"
    st.session_state.expires_at = existing_participant["expires_at"]
    st.session_state.joined = True

takeover_id = query_value("takeover").strip()
if (
    takeover_id
    and takeover_id != st.session_state.session_id
    and takeover_id != st.session_state.takeover_loaded_id
):
    takeover_row = fetch_participant(takeover_id)
    if takeover_row:
        st.session_state.session_id = takeover_row["session_id"]
        st.session_state.nickname = takeover_row["nickname"] or QUICK_JOIN_NICKNAME
        st.session_state.avatar = takeover_row["avatar"] or DEFAULT_AVATAR
        st.session_state.comment = takeover_row["comment"] or DEFAULT_COMMENT
        st.session_state.activity = takeover_row["activity"] or ACTIVITY_OPTIONS[0]
        st.session_state.detail = takeover_row["detail"] or "第1回"
        st.session_state.mood = takeover_row["mood"] or DEFAULT_MOOD
        st.session_state.difficulty = normalize_difficulty(takeover_row["difficulty"])
        st.session_state.participation_type = takeover_row["participation_type"] or "quick"
        st.session_state.expires_at = takeover_row["expires_at"]
        st.session_state.joined = True
        st.session_state.quick_join_registered_key = None
        st.session_state.takeover_loaded_id = takeover_id

quick_join_request = get_quick_join_request()
quick_join_error = None
course_lesson_error = None
if quick_join_request:
    quick_join_error = quick_join_request.get("error")
    if not quick_join_error:
        quick_join_key = f"{quick_join_request['course_code']}:{quick_join_request['detail']}"
        registered_expires_dt = parse_iso_datetime(st.session_state.expires_at)
        registered_expired = registered_expires_dt and registered_expires_dt <= datetime.now(JST)
        should_register_quick_join = (
            st.session_state.quick_join_registered_key != quick_join_key
            or (registered_expired and not st.session_state.joined)
        )
        if should_register_quick_join:
            expires_at = (
                datetime.now(JST) + timedelta(minutes=QUICK_JOIN_TIMEOUT_MINUTES)
            ).isoformat(timespec="seconds")
            st.session_state.nickname = QUICK_JOIN_NICKNAME
            st.session_state.avatar = QUICK_JOIN_AVATAR
            st.session_state.comment = QUICK_JOIN_COMMENT
            st.session_state.activity = quick_join_request["activity"]
            st.session_state.detail = quick_join_request["detail"]
            st.session_state.mood = QUICK_JOIN_MOOD
            st.session_state.difficulty = QUICK_JOIN_DIFFICULTY
            st.session_state.participation_type = "quick"
            st.session_state.expires_at = expires_at
            st.session_state.joined = True
            st.session_state.quick_join_registered_key = quick_join_key
            st.session_state.last_study_summary = None
            upsert_presence(
                st.session_state.session_id,
                QUICK_JOIN_NICKNAME,
                QUICK_JOIN_AVATAR,
                QUICK_JOIN_COMMENT,
                quick_join_request["activity"],
                quick_join_request["detail"],
                QUICK_JOIN_MOOD,
                QUICK_JOIN_DIFFICULTY,
                event_type="入室",
                participation_type="quick",
                expires_at=expires_at,
            )
elif course_lesson_request:
    course_lesson_error = course_lesson_request.get("error")
    requested_key = (
        f"{course_lesson_request['course_code']}:{course_lesson_request['detail']}"
        if not course_lesson_error
        else None
    )
    if not course_lesson_error:
        if st.session_state.participation_type == "quick" and st.session_state.joined:
            st.session_state.participation_type = "regular"
            st.session_state.expires_at = None
            st.session_state.activity = course_lesson_request["activity"]
            st.session_state.detail = course_lesson_request["detail"]
        elif not st.session_state.joined and st.session_state.quick_join_registered_key != requested_key:
            st.session_state.activity = course_lesson_request["activity"]
            st.session_state.detail = course_lesson_request["detail"]
            st.session_state.quick_join_registered_key = requested_key

if st.session_state.participation_type != "quick" and st.session_state.nickname != QUICK_JOIN_NICKNAME:
    persist_preferences_to_browser(current_preferences())

if quick_join_request:
    render_quick_checkin_page(quick_join_request, quick_join_error)
    st.stop()

sync_session_id_to_url()

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
    st.caption(
        "ここは発言しなくても参加できる自習室です。"
        "顔出し・音声・チャットなしで、同じ時間に学んでいる人の気配だけを感じられます。"
    )
    if st.session_state.participation_type == "quick" and st.session_state.joined:
        st.markdown(
            f"""
            <div class="sidebar-notice">
              <strong>試験運用中です</strong>
              授業ページからの簡易参加です。表示名や状態は固定され、{QUICK_JOIN_TIMEOUT_MINUTES}分後に自動退室扱いになります。
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-notice">
              <strong>試験運用中です</strong>
              入室後、ブラウザを閉じるなどして更新が止まった場合、3分後に自動退室扱いになります。
              退室ボタンを押すと、今回取り組んだ科目ごとの学習時間を確認できます。
              <br><br>
              ニックネームやコメントには、氏名・学籍番号など、個人が特定される情報は書かないようにしてください。
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.divider()

    if quick_join_error:
        st.error(quick_join_error)
    elif course_lesson_error:
        st.error(course_lesson_error)

    if st.session_state.last_study_summary and not st.session_state.joined:
        render_study_summary(st.session_state.last_study_summary)

    if st.session_state.participation_type == "quick" and st.session_state.joined:
        st.header("簡易参加中")
        st.caption("授業ページから自動で入室しています。名前や状態は固定表示です。")
        difficulty_label = DIFFICULTY_META.get(
            st.session_state.difficulty,
            DIFFICULTY_META["ふつう"],
        )["label"]
        st.markdown(
            f"""
            <div class="sidebar-notice">
              <strong>{safe_text(st.session_state.activity)} / {safe_text(st.session_state.detail)}</strong>
              表示名：{safe_text(st.session_state.nickname)}<br>
              コメント：{safe_text(st.session_state.comment)}<br>
              状態：{safe_text(st.session_state.mood)}<br>
              体感：{safe_text(difficulty_label)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.header("入室設定")
        st.caption("まずはニックネーム、科目、授業回だけで入室できます。前回の設定がある場合は自動で入力されます。")
        nickname = st.text_input(
            "ニックネーム",
            value=st.session_state.nickname,
            placeholder="例：でこぴん",
            help="本名や学籍番号は入力しない運用を想定しています。全角10文字、または半角20文字以内です。",
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
        with st.expander("詳細設定", expanded=False):
            avatar = st.selectbox(
                "アイコン",
                AVATAR_OPTIONS,
                index=AVATAR_OPTIONS.index(st.session_state.avatar)
                if st.session_state.avatar in AVATAR_OPTIONS else 0,
            )
            comment = st.text_input(
                "コメント",
                value=st.session_state.comment or DEFAULT_COMMENT,
                placeholder=DEFAULT_COMMENT,
                help="参加者カードのアイコン横に表示されます。空欄の場合は「一緒に学習中」と表示します。全角20文字、または半角40文字以内です。",
            )
            mood = st.selectbox(
                "ひとこと状態",
                MOOD_OPTIONS,
                index=MOOD_OPTIONS.index(st.session_state.mood)
                if st.session_state.mood in MOOD_OPTIONS else 0,
            )
            difficulty = st.selectbox(
                "体感難易度",
                DIFFICULTY_OPTIONS,
                index=DIFFICULTY_OPTIONS.index(normalize_difficulty(st.session_state.difficulty)),
                help="具体的な内容は表示せず、参加者カードに体感難易度だけを表示します。",
            )

        if not st.session_state.joined:
            if st.button("入室する", type="primary", use_container_width=True):
                cleaned = nickname.strip()
                cleaned_comment = comment.strip() or DEFAULT_COMMENT
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
                    st.session_state.difficulty = difficulty
                    st.session_state.participation_type = "regular"
                    st.session_state.expires_at = None
                    st.session_state.quick_join_registered_key = None
                    st.session_state.last_study_summary = None
                    st.session_state.joined = True
                    upsert_presence(
                        st.session_state.session_id,
                        cleaned,
                        avatar,
                        cleaned_comment,
                        activity,
                        detail,
                        mood,
                        difficulty,
                        event_type="入室",
                    )
                    st.rerun()
        else:
            if st.button("学習内容を更新", use_container_width=True):
                cleaned = nickname.strip() or st.session_state.nickname
                cleaned_comment = comment.strip() or DEFAULT_COMMENT
                nickname_error = validate_nickname(cleaned)
                comment_error = validate_comment(cleaned_comment)
                if nickname_error:
                    st.error(nickname_error)
                elif comment_error:
                    st.error(comment_error)
                else:
                    previous_activity = st.session_state.activity
                    previous_detail = st.session_state.detail
                    st.session_state.nickname = cleaned
                    st.session_state.avatar = avatar
                    st.session_state.comment = cleaned_comment
                    st.session_state.activity = activity
                    st.session_state.detail = detail
                    st.session_state.mood = mood
                    st.session_state.difficulty = difficulty
                    st.session_state.participation_type = "regular"
                    st.session_state.expires_at = None
                    st.session_state.quick_join_registered_key = None
                    if activity != previous_activity or detail != previous_detail:
                        switch_study_segment(st.session_state.session_id, activity, detail)
                    upsert_presence(
                        st.session_state.session_id,
                        cleaned,
                        avatar,
                        cleaned_comment,
                        activity,
                        detail,
                        mood,
                        difficulty,
                        event_type="更新",
                    )
                    persist_preferences_to_browser(current_preferences())
                    st.success("表示を更新しました。")

            if st.button("退室する", use_container_width=True):
                st.session_state.last_study_summary = leave_room(st.session_state.session_id)
                st.session_state.joined = False
                st.session_state.participation_type = "regular"
                st.session_state.expires_at = None
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
            placeholder="気づいたこと、ほしい機能、使いにくい点など",
            height=110,
            help=f"{FEEDBACK_MAX_CHARS}文字以内で入力してください。授業内容の質問や緊急の連絡には使用しないでください。",
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
            feedback_payload = {
                "session_id": st.session_state.session_id,
                "nickname": st.session_state.nickname if st.session_state.joined else "",
                "activity": st.session_state.activity if st.session_state.joined else "",
                "detail": st.session_state.detail if st.session_state.joined else "",
                "category": feedback_category,
                "body": cleaned_feedback,
                "created_at": now_iso(),
            }
            webhook_ok, webhook_error = send_feedback_webhook(feedback_payload)
            if not webhook_ok:
                st.error(f"送信できませんでした。時間をおいてもう一度お試しください。{webhook_error}")
                st.stop()

            add_feedback(
                feedback_payload["session_id"],
                feedback_payload["nickname"],
                feedback_payload["activity"],
                feedback_payload["detail"],
                feedback_payload["category"],
                feedback_payload["body"],
            )
            st.session_state.last_feedback_at = now
            st.success("送信しました。ありがとうございます。")

    st.divider()
    st.markdown('<div class="sidebar-credit">Copyright 2026 Yosuke Tsuchiya</div>', unsafe_allow_html=True)


@st.fragment(run_every="10s")
def live_area():
    if st.session_state.joined:
        expires_at = st.session_state.expires_at
        expires_dt = parse_iso_datetime(expires_at)
        if st.session_state.participation_type == "quick" and expires_dt and expires_dt <= datetime.now(JST):
            st.session_state.joined = False
        else:
            upsert_presence(
                st.session_state.session_id,
                st.session_state.nickname,
                st.session_state.avatar,
                st.session_state.comment,
                st.session_state.activity,
                st.session_state.detail,
                st.session_state.mood,
                st.session_state.difficulty,
                participation_type=st.session_state.participation_type,
                expires_at=expires_at,
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
    st.markdown(
        """
        <div class="room-caption">
          <div>ここには入室中の参加者のニックネーム、コメント、授業回、状態が表示されます。</div>
          <div>グレーの机は、授業ページからチェックインした参加者を表しています。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
        recent_counts = fetch_recent_activity_entry_counts(activity)
        recent_24h_text = f"最近24h {recent_counts['24h']}人"
        recent_7d_text = f"最近7日 {recent_counts['7d']}人"
        tags = [f'<span class="room-count">{room_count_text}</span>']
        tags.append(f'<span class="room-tag recent">{safe_text(recent_24h_text)}</span>')
        tags.append(f'<span class="room-tag recent">{safe_text(recent_7d_text)}</span>')
        if is_my_room:
            tags.append('<span class="room-tag mine">あなたの部屋</span>')
        tags_html = "".join(tags)
        member_cards = []
        for p in room_members:
            mine = p["session_id"] == st.session_state.session_id
            label = safe_text(p["nickname"])
            avatar_text = safe_text(p["avatar"] if p["avatar"] in AVATAR_OPTIONS else AVATAR_OPTIONS[0])
            you_badge_html = '<span class="you-badge">あなた</span>' if mine else ""
            comment_text = safe_text(p["comment"] or "一緒に学習中")
            detail_text = safe_text(p["detail"] or "学習中")
            mood_text = safe_text(p["mood"] or "学習中")
            is_quick_checkin = (p["participation_type"] or "regular") == "quick"
            time_icon = "⏳" if is_quick_checkin else "⏱"
            time_text = (
                remaining_checkin_time(p["expires_at"])
                if is_quick_checkin
                else elapsed_study_time(p["joined_at"])
            )
            time_text = safe_text(time_text)
            difficulty_meta = DIFFICULTY_META.get(normalize_difficulty(p["difficulty"]))
            difficulty_html = ""
            if difficulty_meta:
                difficulty_class = safe_text(difficulty_meta["class"])
                difficulty_label = safe_text(difficulty_meta["label"])
                difficulty_html = f'<span class="card-difficulty {difficulty_class}">{difficulty_label}</span>'
            else:
                difficulty_html = '<span class="card-difficulty placeholder">体感</span>'
            card_class = "room-card"
            if mine:
                card_class += " my-card"
            if is_quick_checkin:
                card_class += " quick-checkin-card"
            member_cards.append(
                f'<div class="{card_class}">'
                '<div class="seat-note">'
                '<div class="card-top">'
                f'<div class="avatar">{avatar_text}{you_badge_html}</div>'
                '<div class="participant-name">'
                '<div>'
                f'<strong>{label}</strong>'
                '</div>'
                '</div>'
                '</div>'
                '</div>'
                '<div class="desk-surface">'
                f'<div class="profile-comment">{comment_text}</div>'
                '<div class="card-meta-row">'
                '<div class="desk-info-row">'
                '<span class="desk-info-icon">🗂️</span>'
                '<span class="desk-info-line">'
                f'<span class="desk-info-text">{detail_text}</span>'
                f'{difficulty_html}'
                '</span>'
                '</div>'
                '</div>'
                '<div class="desk-info-row">'
                '<span class="desk-info-icon">💬</span>'
                f'<span class="desk-info-text">{mood_text}</span>'
                '</div>'
                '<div class="desk-info-row">'
                f'<span class="desk-info-icon">{time_icon}</span>'
                f'<span class="desk-info-text">{time_text}</span>'
                '</div>'
                '</div>'
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
            expander_label = f"📘 {activity}　{room_count_text}　{recent_24h_text} / {recent_7d_text}"
            with st.expander(expander_label, expanded=False):
                st.markdown(
                    f'<div class="room-desk-area"><div class="room-members">{members_html}</div></div>',
                    unsafe_allow_html=True,
                )

    if empty_rooms:
        with st.expander("空き部屋を見る", expanded=False):
            st.markdown('<div class="empty-rooms-panel"></div>', unsafe_allow_html=True)
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
