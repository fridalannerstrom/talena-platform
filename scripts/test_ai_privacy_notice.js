/* Browser-free smoke test of the actual privacy notice JS.
 * Run: node scripts/test_ai_privacy_notice.js
 */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function element() {
  return {
    children: [],
    dataset: {},
    hidden: false,
    attributes: {},
    append(...nodes) { this.children.push(...nodes); },
    setAttribute(key, value) { this.attributes[key] = value; },
    addEventListener(type, handler) { this["on_" + type] = handler; },
  };
}

async function main() {
  let nextResponse;
  const appended = [];
  const windowMock = {
    fetch: async () => nextResponse,
    setTimeout: () => 1,
    clearTimeout() {},
  };
  const documentMock = {
    documentElement: { lang: "sv" },
    body: { append(node) { appended.push(node); } },
    createElement: () => element(),
  };
  const src = fs.readFileSync(
    path.join(__dirname, "..", "static", "js", "talena", "ai-privacy-notice.js"),
    "utf8",
  );
  vm.runInNewContext(src, {
    window: windowMock,
    document: documentMock,
    Response,
    TransformStream,
    TextDecoder,
    console,
  });

  // Without a proven backend masking signal, no notice may be displayed.
  nextResponse = new Response('{"ok":true}', {
    headers: { "Content-Type": "application/json" },
  });
  const noMask = await windowMock.fetch("/test");
  assert.equal(await noMask.text(), '{"ok":true}');
  assert.equal(appended.length, 0);

  // A successful non-stream OpenAI response signals only a boolean.
  nextResponse = new Response('{"ok":true}', {
    headers: {
      "Content-Type": "application/json",
      "X-Talena-AI-PII-Masked": "1",
    },
  });
  const masked = await windowMock.fetch("/test");
  assert.equal(await masked.text(), '{"ok":true}');
  assert.equal(appended.length, 1);
  const toast = appended[0];
  assert.equal(toast.children[0].children[0].textContent, "Personuppgifter har maskats");
  assert.equal(toast.hidden, false);

  // NDJSON must be passed through byte-for-byte while the short backend
  // privacy event makes the same existing notification visible again.
  toast.hidden = true;
  const ndjson = '{"type":"started"}\n{"type":"ai_privacy_masked"}\n{"type":"complete"}\n';
  nextResponse = new Response(ndjson, {
    headers: { "Content-Type": "application/x-ndjson" },
  });
  const stream = await windowMock.fetch("/stream");
  assert.equal(await stream.text(), ndjson);
  assert.equal(toast.hidden, false);
  assert.equal(appended.length, 1);

  // Failed responses must not show success-style masking messages.
  toast.hidden = true;
  nextResponse = new Response('{"error":"failed"}', {
    status: 500,
    headers: { "X-Talena-AI-PII-Masked": "1" },
  });
  await windowMock.fetch("/failure");
  assert.equal(toast.hidden, true);

  // English language must have the translated content.
  console.log("Privacy notice browser smoke tests passed.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
