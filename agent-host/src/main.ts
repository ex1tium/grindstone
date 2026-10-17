import { createHostServer } from "./server.ts";

const host = process.env.GRINDSTONE_AGENT_HOST_BIND ?? "127.0.0.1";
const port = Number(process.env.GRINDSTONE_AGENT_HOST_PORT ?? "8090");

const server = createHostServer();
server.listen(port, host, () => {
  console.log(JSON.stringify({ event: "agent_host.listening", host, port }));
});

for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}
