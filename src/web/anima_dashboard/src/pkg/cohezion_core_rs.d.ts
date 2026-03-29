/**
 * Type declarations for cohezion_core_rs WASM module.
 * Stub — the actual WASM binary is built from src/cohezion-physics-core/ via wasm-pack.
 * The webapp gracefully degrades to JS-only physics when WASM is unavailable.
 */

export class DualStateManifold {
  constructor();
  hydrate(latent: Float32Array): void;
  evolve_axiomatic(dt: number): void;
  get_axiomatic(): Float32Array;
  get_visibility(): number;
  free(): void;
}

export default function init(): Promise<void>;
