"use client";

import React from 'react';
import { motion } from 'framer-motion';

/**
 * Stitch Design System - GenesisCard
 * Implements the "Dark Matter" aesthetic with neon accents.
 */

interface GenesisCardProps {
  title: string;
  accent?: string;
  glow?: boolean;
  children: React.ReactNode;
  footerMetric?: string;
  footerValue?: string | number;
}

export const GenesisCard: React.FC<GenesisCardProps> = ({
  title,
  accent = "#00d4aa", // Default to HIHO Coherence teal
  glow = true,
  children,
  footerMetric,
  footerValue
}) => {
  return (
    <motion.div
      whileHover={{ y: -2, borderColor: accent }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      style={{
        backgroundColor: "#0a0a12", // Matter panel
        border: `1px solid #222`,
        borderRadius: "12px",
        padding: "24px",
        position: "relative",
        overflow: "hidden",
        fontFamily: "Inter, sans-serif",
        boxShadow: glow ? `inset 0 0 20px ${accent}15` : "none",
        display: "flex",
        flexDirection: "column",
        gap: "16px"
      }}
    >
      {/* Accent Top Bar */}
      <div style={{ 
        position: "absolute", 
        top: 0, 
        left: 0, 
        right: 0, 
        height: "3px", 
        backgroundColor: accent 
      }} />

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ 
          margin: 0, 
          color: "#e0e0e6", 
          fontSize: "1.1rem", 
          textTransform: "uppercase", 
          letterSpacing: "1px" 
        }}>
          {title}
        </h3>
        <span style={{ color: "#444" }}>▸</span>
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, minHeight: "150px" }}>
        {children}
      </div>

      {/* Footer Metrics */}
      {(footerMetric || footerValue) && (
        <div style={{ 
          borderTop: "1px solid #222", 
          paddingTop: "12px", 
          display: "flex", 
          gap: "8px",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.85rem"
        }}>
          <span style={{ color: "#888" }}>{footerMetric}:</span>
          <span style={{ color: "#fff", fontWeight: "bold" }}>{footerValue}</span>
        </div>
      )}
    </motion.div>
  );
};
