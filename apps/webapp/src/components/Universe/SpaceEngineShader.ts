import * as THREE from 'three';

export const SpaceEngineShader = {
    uniforms: {
        uTime: { value: 0 },
        uSize: { value: 100 },
    },
    vertexShader: `
        uniform float uTime;
        uniform float uSize;
        attribute float grade;
        attribute vec3 color;
        varying vec3 vColor;
        varying float vGrade;

        void main() {
            vColor = color;
            vGrade = grade;
            
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            
            // Subtle pulse based on grade (Novelty)
            float s = 1.0 + sin(uTime * 2.0 + position.x * 10.0) * 0.1 * grade;
            
            gl_PointSize = uSize * s * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
        }
    `,
    fragmentShader: `
        varying vec3 vColor;
        varying float vGrade;

        void main() {
            float dist = distance(gl_PointCoord, vec2(0.5));
            if (dist > 0.5) discard;
            
            // Celestial glow
            float alpha = 1.0 - smoothstep(0.4, 0.5, dist);
            float innerGlow = 1.0 - smoothstep(0.0, 0.4, dist);
            
            vec3 finalColor = vColor + (innerGlow * 0.5);
            
            gl_FragColor = vec4(finalColor, alpha * 0.8);
        }
    `
};
