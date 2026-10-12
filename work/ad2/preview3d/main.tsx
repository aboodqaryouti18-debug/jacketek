/**
 * JACKETEK ad — isolated 3D preview (no website changes).
 *
 * Renders the website's own jacket component (@/three/jacket/JacketModel →
 * GltfJacket: zone tinting + the GLB's own textures) with the website's own
 * StudioLighting and NeutralToneMapping (as ThreeJacketViewer.tsx), on the
 * site's studio cream (#FCF0D6). Colours = real configurator options closest
 * to the reference photos. No embroidery: the reference jacket's embroidery
 * configuration is not in the repository (see the report).
 *
 * Driven by render.mjs through window.setShot({ yawDeg, pitchDeg, dist, ... }).
 */
import { Suspense, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { Canvas, useThree } from "@react-three/fiber";
import { Color, NeutralToneMapping, Vector3 } from "three";
import JacketModel from "@/three/jacket/JacketModel";
import StudioLighting from "@/three/stage/StudioLighting";
import type { JacketAppearance } from "@/features/configurator/viewer/types";
import { Thread } from "./thread";

const GLB = "/models/fidelio_varsity_v09.glb";
const STUDIO = "#FCF0D6"; // heroLayout.ts STUDIO_COLOUR

// catalog.ts PALETTE: Burgundy felt #64152B, White leather #F1F0E8
const APPEARANCE: JacketAppearance = {
  surfaces: {
    body: { hex: "#64152B", finish: "felt" },
    sleeves: { hex: "#F1F0E8", finish: "leather" },
    trim: { hex: "#64152B", finish: "rib" },
  },
  stripe: "#F1F0E8",
  embroidery: [],
  fit: "relaxed",
  hardware: "silver",
};

export type Shot = { yawDeg: number; pitchDeg: number; dist: number; targetY: number; fov: number; thread?: number | null };
declare global {
  interface Window { previewReady?: boolean; setShot: (s: Shot) => Promise<void>; }
}

let applyShot: (s: Shot) => void = () => {};
let threadT: number | null = null;

function Rig() {
  const { camera, invalidate, gl } = useThree();
  useEffect(() => {
    gl.toneMapping = NeutralToneMapping;
    applyShot = ({ yawDeg, pitchDeg, dist, targetY, fov }) => {
      const yaw = (yawDeg * Math.PI) / 180, pitch = (pitchDeg * Math.PI) / 180;
      const t = new Vector3(0, targetY, 0);
      camera.position.set(t.x + dist * Math.cos(pitch) * Math.sin(yaw), t.y + dist * Math.sin(pitch), t.z + dist * Math.cos(pitch) * Math.cos(yaw));
      (camera as any).fov = fov;
      camera.lookAt(t);
      camera.updateProjectionMatrix();
      invalidate();
    };
    window.previewReady = true;
  }, [camera, invalidate, gl]);
  return null;
}

function App() {
  return (
    <Canvas
      frameloop="always"
      dpr={1}
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      camera={{ fov: 24, near: 0.05, far: 50, position: [0, 0.6, 3.2] }}
      onCreated={({ scene }) => { scene.background = new Color(STUDIO); }}
    >
      <StudioLighting />
      <Suspense fallback={null}>
        <JacketModel appearance={APPEARANCE} silhouette="male" url={GLB} />
        <Rig />
        <ThreadSlot />
      </Suspense>
    </Canvas>
  );
}

function ThreadSlot() {
  // the thread is only drawn when a shot asks for it (phase 2)
  return <Thread getT={() => threadT} />;
}

window.setShot = async (s) => {
  threadT = s.thread ?? null;
  applyShot(s);
  // let a few frames render (environment map, materials, thread)
  await new Promise((r) => setTimeout(r, 250));
};

createRoot(document.getElementById("root")!).render(<App />);
