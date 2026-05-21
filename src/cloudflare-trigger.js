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

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
