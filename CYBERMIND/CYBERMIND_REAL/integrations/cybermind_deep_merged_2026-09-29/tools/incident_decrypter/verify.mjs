import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { webcrypto } from "node:crypto";
import { runInNewContext } from "node:vm";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { encryptIncidentBrief, encryptIncidentBriefWithKey } from "../../frontend/src/lib/reportCrypto.ts";

const here = dirname(fileURLToPath(import.meta.url));
const html = await readFile(resolve(here, "index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, "decrypter script found");
const ids = ["file", "key", "error", "result", "preview", "decrypt", "reveal", "download"];
const elements = Object.fromEntries(ids.map(id => [id, {
  value: "", textContent: "", style: {}, files: [], disabled: false,
  addEventListener(_name, callback) { this.callback = callback; },
}]));
const context = {
  document: { getElementById(id) { return elements[id]; } },
  crypto: webcrypto, TextEncoder, TextDecoder, Uint8Array, atob, btoa,
  Error, JSON, Array, Blob, URL, Date, setTimeout,
};
runInNewContext(script, context);

async function open(envelope, secret) {
  const contents = JSON.stringify(envelope);
  elements.file.files = [{ size: Buffer.byteLength(contents), text: async () => contents }];
  elements.key.value = secret;
  await elements.decrypt.callback();
  return { visible: elements.result.style.display, error: elements.error.textContent, preview: elements.preview.textContent };
}

const report = { report_type: "CYBERMIND_Incident_Brief", executive_summary: "Offline test" };
const { envelope, reportKey } = await encryptIncidentBriefWithKey(report);
assert.equal(reportKey.length, 43);
assert.equal(JSON.stringify(envelope).includes(reportKey), false, "secret must not be embedded in report");
assert.deepEqual(await open(envelope, reportKey).then(r => JSON.parse(r.preview)), report);
assert.equal((await open(envelope, "A".repeat(43))).visible, "none", "wrong key must fail closed");
assert.match(elements.error.textContent, /Decryption failed/);
const legacy = await encryptIncidentBrief(report, "independent-test-passphrase");
assert.deepEqual(await open(legacy, "independent-test-passphrase").then(r => JSON.parse(r.preview)), report);
console.log("PASS: v2 random-key round trip, key isolation, wrong-key rejection, and legacy v1 decryption");
