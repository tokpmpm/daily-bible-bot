const GITHUB_API_VERSION = "2022-11-28";

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(triggerDailyBot(env, "cloudflare-cron"));
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return jsonResponse({ ok: true, service: "daily-bible-bot-trigger" });
    }

    const isPodcastFeed = url.pathname === "/podcast.xml" || url.pathname === "/feed.rss";
    if (isPodcastFeed && (request.method === "GET" || request.method === "HEAD")) {
      return podcastFeedResponse(request, env);
    }

    if (url.pathname.startsWith("/audio-upload/") && request.method === "PUT") {
      return uploadAudioResponse(request, env, url);
    }

    if (url.pathname === "/trigger" && request.method === "POST") {
      const authHeader = request.headers.get("authorization") || "";
      const expected = env.CRON_TRIGGER_SECRET ? `Bearer ${env.CRON_TRIGGER_SECRET}` : "";

      if (!expected || authHeader !== expected) {
        return jsonResponse({ ok: false, error: "Unauthorized" }, 401);
      }

      const result = await triggerDailyBot(env, "manual-cloudflare-trigger");
      return jsonResponse(result, result.ok ? 202 : 502);
    }

    return jsonResponse({ ok: false, error: "Not found" }, 404);
  },
};

async function triggerDailyBot(env, source) {
  const required = [
    "GITHUB_TOKEN",
    "GITHUB_OWNER",
    "GITHUB_REPO",
    "GITHUB_WORKFLOW_ID",
    "GITHUB_REF",
  ];
  const missing = required.filter((key) => !env[key]);

  if (missing.length) {
    return { ok: false, error: "Missing required environment variables", missing };
  }

  const endpoint = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW_ID}/dispatches`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "daily-bible-bot-cloudflare-trigger",
      "X-GitHub-Api-Version": GITHUB_API_VERSION,
    },
    body: JSON.stringify({
      ref: env.GITHUB_REF,
      inputs: {
        dry_run: "false",
      },
    }),
  });

  if (response.status === 204) {
    return { ok: true, source, workflow: env.GITHUB_WORKFLOW_ID, ref: env.GITHUB_REF };
  }

  return {
    ok: false,
    source,
    status: response.status,
    error: await response.text(),
  };
}

async function uploadAudioResponse(request, env, url) {
  if (!env.DAILY_BIBLE_AUDIO) {
    return jsonResponse({ ok: false, error: "R2 bucket binding is not configured" }, 500);
  }

  const expected = env.AUDIO_UPLOAD_SECRET ? `Bearer ${env.AUDIO_UPLOAD_SECRET}` : "";
  const authHeader = request.headers.get("authorization") || "";

  if (!expected || authHeader !== expected) {
    return jsonResponse({ ok: false, error: "Unauthorized" }, 401);
  }

  const objectKey = decodeURIComponent(url.pathname.replace(/^\/audio-upload\/+/, ""));
  if (!objectKey || objectKey.includes("..") || !objectKey.endsWith(".mp3")) {
    return jsonResponse({ ok: false, error: "Invalid object key" }, 400);
  }

  await env.DAILY_BIBLE_AUDIO.put(objectKey, request.body, {
    httpMetadata: {
      contentType: "audio/mpeg",
    },
  });

  const publicBaseUrl = (env.R2_PUBLIC_BASE_URL || "").replace(/\/$/, "");
  const publicUrl = publicBaseUrl
    ? `${publicBaseUrl}/${objectKey.split("/").map(encodeURIComponent).join("/")}`
    : "";

  return jsonResponse({ ok: true, key: objectKey, url: publicUrl }, 201);
}

async function podcastFeedResponse(request, env) {
  const headOnly = request.method === "HEAD";
  const required = ["SUPABASE_URL", "SUPABASE_ANON_KEY"];
  const missing = required.filter((key) => !env[key]);

  if (missing.length) {
    return xmlResponse(
      `<?xml version="1.0" encoding="UTF-8"?><error>Missing ${escapeXml(missing.join(", "))}</error>`,
      500,
      headOnly,
    );
  }

  const select = [
    "date",
    "verse_text",
    "verse_reference",
    "exposition",
    "audio_url",
    "audio_duration_ms",
    "audio_size_bytes",
    "podcast_guid",
    "published_at",
  ].join(",");
  const endpoint = `${env.SUPABASE_URL}/rest/v1/daily_bible?select=${select}&audio_size_bytes=gt.0&order=published_at.desc&limit=100`;
  const response = await fetch(endpoint, {
    headers: {
      apikey: env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${env.SUPABASE_ANON_KEY}`,
    },
  });

  if (!response.ok) {
    return xmlResponse(
      `<?xml version="1.0" encoding="UTF-8"?><error>Supabase returned ${response.status}</error>`,
      502,
      headOnly,
    );
  }

  const rows = (await response.json()).filter((item) => {
    return item.audio_url && Number(item.audio_size_bytes || 0) > 0;
  });
  const feedUrl = request.url;
  const siteUrl = env.PODCAST_SITE_URL || "https://tokpmpm.github.io/daily-bible-bot/";
  const title = env.PODCAST_TITLE || "每日靈修";
  const description = env.PODCAST_DESCRIPTION || "每日聖經經文、靈修短文與禱告。";
  const author = env.PODCAST_AUTHOR || "Daily Bible Bot";
  const ownerName = env.PODCAST_OWNER_NAME || author;
  const ownerEmail = env.PODCAST_OWNER_EMAIL || "";
  const imageUrl = env.PODCAST_IMAGE_URL || `${siteUrl.replace(/\/$/, "")}/icon-192.png`;
  const lastBuildDate = rows[0]?.published_at || new Date().toISOString();
  const ownerXml = ownerEmail ? `
    <itunes:owner>
      <itunes:name>${escapeXml(ownerName)}</itunes:name>
      <itunes:email>${escapeXml(ownerEmail)}</itunes:email>
    </itunes:owner>` : "";

  const items = rows.map((item) => {
    const episodeTitle = `每日靈修 - ${item.verse_reference || item.date}`;
    const episodeDescription = `${item.verse_text || ""}\n\n${item.exposition || ""}`.trim();
    const pubDate = new Date(item.published_at || item.date).toUTCString();
    const guid = item.podcast_guid || `daily-bible-${item.date}`;

    return `
    <item>
      <title>${escapeXml(episodeTitle)}</title>
      <description>${escapeXml(episodeDescription)}</description>
      <itunes:summary>${escapeXml(episodeDescription)}</itunes:summary>
      <pubDate>${escapeXml(pubDate)}</pubDate>
      <guid isPermaLink="false">${escapeXml(guid)}</guid>
      <enclosure url="${escapeXml(item.audio_url)}" length="${Number(item.audio_size_bytes || 0)}" type="audio/mpeg"/>
      <itunes:duration>${escapeXml(formatDuration(item.audio_duration_ms || 0))}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
    </item>`;
  }).join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>${escapeXml(title)}</title>
    <link>${escapeXml(siteUrl)}</link>
    <atom:link href="${escapeXml(feedUrl)}" rel="self" type="application/rss+xml"/>
    <description>${escapeXml(description)}</description>
    <language>zh-TW</language>
    <lastBuildDate>${escapeXml(new Date(lastBuildDate).toUTCString())}</lastBuildDate>
    <itunes:author>${escapeXml(author)}</itunes:author>
    <itunes:summary>${escapeXml(description)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:image href="${escapeXml(imageUrl)}"/>
    <itunes:category text="Religion &amp; Spirituality"/>
${ownerXml}
${items}
  </channel>
</rss>
`;

  return xmlResponse(xml, 200, headOnly);
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

function xmlResponse(body, status = 200, headOnly = false) {
  return new Response(headOnly ? null : body, {
    status,
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=300",
      "Content-Length": String(new TextEncoder().encode(body).length),
    },
  });
}

function escapeXml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.round(Number(milliseconds || 0) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
