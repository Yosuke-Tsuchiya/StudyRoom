const STATUS_KEY = "status-summary";
const VIEW_RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const UNCHECKED_PRESENCE_MS = 15 * 60 * 1000;
const MAX_EVENTS_PER_LESSON = 10000;
const LESSON_NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8"];

const COURSES = {
  "free-room": { room: "フリールーム", label: "フリールーム" },
  "info-basic": { room: "情報基礎A・B", label: "情報基礎A・B" },
  "internet-tech": { room: "インターネット技術Ⅰ・Ⅱ", label: "インターネット技術Ⅰ・Ⅱ" },
  "data-algorithms": {
    room: "データ構造とアルゴリズムⅠ・Ⅱ",
    label: "データ構造とアルゴリズムⅠ・Ⅱ",
  },
  programming: { room: "実践プログラミングⅠ・Ⅱ", label: "実践プログラミングⅠ・Ⅱ" },
  "secure-programming": {
    room: "初級セキュアプログラミング",
    label: "初級セキュアプログラミング",
  },
  seminar: { room: "基礎ゼミA・B", label: "基礎ゼミA・B" },
  certification: { room: "資格勉強", label: "資格勉強" },
};

const SVG_HEADERS = {
  "content-type": "image/svg+xml; charset=utf-8",
  "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
  pragma: "no-cache",
};

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/sync") {
      return syncStatusSummary(request, env);
    }

    if (request.method === "GET") {
      const statusMatch = url.pathname.match(/^\/status\/([a-z0-9-]+)\.svg$/);
      if (statusMatch) {
        return renderStatusImage(env, statusMatch[1]);
      }

      const viewMatch = url.pathname.match(/^\/views\/([a-z0-9-]+)\/lesson-([1-8])\.svg$/);
      if (viewMatch) {
        return renderPageViewImage(env, viewMatch[1], viewMatch[2]);
      }

      if (url.pathname === "/unchecked.json") {
        return renderUncheckedJson(env);
      }

      return new Response("StudyRoom status worker", {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    return new Response("Method Not Allowed", { status: 405 });
  },
};

async function syncStatusSummary(request, env) {
  const payload = await request.json().catch(() => null);
  if (!payload || payload.token !== env.STATUS_TOKEN || payload.type !== "status_summary") {
    return json({ ok: false, error: "unauthorized" }, 403);
  }

  await env.STATUS_KV.put(
    STATUS_KEY,
    JSON.stringify({
      total_online: Number(payload.total_online || 0),
      rooms: payload.rooms || {},
      participants: Array.isArray(payload.participants) ? payload.participants : [],
      updated_at: payload.updated_at || new Date().toISOString(),
    })
  );

  return json({ ok: true });
}

async function renderStatusImage(env, courseCode) {
  const course = COURSES[courseCode] || COURSES["free-room"];
  const now = Date.now();
  const summary = await getStatusSummary(env);
  const roomOnline = Number(summary.rooms?.[course.room] || 0);
  const totalOnline = Number(summary.total_online || 0);
  const checkedParticipants = Array.isArray(summary.participants)
    ? summary.participants.filter((participant) => participant.activity === course.room)
    : [];
  const uncheckedParticipants = await getUncheckedParticipants(env, courseCode, course.room, now);
  const participants = [...checkedParticipants, ...uncheckedParticipants];
  const updatedAt = formatDateTime(new Date(now).toISOString());

  return svgResponse(renderStudyRoomStatusSvg({
    courseLabel: course.label,
    roomOnline: roomOnline + uncheckedParticipants.length,
    totalOnline,
    participants,
    updatedAt,
  }));
}

async function renderPageViewImage(env, courseCode, lesson) {
  const course = COURSES[courseCode] || COURSES["free-room"];
  const now = Date.now();
  const events = await recordPageView(env, courseCode, lesson, now);
  const last24h = countSince(events, now - 24 * 60 * 60 * 1000);
  const last7d = countSince(events, now - VIEW_RETENTION_MS);

  return svgResponse(renderPageViewSvg({
    courseLabel: course.label,
    lessonLabel: `第${lesson}回`,
    last24h,
    last7d,
    updatedAt: formatDateTime(new Date(now).toISOString()),
  }));
}

async function renderUncheckedJson(env) {
  const now = Date.now();
  return json({
    ok: true,
    participants: await getAllUncheckedParticipants(env, now),
    updated_at: new Date(now).toISOString(),
  });
}

async function getStatusSummary(env) {
  const raw = await env.STATUS_KV.get(STATUS_KEY);
  if (!raw) {
    return { total_online: 0, rooms: {}, updated_at: new Date().toISOString() };
  }
  try {
    return JSON.parse(raw);
  } catch {
    return { total_online: 0, rooms: {}, updated_at: new Date().toISOString() };
  }
}

async function recordPageView(env, courseCode, lesson, now) {
  const key = `page-views:${courseCode}:lesson-${lesson}`;
  const raw = await env.STATUS_KV.get(key);
  let events = [];
  if (raw) {
    try {
      events = JSON.parse(raw);
    } catch {
      events = [];
    }
  }

  const minTime = now - VIEW_RETENTION_MS;
  events = events.filter((timestamp) => Number(timestamp) >= minTime);

  events.push(now);
  if (events.length > MAX_EVENTS_PER_LESSON) {
    events = events.slice(events.length - MAX_EVENTS_PER_LESSON);
  }
  await env.STATUS_KV.put(key, JSON.stringify(events));

  return events;
}

async function getUncheckedParticipants(env, courseCode, roomName, now) {
  const minTime = now - UNCHECKED_PRESENCE_MS;
  const results = [];

  for (const lesson of LESSON_NUMBERS) {
    const key = `page-views:${courseCode}:lesson-${lesson}`;
    const raw = await env.STATUS_KV.get(key);
    if (!raw) continue;

    let events = [];
    try {
      events = JSON.parse(raw);
    } catch {
      events = [];
    }

    for (const timestamp of events) {
      const recordedAt = Number(timestamp);
      if (recordedAt < minTime) continue;
      results.push({
        session_id: `unchecked:${courseCode}:lesson-${lesson}:${recordedAt}`,
        nickname: "匿名学生さん",
        activity: roomName,
        detail: `第${lesson}回`,
        avatar: "",
        avatar_color: "",
        comment: "授業ページを表示中",
        mood: "未チェックイン",
        difficulty: "表示なし",
        participation_type: "unchecked",
        joined_at: new Date(recordedAt).toISOString(),
        expires_at: new Date(recordedAt + UNCHECKED_PRESENCE_MS).toISOString(),
      });
    }
  }

  return results;
}

async function getAllUncheckedParticipants(env, now) {
  const participants = [];
  for (const [courseCode, course] of Object.entries(COURSES)) {
    participants.push(...await getUncheckedParticipants(env, courseCode, course.room, now));
  }
  return participants;
}

function countSince(events, minTime) {
  return events.filter((timestamp) => Number(timestamp) >= minTime).length;
}

function renderStudyRoomStatusSvg({ courseLabel, roomOnline, totalOnline, participants, updatedAt }) {
  const sortedParticipants = [...participants].sort(comparePresenceParticipants);
  const visibleParticipants = sortedParticipants.slice(0, 20);
  const overflowCount = Math.max(0, sortedParticipants.length - visibleParticipants.length);
  const message = roomOnline > 0 ? "この授業を受けている人の気配" : "まだ人の気配はありません";
  const seats = Array.from({ length: 20 }, (_, index) => renderClassroomSeat(index, visibleParticipants[index])).join("");
  const overflowSeat = overflowCount > 0 ? renderOverflowSeat(20, overflowCount) : renderClassroomSeat(20, null);

  return `
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="520" viewBox="0 0 960 520" role="img" aria-label="${escapeXml(courseLabel)} 全体を受けている人の気配">
  <defs>
    <linearGradient id="statusFloor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f2d4a3"/>
      <stop offset="1" stop-color="#d39b58"/>
    </linearGradient>
    <filter id="statusSoftShadow" x="-20%" y="-20%" width="140%" height="150%">
      <feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#7b4d24" flood-opacity=".18"/>
    </filter>
    <clipPath id="statusFrameClip">
      <rect x="2" y="2" width="956" height="516" rx="26"/>
    </clipPath>
  </defs>
  <rect x="1.5" y="1.5" width="957" height="517" rx="26" fill="#fff8ea" stroke="#b98048" stroke-width="3"/>
  <g clip-path="url(#statusFrameClip)">
    <rect x="2" y="2" width="956" height="181" fill="#fff8ea"/>
    <rect x="2" y="183" width="956" height="335" fill="url(#statusFloor)"/>
    <path d="M2 183 H958" stroke="#bf9056" stroke-width="1"/>
    <g opacity=".22" stroke="#a8753e" stroke-width="1">
      <path d="M480 183 L480 518"/>
      <path d="M402 183 L364 518"/>
      <path d="M558 183 L596 518"/>
      <path d="M324 183 L248 518"/>
      <path d="M636 183 L712 518"/>
      <path d="M246 183 L132 518"/>
      <path d="M714 183 L828 518"/>
      <path d="M168 183 L16 518"/>
      <path d="M792 183 L944 518"/>
    </g>
  </g>

  <rect x="48" y="26" width="864" height="128" rx="13" fill="#a96f3d" filter="url(#statusSoftShadow)"/>
  <rect x="55" y="33" width="850" height="114" rx="9" fill="#376b59"/>
  <text x="92" y="80" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="26" font-weight="700" fill="#f6fff8">${escapeXml(courseLabel)} 全体</text>
  <text x="92" y="119" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="22" fill="#d9f0e2">${escapeXml(message)}</text>
  <text x="874" y="135" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="#d6eadf">Updated: ${escapeXml(updatedAt)}</text>
  <circle cx="796" cy="170" r="10" fill="#d9e5df" stroke="#899d94" stroke-width="2"/>
  <text x="905" y="175" text-anchor="end" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="14" fill="#5d4630">未チェックイン</text>

  <g transform="translate(62 214)" filter="url(#statusSoftShadow)">
    ${seats}
    ${overflowSeat}
  </g>
</svg>`.trim();
}

function comparePresenceParticipants(a, b) {
  const priorityA = participationPriority(a);
  const priorityB = participationPriority(b);
  if (priorityA !== priorityB) return priorityA - priorityB;

  const lessonA = detailRank(a.detail);
  const lessonB = detailRank(b.detail);
  if (lessonA !== lessonB) return lessonB - lessonA;

  return String(a.joined_at || "").localeCompare(String(b.joined_at || ""));
}

function participationPriority(participant) {
  return (participant.participation_type || "regular") === "regular" ? 0 : 1;
}

function detailRank(detail) {
  const match = String(detail || "").match(/^第([1-8])回$/);
  if (match) return Number(match[1]);
  if (detail === "その他") return 0;
  return -1;
}

function lessonBadge(detail) {
  const match = String(detail || "").match(/^第([1-8])回$/);
  if (match) return match[1];
  if (detail === "その他") return "他";
  return "";
}

function renderClassroomSeat(index, participant) {
  const cols = 7;
  const x = (index % cols) * 122;
  const y = Math.floor(index / cols) * 94;
  const row = Math.floor(index / cols);
  const desk = row === 0
    ? { fill: "#c8945d", stroke: "#a96f3d" }
    : row === 1
      ? { fill: "#bd8650", stroke: "#9b673a" }
      : { fill: "#ad7746", stroke: "#8f5d35" };
  const emptyDesk = row === 0
    ? { fill: "#dfbd8c", stroke: "#c99b67" }
    : row === 1
      ? { fill: "#d8b17e", stroke: "#bd8d58" }
      : { fill: "#cfa470", stroke: "#ac7d4d" };
  const deskStyle = participant ? desk : emptyDesk;
  const marker = participant ? renderPresenceMarker(participant) : "";
  return `
    <g transform="translate(${x} ${y})">
      <rect x="0" y="0" width="104" height="64" rx="13" fill="${deskStyle.fill}" stroke="${deskStyle.stroke}" stroke-width="1.2"/>
      ${marker}
    </g>`;
}

function renderPresenceMarker(participant) {
  const isRegular = (participant.participation_type || "regular") === "regular";
  const badge = escapeXml(lessonBadge(participant.detail));
  if (!isRegular) {
    return `
      <circle cx="52" cy="32" r="22" fill="#d9e5df" stroke="#899d94" stroke-width="4"/>
      <text x="84" y="55" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="600" fill="#dfc89e">${badge}</text>`;
  }

  const avatar = escapeXml(String(participant.avatar || "🧑‍💻").trim() || "🧑‍💻");
  const color = sanitizeHexColor(participant.avatar_color, "#f4c76f");
  const stroke = darkenHexColor(color);
  return `
    <circle cx="52" cy="32" r="22" fill="${color}" stroke="${stroke}" stroke-width="4"/>
    <text x="52" y="41" text-anchor="middle" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="22" font-weight="700" fill="#3f2b1a">${avatar}</text>
    <text x="84" y="55" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="600" fill="#dfc89e">${badge}</text>`;
}

function renderOverflowSeat(index, overflowCount) {
  const cols = 7;
  const x = (index % cols) * 122;
  const y = Math.floor(index / cols) * 94;
  return `
    <g transform="translate(${x} ${y})">
      <rect x="0" y="0" width="104" height="64" rx="13" fill="#ad7746" stroke="#8f5d35" stroke-width="1.2"/>
      <rect x="20" y="17" width="64" height="30" rx="15" fill="#fff8ea" stroke="#8d6a45" stroke-width="3"/>
      <text x="52" y="38" text-anchor="middle" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="17" font-weight="700" fill="#5d4630">他${overflowCount}名</text>
    </g>`;
}

function renderPageViewSvg({ courseLabel, lessonLabel, last24h, last7d, updatedAt }) {
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="120" viewBox="0 0 960 120" role="img" aria-label="${escapeXml(courseLabel)} ${escapeXml(lessonLabel)} のページ表示状況">
  <defs>
    <linearGradient id="viewPanel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#066C6F"/>
      <stop offset="1" stop-color="#0a5558"/>
    </linearGradient>
    <filter id="viewSoftShadow" x="-20%" y="-30%" width="140%" height="170%">
      <feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#06484b" flood-opacity=".14"/>
    </filter>
  </defs>
  <rect width="960" height="120" rx="14" fill="#edf7f6"/>
  <rect x="1.5" y="1.5" width="957" height="117" rx="13" fill="none" stroke="#4d9a9c" stroke-width="3"/>
  <rect x="0" y="0" width="276" height="120" rx="14" fill="url(#viewPanel)"/>
  <rect x="256" y="0" width="34" height="120" fill="#0a5558"/>
  <text x="34" y="39" font-family="Arial, 'Yu Gothic', Meiryo, sans-serif" font-size="21" font-weight="700" fill="#f5ffff">@ROOM</text>
  <text x="34" y="66" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="19" font-weight="700" fill="#dff7f6">ページ表示</text>
  <text x="34" y="95" font-family="Arial, sans-serif" font-size="11" fill="#bde3e3">Updated: ${escapeXml(updatedAt)}</text>

  <text x="326" y="35" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="22" font-weight="700" fill="#06484b">${escapeXml(courseLabel)} ${escapeXml(lessonLabel)}</text>
  <text x="326" y="62" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="14" fill="#557879">この授業回ページが表示された回数です</text>

  <g filter="url(#viewSoftShadow)">
    <rect x="604" y="24" width="150" height="72" rx="13" fill="#d7eeed"/>
    <text x="629" y="51" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="16" fill="#557879">24時間</text>
    <text x="711" y="80" text-anchor="end" font-family="Arial, 'Yu Gothic', Meiryo, sans-serif" font-size="31" font-weight="700" fill="#07585b">${last24h}</text>
    <text x="721" y="77" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">回</text>

    <rect x="780" y="24" width="150" height="72" rx="13" fill="#d7eeed"/>
    <text x="805" y="51" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="16" fill="#557879">7日間</text>
    <text x="887" y="80" text-anchor="end" font-family="Arial, 'Yu Gothic', Meiryo, sans-serif" font-size="31" font-weight="700" fill="#07585b">${last7d}</text>
    <text x="897" y="77" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">回</text>
  </g>
</svg>`.trim();
}

function svgResponse(svg) {
  return new Response(svg, { status: 200, headers: SVG_HEADERS });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: JSON_HEADERS });
}

function formatDateTime(value) {
  const date = value ? new Date(value) : new Date();
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
}

function sanitizeHexColor(value, fallback) {
  const color = String(value || "").trim();
  return /^#[0-9a-fA-F]{6}$/.test(color) ? color : fallback;
}

function darkenHexColor(value) {
  const color = sanitizeHexColor(value, "#f4c76f").slice(1);
  const r = Math.max(0, Math.round(parseInt(color.slice(0, 2), 16) * 0.58));
  const g = Math.max(0, Math.round(parseInt(color.slice(2, 4), 16) * 0.58));
  const b = Math.max(0, Math.round(parseInt(color.slice(4, 6), 16) * 0.58));
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function toHex(value) {
  return value.toString(16).padStart(2, "0");
}

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}
