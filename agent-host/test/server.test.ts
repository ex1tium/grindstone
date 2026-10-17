import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import type { ServiceHealth } from "@grindstone/contracts";
import { createHostServer } from "../src/server.ts";

const server = createHostServer();
let base = "";

before(async () => {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

after(() => {
  server.close();
});

test("readyz reports ok in the shared health contract", async () => {
  const res = await fetch(`${base}/readyz`);
  assert.equal(res.status, 200);
  const body = (await res.json()) as ServiceHealth;
  assert.equal(body.service, "agent-host");
  assert.equal(body.status, "ok");
  assert.equal(body.schema_version, 1);
});

test("unknown paths are 404", async () => {
  const res = await fetch(`${base}/anything`);
  assert.equal(res.status, 404);
});
