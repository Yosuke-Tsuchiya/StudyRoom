const STATUS_KEY = "status-summary";
const VIEW_RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const VIEW_WRITE_INTERVAL_MS = 15 * 60 * 1000;

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
      updated_at: payload.updated_at || new Date().toISOString(),
    })
  );

  return json({ ok: true });
}

async function renderStatusImage(env, courseCode) {
  const course = COURSES[courseCode] || COURSES["free-room"];
  const summary = await getStatusSummary(env);
  const roomOnline = Number(summary.rooms?.[course.room] || 0);
  const totalOnline = Number(summary.total_online || 0);
  const updatedAt = formatDateTime(summary.updated_at);

  return svgResponse(renderStudyRoomStatusSvg({
    courseLabel: course.label,
    roomOnline,
    totalOnline,
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

  const lastRecordedAt = events.length ? Number(events[events.length - 1]) : 0;
  if (!lastRecordedAt || now - lastRecordedAt >= VIEW_WRITE_INTERVAL_MS) {
    events.push(now);
    await env.STATUS_KV.put(key, JSON.stringify(events));
  }

  return events;
}

function countSince(events, minTime) {
  return events.filter((timestamp) => Number(timestamp) >= minTime).length;
}

function renderStudyRoomStatusSvg({ courseLabel, roomOnline, totalOnline, updatedAt }) {
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="120" viewBox="0 0 500 120">
  <rect width="500" height="120" rx="14" fill="#fff8ea"/>
  <rect x="1.5" y="1.5" width="497" height="117" rx="13" fill="none" stroke="#c8945d" stroke-width="3"/>
  <rect x="0" y="0" width="154" height="120" rx="14" fill="#a96f3d"/>
  <rect x="140" y="0" width="24" height="120" fill="#a96f3d"/>
  <text x="24" y="37" font-family="Arial, 'Yu Gothic', Meiryo, sans-serif" font-size="19" font-weight="700" fill="#fff8ea">StudyRoom</text>
  <text x="24" y="61" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" font-weight="700" fill="#ffe8c6">利用状況</text>
  <text x="24" y="90" font-family="Arial, sans-serif" font-size="10" fill="#f4d6ad">Updated: ${escapeXml(updatedAt)}</text>
  <text x="184" y="35" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="17" font-weight="700" fill="#4b2f17">${escapeXml(courseLabel)}</text>
  <text x="184" y="67" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#7d6245">この科目</text>
  <text x="262" y="69" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="24" font-weight="700" fill="#6c4325">${roomOnline}</text>
  <text x="300" y="67" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#7d6245">人が学習中</text>
  <text x="184" y="98" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#7d6245">全体</text>
  <text x="262" y="100" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="24" font-weight="700" fill="#6c4325">${totalOnline}</text>
  <text x="300" y="98" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#7d6245">人が学習中</text>
</svg>`.trim();
}

function renderPageViewSvg({ courseLabel, lessonLabel, last24h, last7d, updatedAt }) {
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="120" viewBox="0 0 500 120">
  <rect width="500" height="120" rx="14" fill="#edf7f6"/>
  <rect x="1.5" y="1.5" width="497" height="117" rx="13" fill="none" stroke="#4d9a9c" stroke-width="3"/>
  <rect x="0" y="0" width="154" height="120" rx="14" fill="#066C6F"/>
  <rect x="140" y="0" width="24" height="120" fill="#066C6F"/>
  <text x="24" y="37" font-family="Arial, 'Yu Gothic', Meiryo, sans-serif" font-size="18" font-weight="700" fill="#f5ffff">@ROOM</text>
  <text x="24" y="61" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="16" font-weight="700" fill="#dff7f6">ページ表示</text>
  <text x="24" y="90" font-family="Arial, sans-serif" font-size="10" fill="#bde3e3">Updated: ${escapeXml(updatedAt)}</text>
  <text x="184" y="35" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="17" font-weight="700" fill="#06484b">${escapeXml(courseLabel)} ${escapeXml(lessonLabel)}</text>
  <text x="184" y="67" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">24時間</text>
  <text x="252" y="69" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="24" font-weight="700" fill="#07585b">${last24h}</text>
  <text x="292" y="67" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">回表示</text>
  <text x="184" y="98" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">7日間</text>
  <text x="252" y="100" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="24" font-weight="700" fill="#07585b">${last7d}</text>
  <text x="292" y="98" font-family="'Yu Gothic', Meiryo, sans-serif" font-size="15" fill="#557879">回表示</text>
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

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}
