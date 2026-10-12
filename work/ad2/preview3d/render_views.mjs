// Phase 1: five still views of the website's jacket, local only.
//   node render_views.mjs <outDir>
// Starts this folder's Vite server (127.0.0.1:5299), drives headless Chromium
// (pre-installed, /opt/pw-browsers) with SwiftShader WebGL, saves PNGs.
import { createServer } from "vite";
import { chromium } from "playwright-core";
import { mkdirSync, writeFileSync } from "node:fs";

const out = process.argv[2] || "out";
mkdirSync(out, { recursive: true });
const W = 1080, H = 1350;              // 4:5 stills for the comparison sheet
const base = { pitchDeg: 7, dist: Number(process.env.DIST || 3.15), targetY: Number(process.env.TARGET_Y || 0.37), fov: 24 };   // heroLayout: FOV 24, pitch 7°
const VIEWS = process.env.VIEWS ? JSON.parse(process.env.VIEWS) : [
  ["01_front", 0], ["02_three_quarter_front", 35], ["03_side", 90],
  ["04_three_quarter_back", 145], ["05_back", 180],
];

const server = await createServer({ configFile: new URL("./vite.config.mjs", import.meta.url).pathname, logLevel: "error" });
await server.listen();
const browser = await chromium.launch({
  executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: W, height: H } });
const requests = new Set();
page.on("request", (r) => requests.add(new URL(r.url()).host));
page.on("console", (m) => ["error", "warning"].includes(m.type()) && console.error("page:", m.text().slice(0, 300)));
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.goto("http://127.0.0.1:5299/", { waitUntil: "networkidle", timeout: 180000 });
await page.waitForFunction(() => window.previewReady === true, null, { timeout: 180000 });
for (const [name, yaw] of VIEWS) {
  await page.evaluate((s) => window.setShot(s), { ...base, yawDeg: yaw });
  await page.waitForTimeout(400);
  const png = await page.locator("canvas").screenshot();
  writeFileSync(`${out}/${name}.png`, png);
  console.log("saved", `${out}/${name}.png`);
}
console.log("hosts contacted:", [...requests].join(", "));
await browser.close();
await server.close();
