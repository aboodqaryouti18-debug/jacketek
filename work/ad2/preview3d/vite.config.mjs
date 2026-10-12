// Isolated preview server: imports the website's 3D code READ-ONLY from the
// jacketportable clone and serves its public/ folder (the GLB) read-only.
// Nothing in jacketportable is written; packages come from ./node_modules.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const SITE = process.env.JACKETPORTABLE_DIR || "/home/user/jacketportable";
const HERE = fileURLToPath(new URL(".", import.meta.url));
const NM = `${HERE}node_modules`;

export default defineConfig({
  root: HERE,
  publicDir: `${SITE}/public`,
  plugins: [react()],
  resolve: {
    alias: [
      { find: /^@\//, replacement: `${SITE}/src/` },
      { find: /^three$/, replacement: `${NM}/three/build/three.module.js` },
      { find: /^three\/(.*)$/, replacement: `${NM}/three/$1` },
      { find: /^react$/, replacement: `${NM}/react/index.js` },
      { find: /^react\/(.*)$/, replacement: `${NM}/react/$1` },
      { find: /^react-dom\/client$/, replacement: `${NM}/react-dom/client.js` },
      { find: /^react-dom$/, replacement: `${NM}/react-dom/index.js` },
      { find: /^@react-three\/fiber$/, replacement: `${NM}/@react-three/fiber` },
      { find: /^@react-three\/drei$/, replacement: `${NM}/@react-three/drei` },
    ],
    dedupe: ["three", "react", "react-dom", "@react-three/fiber", "@react-three/drei"],
  },
  optimizeDeps: { include: ["three", "react", "react-dom", "react-dom/client", "@react-three/fiber", "@react-three/drei"] },
  server: { port: 5299, strictPort: true, host: "127.0.0.1", fs: { allow: [HERE, SITE] } },
});
