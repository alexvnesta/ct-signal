/* Attention store: data/interactions.json in this repo, updated via the
 * GitHub Contents API. Votes are commits — the audit trail is the database.
 * Env: GH_STORE_TOKEN (contents:write, this repo), GH_STORE_REPO
 * (owner/repo), optional GH_STORE_BRANCH (default master). */
const FILE = "data/interactions.json";

async function bump(id, field) {
  const repo = process.env.GH_STORE_REPO;
  const branch = process.env.GH_STORE_BRANCH || "master";
  const H = {
    authorization: `Bearer ${process.env.GH_STORE_TOKEN}`,
    accept: "application/vnd.github+json",
    "x-github-api-version": "2022-11-28",
    "content-type": "application/json",
  };
  const api = `https://api.github.com/repos/${repo}/contents/${FILE}`;
  for (let try_ = 0; try_ < 4; try_++) {
    const cur = await (await fetch(`${api}?ref=${branch}`, { headers: H })).json()
      .catch(() => null);
    let data = {};
    let sha;
    if (cur && cur.content) {
      data = JSON.parse(Buffer.from(cur.content, "base64").toString());
      sha = cur.sha;
    }
    const day = new Date().toISOString().slice(0, 10);
    const e = (data[id] = data[id] || {});
    const d = (e[day] = e[day] || { u: 0, d: 0, s: 0 });
    d[field] = (d[field] || 0) + 1;
    const res = await fetch(`${api}?`, {
      method: "PUT",
      headers: H,
      body: JSON.stringify({
        message: `attention: ${field} ${id}`,
        branch,
        content: Buffer.from(JSON.stringify(data)).toString("base64"),
        sha,
      }),
    });
    if (res.status === 409) continue;   // CI heartbeat raced us; retry
    return res.ok;
  }
  return false;
}

export async function handle(req, field) {
  let id;
  try { id = (await req.json()).id; } catch { return new Response(null, { status: 400 }); }
  if (!/^[0-9a-f]{12}$/.test(id || "")) return new Response(null, { status: 400 });
  const ok = await bump(id, field);
  return new Response(null, { status: ok ? 204 : 502 });
}
