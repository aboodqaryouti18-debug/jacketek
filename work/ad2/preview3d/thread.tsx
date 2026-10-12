/**
 * Phase 2: one thin burgundy sewing thread travelling around the jacket in
 * 3D. It is a real tube in the same scene, so the depth buffer gives true
 * occlusion: it passes in front of the jacket and disappears behind it.
 *
 * The path is a slow, descending spiral (almost two turns) around the
 * jacket's vertical axis; the visible part is a moving window along the
 * path (head + trailing length), set per frame through getT() in 0..1.
 */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { CatmullRomCurve3, Color, Mesh, TubeGeometry, Vector3 } from "three";

const SEGMENTS = 1400;
const RADIUS = 0.0016;          // 1.6 mm thread
const TRAIL = 0.34;             // visible share of the whole path

export function threadPath() {
  const pts: Vector3[] = [];
  const n = 60;
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const th = (-110 + u * 610) * (Math.PI / 180);      // ~1.7 turns, front = +z
    const r = 0.46 + 0.035 * Math.sin(2 * th + 0.6);    // stays clear of the garment
    const y = 0.66 - 0.42 * u + 0.025 * Math.sin(3 * th);
    pts.push(new Vector3(r * Math.sin(th), y, r * Math.cos(th)));
  }
  return new CatmullRomCurve3(pts, false, "centripetal");
}

export function Thread({ getT }: { getT: () => number | null }) {
  const ref = useRef<Mesh>(null);
  const geom = useMemo(() => new TubeGeometry(threadPath(), SEGMENTS, RADIUS, 8, false), []);
  const perSeg = 8 * 6; // indices per tubular segment (radialSegments * 2 triangles * 3)

  useFrame(() => {
    const m = ref.current;
    if (!m) return;
    const t = getT();
    m.visible = t !== null;
    if (t === null) return;
    const head = t * (1 + TRAIL);
    const s0 = Math.max(0, head - TRAIL), s1 = Math.min(1, head);
    const a = Math.floor(s0 * SEGMENTS), b = Math.floor(s1 * SEGMENTS);
    geom.setDrawRange(a * perSeg, Math.max(0, b - a) * perSeg);
  });

  return (
    <mesh ref={ref} geometry={geom} visible={false} frustumCulled={false}>
      <meshPhysicalMaterial color={new Color("#64152B")} roughness={0.55} sheen={1} sheenColor={new Color("#9a3a52")} sheenRoughness={0.4} />
    </mesh>
  );
}
