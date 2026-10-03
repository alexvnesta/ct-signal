import { handle } from "./_store.js";
export default { POST: (req) => handle(req, "u", (b) => (b.dir === "down" ? "d" : "u")) };
