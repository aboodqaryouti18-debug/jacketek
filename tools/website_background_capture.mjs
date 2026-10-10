// Screenshots of the live JACKETEK site's backgrounds (homepage chapters + Design page).
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const out = process.argv[2];
const b = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
await p.goto("http://localhost:5173/", { waitUntil: "networkidle", timeout: 180000 });
await p.waitForTimeout(15000);
const H = await p.evaluate(() => document.documentElement.scrollHeight);
for (const f of [0, 0.32, 0.5, 0.68, 0.8]) {
  await p.evaluate((y) => window.scrollTo(0, y), Math.round(f * (H - 1350)));
  await p.waitForTimeout(5000);
  await p.screenshot({ path: `${out}/home_${String(Math.round(f * 100)).padStart(2, "0")}.png` });
}
await p.goto("http://localhost:5173/design", { waitUntil: "networkidle", timeout: 180000 });
await p.waitForTimeout(15000);
await p.screenshot({ path: `${out}/design.png` });
console.log("scrollHeight", H);
await b.close();
