/* Which town should we suggest? Vercel's edge network resolves the
 * requester's IP and injects x-vercel-ip-city; we echo the city (and
 * region) and nothing else — no logging, no store, cache-bypassed.
 * The page maps city to town slug or stays quiet. */
export default function handler(req) {
  const h = req.headers;
  return new Response(JSON.stringify({
    city: h.get("x-vercel-ip-city") || null,
    region: h.get("x-vercel-ip-country-region") || null,
  }), {
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
    },
  });
}
