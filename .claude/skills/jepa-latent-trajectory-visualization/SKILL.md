---
name: jepa-latent-trajectory-visualization
description: |
  Pattern for adding explicit structured primitive decoders + 3D trajectory
  visualization to a JEPA world model (Cohezion). Implements FLAT paper
  (arxiv 2606.24876) approach: latent → explicit geometry.
  Use when: adding visual representation of latent space to Genesis UI,
  implementing structured output heads on world models, or building
  Three.js mesh components from API trajectory data.
  Components: StatePrimitiveHead (backend), trajectory_for_viz (backend),
  FastAPI endpoint, JEPATrajectoryMesh.tsx (React Three Fiber).
author: Claude Code
version: 1.0.0
---

# JEPA Latent Trajectory Visualization (FLAT Pattern)

## Problem

JEPA world models produce opaque 64D latent trajectories. Need: (1) explicit structured primitives for interpretability, (2) 3D visualization in Genesis UI with curvature-coded surprise.

## Core Insight (FLAT, arxiv 2606.24876)

Explicit structured primitives decoded from latents in one forward pass beat dense volumetric representations when structural correctness matters.

## Backend: StatePrimitiveHead

```python
class StatePrimitiveHead(nn.Module):
    FABRICS = ("Space", "Field", "Control", "Precipitation")
    N_FABRICS = 4
    PARAMS_PER = 4  # (x, y, z, scale)

    def __init__(self, embed_dim: int = 64) -> None:
        super().__init__()
        self.decode = nn.Linear(embed_dim, self.N_FABRICS * self.PARAMS_PER)
        nn.init.normal_(self.decode.weight, std=0.01)  # near-zero init
        nn.init.zeros_(self.decode.bias)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        raw = self.decode(z).view(-1, self.N_FABRICS, self.PARAMS_PER)
        xyz = torch.tanh(raw[..., :3])       # bounded [-1, 1]
        scale = nn.functional.softplus(raw[..., 3:4])  # positive
        return torch.cat([xyz, scale], dim=-1)
```

**Key**: near-zero init (std=0.01) prevents disrupting existing latent structure.

## Backend: trajectory_for_viz method

```python
def trajectory_for_viz(self, initial_state, actions, n_predict_ahead=5) -> dict:
    # 1. Simulate past trajectory in latent space
    past = self.simulate_latent_trajectory(initial_state, actions)
    # 2. Project 64D → 3D via top-3 causal dims
    causal_dims = self.top_k_causal_dims(3)
    points_3d = [[float(s[d]) for d in causal_dims] for s in past]
    # 3. Per-step curvature = 1 - cosine_similarity(v_t, v_{t+1}), normalized
    curvatures = compute_curvatures(past)  # list[float] in [0, 1]
    # 4. Predict n_predict_ahead zero-action steps ahead
    predicted_3d = predict_future(past[-1], n_predict_ahead)
    # 5. Extract fabric primitives from terminal predicted state
    fabric_primitives = self.primitive_head.to_list(...)
    return {"points_3d": points_3d, "curvatures": curvatures,
            "predicted_3d": predicted_3d, "fabric_primitives": fabric_primitives,
            "causal_dims": causal_dims, "n_points": len(points_3d), "n_predicted": n_predict_ahead}
```

## FastAPI endpoint

```python
@genesis_router.get("/jepa/trajectory")
async def get_jepa_trajectory(n_steps: int = 30, n_predict: int = 5) -> dict:
    model = JEPAWorldModel()
    data = generate_synthetic_training_data(n_samples=200)
    for _ in range(3):
        model.train_epoch(data, batch_size=32)
    rng = np.random.default_rng(42)
    initial_state = rng.uniform(0.2, 0.8, 12).astype(np.float32)
    actions = [rng.normal(0, 0.02, 12).astype(np.float32) for _ in range(n_steps)]
    return model.trajectory_for_viz(initial_state, actions, n_predict_ahead=n_predict)
```

## Three.js: TubeGeometry with per-vertex curvature coloring

```typescript
function curvatureColor(c: number): THREE.Color {
  return new THREE.Color().setHSL(0.66 - c * 0.66, 1.0, 0.5); // blue→red
}

function buildTube(pts, curvatures, radius, radialSegments = 6) {
  const curve = new THREE.CatmullRomCurve3(pts.map(([x,y,z]) => new THREE.Vector3(x,y,z)));
  const geo = new THREE.TubeGeometry(curve, pts.length * 3, radius, radialSegments, false);
  // Per-vertex color: map each ring segment to closest curvature sample
  const colors = new Float32Array(geo.attributes.position.count * 3);
  const vertsPerRing = radialSegments + 1;
  for (let seg = 0; seg <= pts.length * 3; seg++) {
    const cIdx = Math.floor((seg / (pts.length * 3)) * (curvatures.length - 1));
    const col = curvatureColor(curvatures[cIdx]);
    for (let r = 0; r < vertsPerRing; r++) {
      const vi = (seg * vertsPerRing + r) * 3;
      colors[vi] = col.r; colors[vi+1] = col.g; colors[vi+2] = col.b;
    }
  }
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return geo;
}
```

## Fallback (Lissajous) for API-unavailable

```typescript
function generateLocalTrajectory(n = 30): TrajectoryData {
  const points_3d = [];
  for (let i = 0; i < n; i++) {
    const t = (i / n) * Math.PI * 4;
    points_3d.push([Math.sin(t)*1.5, Math.sin(t*1.3+0.5)*1.2, Math.cos(t*0.7)*1.0]);
  }
  // curvatures: 0.3 + 0.4 * |sin(t)|
}
```

## Wiring checklist

- [ ] `StatePrimitiveHead` added to model `__init__` after decoder
- [ ] Add `list(self.primitive_head.parameters())` to optimizer param group
- [ ] Include in `_set_inference_mode()` loop
- [ ] Add `"primitive_head": self.primitive_head.state_dict()` to `save()`
- [ ] Optional load in `load()` (backwards compat)
- [ ] FastAPI endpoint registered on genesis_router
- [ ] React component uses `useFrame` for slow rotation (`delta * 0.08`)
- [ ] Predicted extension: `transparent`, `opacity=0.38`, `depthWrite=false`
- [ ] Wire into GenesisScene.tsx Canvas: `<JEPATrajectoryMesh scale={2.0} />`

## Files modified (Cohezion)

- `src/cohezion/world_model/jepa_world_model.py` — StatePrimitiveHead class + methods
- `src/cohezion/api/services/genesis.py` — GET /api/genesis/jepa/trajectory
- `src/web/anima_dashboard/src/components/genesis/JEPATrajectoryMesh.tsx` — new file
