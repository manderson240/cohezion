import { NextResponse } from "next/server";
import { projectPCA } from "@/lib/pca";

// Serve real agentic-journey points (FLUME latent space) from SurrealDB `journey_point`.
// Each point's `physics_state` is the 12D manifold position (the exotic-vacuum-object analogue
// coordinates); `coherence` drives the colour. Projected 12D -> 3D on three physics axes.
// These journeys were produced by GAIA-backed local inference (model_used e.g. igpu:architect).
//
// Two consumers, two shapes — served together:
//   - genesis/FlumeLatentViz.tsx  POSTs, reads `data.samples[].pca` + `.coherence`
//   - FlumeNavigator.tsx          reads `data.points` (number[][]) + `data.coherence_scores`

const SURREAL = process.env.SURREAL_HTTP ?? "http://localhost:8001/sql";
const NS = "cohezion";
const DB = "main";
const AUTH = "Basic " + Buffer.from("root:root").toString("base64");
const AXES = ["biology", "control", "field"]; // physics-manifold coords to project onto

export const dynamic = "force-dynamic";

async function buildData(limit: number) {
  const q = `SELECT physics_state, coherence, skill_used, phase, timestamp FROM journey_point ORDER BY timestamp DESC LIMIT ${limit};`;
  const res = await fetch(SURREAL, {
    method: "POST",
    headers: {
      "surreal-ns": NS,
      "surreal-db": DB,
      "Content-Type": "text/plain",
      Accept: "application/json",
      Authorization: AUTH,
    },
    body: q,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`surrealdb ${res.status}`);
  const data = await res.json();
  const rows: Array<Record<string, unknown>> = data?.[0]?.result ?? [];

  // Collect valid rows as full physics-manifold vectors (consistent key order) + metadata.
  let keys: string[] = [];
  const kept: Array<{ vec: number[]; coherence: number; skill: string; phase: string }> = [];
  for (const r of rows) {
    const ps = (r.physics_state ?? {}) as Record<string, number>;
    const numeric = Object.keys(ps).filter((k) => typeof ps[k] === "number").sort();
    if (numeric.length < 3) continue;
    if (keys.length === 0) keys = numeric; // fix axis order from the first valid row
    kept.push({
      vec: keys.map((k) => Number(ps[k] ?? 0)),
      coherence: Number(r.coherence ?? 0.5),
      skill: String(r.skill_used ?? ""),
      phase: String(r.phase ?? ""),
    });
  }

  // Project the full physics manifold onto its top-3 principal (statistically informative)
  // directions via Jacobi PCA — the faithful stored-data analogue of the Fisher-optimal
  // reduction (the true Fisher metric needs the encoder Jacobian, absent from journey_point).
  const { projected, eigenvalues } =
    kept.length > 0 ? projectPCA(kept.map((k) => k.vec), 3) : { projected: [], eigenvalues: [] };

  const points: number[][] = [];
  const coherence_scores: number[] = [];
  const samples: Array<{ pca: number[]; coherence: number; skill: string; phase: string }> = [];
  let quadrature = 0;
  for (let i = 0; i < kept.length; i++) {
    const pca = projected[i] ?? [0, 0, 0];
    while (pca.length < 3) pca.push(0);
    points.push(pca);
    coherence_scores.push(kept[i].coherence);
    samples.push({ pca, coherence: kept[i].coherence, skill: kept[i].skill, phase: kept[i].phase });
    if (kept[i].skill === "quadrature_nexus") quadrature += 1;
  }
  return {
    points,
    coherence_scores,
    samples,
    count: points.length,
    axes: keys.length ? keys.slice(0, 3) : AXES,
    manifold_dims: keys.length,
    eigenvalues,
    quadrature_nexus_points: quadrature,
    source: "surrealdb:cohezion/main/journey_point",
    note: "12D physics_state manifold -> top-3 principal directions (Jacobi PCA); GAIA-backed journeys",
  };
}

function limitFrom(url: string): number {
  return Math.min(Number(new URL(url).searchParams.get("limit") ?? 800), 4000);
}

async function respond(limit: number) {
  try {
    return NextResponse.json(await buildData(limit));
  } catch (e) {
    return NextResponse.json(
      { points: [], coherence_scores: [], samples: [], count: 0, error: String(e) },
      { status: 200 },
    );
  }
}

export async function GET(request: Request) {
  return respond(limitFrom(request.url));
}

export async function POST(request: Request) {
  let limit = 800;
  try {
    const body = await request.json();
    if (body && typeof body.limit === "number") limit = Math.min(body.limit, 4000);
  } catch {
    /* empty body is fine */
  }
  return respond(limit);
}
