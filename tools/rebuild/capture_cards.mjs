// POST_05's two UI cards, re-captured from the live JACKETEK configurator (jacketportable
// dev server on :5173, Arabic locale) at 3x pixel density, in the state the cards show:
//   card 1  Body step, navy body, leather (chip "كحلي · جلد")
//   card 2  Embroidery step, 4 zones used (left chest JK, main back 27, left arm top 09,
//           right arm top 09), left chest selected
//   node tools/rebuild/capture_cards.mjs <outDir>
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const out = process.argv[2];
const T = "work/rebuild/thumbs";
const b = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 3 });
await ctx.addInitScript(() => localStorage.setItem("jacketek.locale", "ar-IQ"));
const p = await ctx.newPage();
p.setDefaultTimeout(240000);
p.on("pageerror", (e) => console.error("pageerror:", e.message));
await p.goto("http://localhost:5173/design", { waitUntil: "networkidle", timeout: 180000 });
await p.waitForTimeout(15000);
const panel = { x: 0, y: 0, width: 490, height: 1000 };
// card 1
await p.getByText("جلد", { exact: true }).first().click({ force: true });
await p.waitForTimeout(4000);
await p.mouse.move(1000, 950);
await p.waitForTimeout(800);
await p.screenshot({ path: `${out}/body_panel.png`, clip: panel, timeout: 240000 });
// card 2
for (let i = 0; i < 4; i++) {   // through the steps with the site's own "continue" button
  await p.getByRole("button", { name: /^كمّل/ }).first().click({ force: true });
  await p.waitForTimeout(2500);
}
await p.waitForTimeout(3000);
const zones = [["الصدر اليسار", "JK"], ["الظهر الرئيسي", "27"], ["الردن اليسار — فوق", "09"], ["الردن اليمين — فوق", "09"]];
for (const [zone, file] of zones) {
  const z = p.getByRole("button", { name: zone, exact: true });
  await ((await z.count()) ? z.first() : p.getByText(zone, { exact: true }).first()).click({ force: true });
  await p.waitForTimeout(1500);
  await p.getByText("تصميم", { exact: true }).first().click({ force: true });
  await p.waitForTimeout(1200);
  const [fc] = await Promise.all([p.waitForEvent("filechooser", { timeout: 10000 }), p.getByText("ارفع تصميم", { exact: true }).first().click({ force: true })]);
  await fc.setFiles(`${T}/${file}.png`);
  await p.waitForTimeout(12000);
}
await p.getByText("الصدر اليسار", { exact: true }).first().click({ force: true });
await p.waitForTimeout(3000);
// the card shows the zone list: scroll the panel back to its top
await p.evaluate(() => document.querySelectorAll("*").forEach((e) => { if (e.scrollTop > 0) e.scrollTop = 0; }));
await p.waitForTimeout(1500);
await p.mouse.move(1000, 950);
await p.waitForTimeout(800);
await p.screenshot({ path: `${out}/embroidery_panel.png`, clip: panel, timeout: 240000 });
console.log((await p.locator("body").innerText()).slice(0, 1500));
await b.close();
