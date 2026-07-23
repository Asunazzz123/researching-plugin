import assert from "node:assert/strict";
import test from "node:test";

import { ALPHAXIV_TOOLS, createLazyAlphaXivHandler } from "./server.mjs";

test("initialization and tool listing do not connect to alphaXiv", async () => {
  let connections = 0;
  const handler = createLazyAlphaXivHandler({
    connect: async () => {
      connections += 1;
      throw new Error("unexpected remote connection");
    },
  });

  const initialized = await handler.handle("initialize", {});
  const listed = await handler.handle("tools/list", {});

  assert.equal(initialized.serverInfo.name, "alphaxiv-lazy-bridge");
  assert.deepEqual(listed.tools, ALPHAXIV_TOOLS);
  assert.equal(connections, 0);
});

test("the first allowed tool call connects once and forwards subsequent calls", async () => {
  let connections = 0;
  const calls = [];
  const handler = createLazyAlphaXivHandler({
    connect: async () => {
      connections += 1;
      return {
        request: async (method, params) => {
          calls.push({ method, params });
          return { content: [{ type: "text", text: "ok" }] };
        },
        close() {},
      };
    },
  });

  const params = {
    name: "get_paper_content",
    arguments: { url: "https://arxiv.org/abs/1706.03762" },
  };
  await handler.handle("tools/call", params);
  await handler.handle("tools/call", params);

  assert.equal(connections, 1);
  assert.deepEqual(calls, [
    { method: "tools/call", params },
    { method: "tools/call", params },
  ]);
});

test("library mutation tools are rejected without connecting", async () => {
  let connections = 0;
  const handler = createLazyAlphaXivHandler({
    connect: async () => {
      connections += 1;
      throw new Error("unexpected remote connection");
    },
  });

  await assert.rejects(
    handler.handle("tools/call", { name: "delete_folder", arguments: {} }),
    /not exposed/,
  );
  assert.equal(connections, 0);
});
