"use client";

import React from 'react';
import { motion } from 'framer-motion';

/**
 * Stitch Design System - CoherenceIndicator
 * Visualizes HIHO stability distance from the 0.5 attractor.
 */

interface CoherenceIndicatorProps {
  value: number; // 0.0 to 1.0
}

export const CoherenceIndicator: React.FC<CoherenceIndicatorProps> = ({ value }) => {
  const delta = Math.abs(value - 0.5);
  
  // Color logic based on delta thresholds
  let color = "#00d4aa"; // healthy
  if (delta > 0.3) color = "#e63946"; // error
  else if (delta > 0.1) color = "#ffb703"; // warning

  return (
    <div style={{ width: "100%", padding: "8px 0" }}>
      <div style={{ 
        display: "flex", 
        justify_content: "space-between", 
        fontFamily: "JetBrains Mono, monospace",
        fontSize: "0.75rem",
        color: "#666",
        marginBottom: "8px"
      }}>
        <span>COHERENCE</span>
        <span style={{ color: "#fff" }}>{value.toFixed(4)}</span>
      </div>
      
      {/* Dial Track */}
      <div style={{ 
        height: "4px", 
        backgroundColor: "#000", 
        borderRadius: "2px", 
        position: "relative",
        display: "flex",
        alignItems: "center"
      }}>
        {/* Attractor Line (0.5) */}
        <div style={{ 
          position: "absolute", 
          left: "50%", 
          height: "12px", 
          width: "1px", 
          backgroundColor: "#333",
          zIndex: 1
        }} />
        
        {/* Value Pointer */}
        <motion.div
          animate={{ left: `${value * 100}%` }}
          transition={{ 
            type: "spring", 
            stiffness: 100, 
            damping: 10,
            mass: 0.5 
          }}
          style={{
            position: "absolute",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: color,
            boxShadow: `0 0 10px ${color}`,
            transform: "translateX(-4px)",
            zIndex: 2
          }}
        />
      </div>
      
      <div style={{ 
        textAlign: "center", 
        fontSize: "0.6rem", 
        color: color, 
        marginTop: "12px",
        fontWeight: "bold",
        opacity: 0.8
      }}>
        {delta < 0.001 ? "STABILITY LOCKED" : `DELTA: ${delta.toFixed(4)}`}
      </div>
    </div>
  );
};
