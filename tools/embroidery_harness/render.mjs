// Drives the harness page (vite dev server on :5199) in headless Chromium.
//   node render.mjs tasks.json
// tasks: [{ "op": "mask", "text", "px", "pad", "out" }
//         { "op": "embroider", "mask", "strokePx", "threadHex", "outDir", "kind"?: "image", "singleThread"?, "layer"? }]
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "/opt/node22/lib/node_modules/playwright");

const tasks = JSON.parse(readFileSync(process.argv[2], "utf8"));
const save = (file, dataUrl) => writeFileSync(file, Buffer.from(dataUrl.split(",")[1], "base64"));

const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 2400, height: 1400 } });
page.on("console", (m) => m.type() === "error" && console.error("page:", m.text()));
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.goto("http://localhost:5199/", { waitUntil: "networkidle" });
await page.waitForFunction(() => window.harnessReady === true);

for (const t of tasks) {
  if (t.op === "mask") {
    const r = await page.evaluate(({ text, px, pad }) => window.textMask(text, px, pad), t);
    save(t.out, r.url);
    console.log("mask", t.out, r.width, r.height);
  } else if (t.op === "embroider") {
    const img = readFileSync(t.mask);
    const { width, height } = { width: img.readUInt32BE(16), height: img.readUInt32BE(20) };
    const maskUrl = "data:image/png;base64," + img.toString("base64");
    await page.setViewportSize({ width: Math.max(width, 800), height: Math.max(height, 600) });
    const r = await page.evaluate((o) => window.renderEmbroidery(o), { kind: t.kind, singleThread: t.singleThread, maskUrl, strokePx: t.strokePx, threadHex: t.threadHex || "#FFFFFF", layer: t.layer, width, height });
    mkdirSync(t.outDir, { recursive: true });
    const tag = t.layer ? `_${t.layer}` : "";
    for (const [k, v] of Object.entries(r)) save(`${t.outDir}/${k === "render" ? "render" + tag : k}.png`, v);
    console.log("embroidered", t.outDir, width, height);
  }
}
await browser.close();
