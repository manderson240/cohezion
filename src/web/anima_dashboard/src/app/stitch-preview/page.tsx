import React from 'react';
import { GenesisCard } from '@/components/GenesisCard';
import { CoherenceIndicator } from '@/components/CoherenceIndicator';

/**
 * Stitch Research Terminal - Page Layout
 * Demonstrates the Triune Substrate monitoring dashboard.
 */

export default function StitchPreviewPage() {
  return (
    <div 
      data-testid="stitch-preview-container"
      style={{ 
        backgroundColor: "#020208", // Void background
        minHeight: "100vh",
        padding: "40px",
        color: "#e0e0e6"
      }}
    >
      <header style={{ marginBottom: "48px" }}>
        <h1 style={{ 
          fontSize: "2rem", 
          fontWeight: 700, 
          letterSpacing: "-0.02em",
          color: "#3a86ff" // Info/Space accent
        }}>
          GENESIS_ENGINE // <span style={{ opacity: 0.5 }}>RESEARCH_STATION</span>
        </h1>
        <p style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "#666" }}>
          TRIUNE_SUBSTRATE: STRIX_HALO_GFX1151 [WAVE32_UNLOCKED]
        </p>
      </header>

      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", 
        gap: "24px" 
      }}>
        {/* NPU Monitor */}
        <GenesisCard 
          title="NPU Analysis Lane" 
          accent="#00ff88"
          footerMetric="THROUGHPUT"
          footerValue="111.4 TPS"
        >
          <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <CoherenceIndicator value={0.5002} />
            <p style={{ fontSize: "0.8rem", color: "#888", marginTop: "16px" }}>
              FastFlowLM (FLM) backend active. Port 13306 processing 4B context.
            </p>
          </div>
        </GenesisCard>

        {/* iGPU Monitor */}
        <GenesisCard 
          title="iGPU Synthesis Engine" 
          accent="#f72585"
          footerMetric="VRAM_USED"
          footerValue="32.4 GB"
        >
          <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <CoherenceIndicator value={0.4998} />
            <p style={{ fontSize: "0.8rem", color: "#888", marginTop: "16px" }}>
              TurboKVKernel executing Wave32-aligned fused attention. 128k horizon stable.
            </p>
          </div>
        </GenesisCard>

        {/* System Coherence */}
        <GenesisCard 
          title="Manifold Stability" 
          accent="#3a86ff"
          footerMetric="STABILITY_DELTA"
          footerValue="0.0008"
        >
          <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
             <div style={{ 
               width: "120px", 
               height: "120px", 
               borderRadius: "50%", 
               border: "2px dashed #3a86ff",
               display: "flex",
               alignItems: "center",
               justifyContent: "center",
               fontFamily: "JetBrains Mono, monospace",
               fontSize: "1.5rem",
               color: "#fff",
               boxShadow: "0 0 30px rgba(58, 134, 255, 0.2)"
             }}>
               0.5
             </div>
             <p style={{ fontSize: "0.7rem", color: "#666", marginTop: "20px", textAlign: "center" }}>
               HIHO ATTRACTOR REACHED // ZERO DRIFT DETECTED
             </p>
          </div>
        </GenesisCard>
      </div>
    </div>
  );
}
