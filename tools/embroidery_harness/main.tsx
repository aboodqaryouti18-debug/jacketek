/**
 * EMBROIDERY RENDERING HARNESS (outside the website; nothing in it is changed).
 *
 * Runs the JACKETEK website's own 3D embroidery pipeline on a lettering mask:
 *   mask → createLetteringEmbroidery()   (@/three/embroidery/embroideryMaps.ts)
 *        → <EmbroideryDecal>             (@/three/jacket/EmbroideryDecal.tsx:
 *                                         contact-shadow decal + matte
 *                                         meshPhysicalMaterial thread decal)
 *        → <StudioLighting>              (@/three/stage/StudioLighting.tsx)
 *        → NeutralToneMapping            (as ThreeJacketViewer.tsx)
 * on a flat, invisible "fabric" plane seen straight on by an orthographic
 * camera, so the render can be composited back onto a flat post. The
 * background is transparent: the PNG holds the thread and its shadow only.
 *
 * Driven by tools/embroidery_harness/render.mjs through window.* calls.
 */
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { CanvasTexture, NeutralToneMapping } from "three";
import StudioLighting from "@/three/stage/StudioLighting";
import EmbroideryDecal from "@/three/jacket/EmbroideryDecal";
import { createImageEmbroidery, createLetteringEmbroidery, type EmbroideryMaps } from "@/three/embroidery/embroideryMaps";

type Job = {
  /**
   * "lettering": maskUrl is a coverage mask, sewn in threadHex (createLetteringEmbroidery).
   * "image": maskUrl is an RGBA artwork, sewn as is (createImageEmbroidery, the
   * site's uploaded-image path: the colour map is the image's own pixels).
   */
  kind?: "lettering" | "image";
  /** "image" only: sew the shape in threadHex (the site's one-thread option). */
  singleThread?: boolean;
  maskUrl: string;
  strokePx: number;
  threadHex: string;
  /**
   * Which of the decal's two layers to draw: "thread", "shadow" or "both".
   * A layer is left out by handing EmbroideryDecal an empty texture for it
   * (an input swap only: the site's maps and material code run unchanged).
   */
  layer?: "thread" | "shadow" | "both";
  /** Output size in px (= mask size: one texel per pixel). */
  width: number;
  height: number;
  resolve: (r: Record<string, string>) => void;
};

declare global {
  interface Window {
    harnessReady?: boolean;
    textMask: (text: string, px: number, pad: number) => Promise<{ url: string; width: number; height: number }>;
    renderEmbroidery: (o: Omit<Job, "resolve">) => Promise<Record<string, string>>;
  }
}

let setJob: (j: Job | null) => void = () => {};

/** The word set in DARK ExtraBold (the site's --font-ar-display), cropped to its ink plus `pad`. */
window.textMask = async (text, px, pad) => {
  await document.fonts.load(`800 ${px}px "DARK"`, text);
  const font = `800 ${px}px "DARK"`;
  const probe = document.createElement("canvas").getContext("2d")!;
  probe.font = font;
  probe.direction = "rtl";
  probe.textAlign = "left";
  probe.textBaseline = "alphabetic";
  const m = probe.measureText(text);
  const w = Math.ceil(m.actualBoundingBoxLeft + m.actualBoundingBoxRight + pad * 2);
  const h = Math.ceil(m.actualBoundingBoxAscent + m.actualBoundingBoxDescent + pad * 2);
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d")!;
  ctx.font = font;
  ctx.direction = "rtl";
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "#fff";
  ctx.fillText(text, pad + m.actualBoundingBoxLeft, pad + m.actualBoundingBoxAscent);
  return { url: c.toDataURL("image/png"), width: w, height: h };
};

window.renderEmbroidery = (o) => new Promise((resolve) => setJob({ ...o, resolve }));

async function loadCanvas(url: string) {
  const img = new Image();
  img.src = url;
  await img.decode();
  const c = document.createElement("canvas");
  c.width = img.naturalWidth;
  c.height = img.naturalHeight;
  c.getContext("2d")!.drawImage(img, 0, 0);
  return c;
}

/** A 1x1 transparent black texture. */
function emptyTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 1;
  return new CanvasTexture(c);
}

const mapUrl = (t: { image: unknown }) => (t.image as HTMLCanvasElement).toDataURL("image/png");

/** Grabs the frame once the maps are on screen and the environment has rendered. */
function Grab({ job, maps }: { job: Job; maps: EmbroideryMaps }) {
  const gl = useThree((s) => s.gl);
  const [frames, setFrames] = useState(0);
  useFrame(() => setFrames((f) => f + 1));
  useEffect(() => {
    if (frames !== 12) return;
    job.resolve({
      render: gl.domElement.toDataURL("image/png"),
      map: mapUrl(maps.map),
      normalMap: mapUrl(maps.normalMap),
      roughnessMap: mapUrl(maps.roughnessMap),
      aoMap: mapUrl(maps.aoMap),
      shadowMap: mapUrl(maps.shadowMap),
    });
    setJob(null);
  }, [frames, gl, job, maps]);
  return null;
}

function App() {
  const [job, _setJob] = useState<Job | null>(null);
  const [maps, setMaps] = useState<EmbroideryMaps | null>(null);
  setJob = _setJob;
  useEffect(() => {
    setMaps(null);
    if (!job) return;
    let live = true;
    loadCanvas(job.maskUrl).then((mask) => {
      // Exactly the site's lettering path (EmbroideryLayer.tsx → createLetteringEmbroidery).
      if (!live) return;
      const maps =
        job.kind === "image"
          ? createImageEmbroidery(mask, job.singleThread ? job.threadHex : null)
          : createLetteringEmbroidery(mask, job.threadHex, job.strokePx);
      const layer = job.layer ?? "both";
      if (layer === "thread") maps.shadowMap = emptyTexture(); // black alphaMap = no shadow
      if (layer === "shadow") maps.map = emptyTexture(); // transparent colour map = no thread
      setMaps(maps);
    });
    return () => {
      live = false;
    };
  }, [job]);
  useEffect(() => () => maps?.dispose(), [maps]);
  useEffect(() => {
    window.harnessReady = true;
  }, []);
  if (!job || !maps) return null;
  // World units: the artwork is 1 unit tall; the camera shows exactly the artwork.
  const h = 1;
  const w = job.width / job.height;
  return (
    <div style={{ width: job.width, height: job.height }}>
      <Canvas
        key={job.maskUrl.length + job.threadHex + job.width + (job.layer ?? "both") + (job.kind ?? "lettering") + (job.singleThread ? "1" : "0")}
        orthographic
        dpr={1}
        frameloop="always"
        camera={{ position: [0, 0, 5], zoom: job.height / h, near: 0.1, far: 20 }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
        onCreated={({ gl }) => {
          gl.toneMapping = NeutralToneMapping; // as ThreeJacketViewer.tsx
          gl.setClearColor(0x000000, 0);
        }}
        style={{ width: job.width, height: job.height }}
      >
        <StudioLighting />
        {/* The "fabric": a flat panel that receives the decals but draws nothing itself. */}
        <mesh>
          <planeGeometry args={[w * 1.5, h * 1.5]} />
          <meshBasicMaterial colorWrite={false} />
          <EmbroideryDecal maps={maps} threadHex={job.threadHex} position={[0, 0, 0]} rotation={[0, 0, 0]} size={[w, h]} depth={0.5} />
        </mesh>
        <Grab job={job} maps={maps} />
      </Canvas>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
