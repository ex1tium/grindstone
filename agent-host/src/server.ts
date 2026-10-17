import { createServer, type Server } from "node:http";
import { health } from "./health.ts";

/**
 * The agent host's HTTP listener. M0 serves only `/healthz` and `/readyz`;
 * the host control API (ADR-15) and AHP arrive with SPEC-06 after SPK-1.
 */
export function createHostServer(): Server {
  return createServer((req, res) => {
    if (req.method === "GET" && (req.url === "/healthz" || req.url === "/readyz")) {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(health()));
      return;
    }
    res.writeHead(404, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "not_found" }));
  });
}
