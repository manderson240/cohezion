import * as THREE from 'three';

export const HIHOShader = {
    uniforms: {
        uTime: { value: 0 },
        uSize: { value: 25 },
        uBaseColor: { value: new THREE.Color("#00FF88") } // Nexus Green
    },
    vertexShader: `
        uniform float uTime;
        uniform float uSize;
        
        attribute float awareness;
        attribute float stability; // 1.0 - abs(coherence - 0.5) * 2.0
        attribute float novelty;
        attribute float precipitation;
        
        varying float vAwareness;
        varying float vStability;
        varying float vNovelty;
        varying float vPrecipitation;
        varying vec3 vColor;

        void main() {
            vAwareness = awareness;
            vStability = stability;
            vNovelty = novelty;
            vPrecipitation = precipitation;
            
            // Color shift based on Novelty (D11)
            // Range from Nexus Green to Royal Purple
            vec3 lowNovelty = vec3(0.0, 1.0, 0.53); // #00FF88
            vec3 highNovelty = vec3(0.5, 0.0, 1.0); // #8000FF
            vColor = mix(lowNovelty, highNovelty, novelty);

            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            
            // Size scales with Precipitation (D12) and Stability
            float s = uSize * (0.5 + precipitation * 1.5) * (0.8 + stability * 0.4);
            
            gl_PointSize = s * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
        }
    `,
    fragmentShader: `
        varying float vAwareness;
        varying float vStability;
        varying float vNovelty;
        varying float vPrecipitation;
        varying vec3 vColor;

        void main() {
            float dist = distance(gl_PointCoord, vec2(0.5));
            if (dist \u003e 0.5) discard;
            
            // Awareness dictates the core luminosity
            // Stability dictates the edge hardness (The 0.5 Rule)
            
            float edgeSoftness = 0.45 - (vStability * 0.3); // High stability = sharp edge
            float alpha = 1.0 - smoothstep(edgeSoftness, 0.5, dist);
            
            // Add a "Crystalline" core for high stability
            float core = 1.0 - smoothstep(0.0, 0.1, dist);
            vec3 finalColor = vColor + (core * vStability * 0.8);
            
            // Intensity modulation by Awareness
            float intensity = vAwareness * 1.2;
            
            gl_FragColor = vec4(finalColor * intensity, alpha * vPrecipitation);
        }
    `
};
