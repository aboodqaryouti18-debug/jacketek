// Phase 2: low-cost local orbit + thread preview (no typography, no graphics).
//   node render_orbit.mjs <outDir> [seconds=12] [width=540] [height=960]
// One continuous camera path: front → side → back (yaw -20° → 200°), constant
// distance, eased; the thread's head leads the camera around the jacket.
// Frames are rendered by the website's own 3D code in local headless Chromium
// (SwiftShader) and encoded locally with ffmpeg.
import { createServer } from "vite";
import { chromium } from "playwright-core";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const out = process.argv[2] || "out";
const SEC = Number(process.argv[3] || 12), W = Number(process.argv[4] || 540), H = Number(process.argv[5] || 960);
const FPS = 24, N = Math.round(SEC * FPS);
mkdirSync(`${out}/frames`, { recursive: true });

const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);

const server = await createServer({ configFile: new URL("./vite.config.mjs", import.meta.url).pathname, logLevel: "error" });
await server.listen();
const browser = await chromium.launch({
  executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: W, height: H } });
const hosts = new Set();
page.on("request", (r) => hosts.add(new URL(r.url()).host));
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.goto("http://127.0.0.1:5299/", { waitUntil: "networkidle", timeout: 180000 });
await page.waitForFunction(() => window.previewReady === true, null, { timeout: 180000 });

for (let i = 0; i < N; i++) {
  const file = `${out}/frames/f_${String(i).padStart(4, "0")}.png`;
  if (existsSync(file)) continue;          // resume: frames already rendered are kept
  const u = i / (N - 1);
  const shot = {
    yawDeg: -20 + 220 * ease(u),        // front → side → back
    pitchDeg: 7,
    dist: 2.75,                         // constant distance (9:16 frame, jacket centred)
    targetY: 0.37,
    fov: 24,
    thread: 0.08 + 0.92 * u,            // thread leads around the jacket
  };
  await page.evaluate((s) => window.setShot(s), shot);
  writeFileSync(file, await page.locator("canvas").screenshot());
  if (i % 24 === 0) console.log(`frame ${i}/${N}`);
}
console.log("hosts contacted:", [...hosts].join(", "));
await browser.close();
await server.close();

execFileSync("ffmpeg", ["-y", "-v", "error", "-framerate", String(FPS), "-i", `${out}/frames/f_%04d.png`,
  "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", `${out}/orbit_thread_preview.mp4`]);
console.log("wrote", `${out}/orbit_thread_preview.mp4`);
