// Captures the REAL website's embroidery (jacketportable dev server on :5173)
// for comparison: Arabic text, Red thread, on the left chest, zoomed in.
//   node tools/website_embroidery/capture_site.mjs <outDir> [bodyColour]
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const [outDir, body = "Navy Blue", word = "تفصيلة", font = "LALEZAR"] = process.argv.slice(2);
const b = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
await p.goto("http://localhost:5173/design", { waitUntil: "networkidle", timeout: 180000 });
await p.waitForTimeout(20000);
if (body !== "Navy Blue") {
  await p.locator("button").filter({ hasText: new RegExp(`^\\s*${body}\\s*$`) }).first().click();
  await p.waitForTimeout(3000);
}
await p.getByRole("button", { name: "Step 5: Embroidery" }).click();
await p.waitForTimeout(2000);
await p.locator("button, [role=tab], [role=radio], label").filter({ hasText: /^\s*text\s*$/i }).first().click();
await p.waitForTimeout(1500);
await p.locator("textarea").first().fill(word);
await p.waitForTimeout(2000);
await p.getByRole("button", { name: /CHOOSE FONT/i }).click();
await p.waitForTimeout(1500);
await p.locator("button").filter({ hasText: new RegExp(font, "i") }).first().click();
await p.waitForTimeout(1500);
await p.getByRole("button", { name: "Red", exact: true }).last().click();
await p.waitForTimeout(6000);
await p.screenshot({ path: `${outDir}/configurator_${body.replace(/\s/g, "")}.png` });
// zoom the viewer in on the chest
const canvas = p.locator("canvas").first();
const box = await canvas.boundingBox();
await p.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.5);
for (let i = 0; i < 10; i++) { await p.mouse.wheel(0, -300); await p.waitForTimeout(400); }
await p.waitForTimeout(6000);
await p.screenshot({ path: `${outDir}/closeup_${body.replace(/\s/g, "")}.png` });
await b.close();
