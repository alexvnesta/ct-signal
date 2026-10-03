import { handle } from "./_store.js";
export default {
  async POST(req) {
    let dir;
    try { dir = (await req.json()).dir; } catch { return new Response(null, { status: 400 }); }
    return handle(req, dir === "down" ? "d" : "u");
  },
};
