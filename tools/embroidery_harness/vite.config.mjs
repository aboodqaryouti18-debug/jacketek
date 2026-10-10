// Rendering harness: runs the JACKETEK website's own embroidery code
// (imported unchanged from the jacketportable clone) in a browser page.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const SITE = process.env.JACKETPORTABLE_DIR || "/home/user/jacketportable";
const HERE = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: HERE,
  publicDir: `${SITE}/public`, // DARK font and site assets, served as on the site
  plugins: [react()],
  resolve: {
    alias: { "@": `${SITE}/src` },
    dedupe: ["three", "react", "react-dom", "@react-three/fiber", "@react-three/drei"],
  },
  server: { port: 5199, strictPort: true, fs: { allow: [HERE, SITE] } },
});
