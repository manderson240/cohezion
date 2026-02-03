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
        varying vec2 vUv;

        // High-fidelity noise for filament dynamics
        vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
        vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

        float snoise(vec3 v) {
            const vec2  C = vec2(1.0/6.0, 1.0/3.0);
            const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
            vec3 i  = floor(v + dot(v, C.yyy));
            vec3 x0 = v - i + dot(i, C.xxx);
            vec3 g = step(x0.yzx, x0.xyz);
            vec3 l = 1.0 - g;
            vec3 i1 = min( g.xyz, l.zxy );
            vec3 i2 = max( g.xyz, l.zxy );
            vec3 x1 = x0 - i1 + C.xxx;
            vec3 x2 = x0 - i2 + C.yyy;
            vec3 x3 = x0 - D.yyy;
            i = mod289(i);
            vec4 p = permute( permute( permute(
                      i.z + vec4(0.0, i1.z, i2.z, 1.0))
                    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
                    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
            float n_ = 0.142857142857;
            vec3 ns = n_ * D.wyz - p.xzw * n_;
            vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
            vec4 x_ = floor(j * ns.z);
            vec4 y_ = floor(j - 7.0 * x_ );
            vec4 x = x_ * ns.x + ns.yyyy;
            vec4 y = y_ * ns.x + ns.yyyy;
            vec4 h = 1.0 - abs(x) - abs(y);
            vec4 b0 = vec4( x.xy, y.xy );
            vec4 b1 = vec4( x.zw, y.zw );
            vec4 s0 = floor(b0)*2.0 + 1.0;
            vec4 s1 = floor(b1)*2.0 + 1.0;
            vec4 sh = -step(h, vec4(0.0));
            vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
            vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
            vec3 p0 = vec3(a0.xy,h.x);
            vec3 p1 = vec3(a0.zw,h.y);
            vec3 p2 = vec3(a1.xy,h.z);
            vec3 p3 = vec3(a1.zw,h.w);
            vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
            p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
            vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
            m = m * m;
            return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
        }

        void main() {
            vAwareness = awareness;
            vStability = stability;
            vNovelty = novelty;
            vPrecipitation = precipitation;
            vUv = uv;
            
            // Filament Perturbation
            vec3 pos = position;
            float noise = snoise(pos * 2.0 + uTime * 0.1);
            pos += normalize(pos) * noise * (1.0 - stability) * 0.5;

            // Lattice Alignment (Project to 12-sided symmetry)
            float lattice = abs(sin(pos.x * 12.0) * cos(pos.y * 12.0) * sin(pos.z * 12.0));
            pos *= (1.0 + lattice * 0.1 * stability);

            // Quadrature Geometry proof layer (geometric scaling)
            float quad = 0.0;
            if (stability > 0.8) {
                quad = sin(pos.x * 20.0 + uTime) * sin(pos.y * 20.0) * stability;
                pos += normalize(pos) * quad * 0.02;
            }

            // Color shift based on Novelty (D11)
            // Range from Nexus Green to Royal Purple
            vec3 lowNovelty = vec3(0.0, 1.0, 0.53); // #00FF88
            vec3 highNovelty = vec3(0.5, 0.0, 1.0); // #8000FF
            vColor = mix(lowNovelty, highNovelty, novelty);

            vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
            
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
        varying vec2 vUv;

        void main() {
            float dist = distance(gl_PointCoord, vec2(0.5));
            if (dist > 0.5) discard;
            
            // Awareness dictates the core luminosity
            // Stability dictates the edge hardness (The 0.5 Rule)
            
            // Hyper-fidelity crystalline core
            float edgeSoftness = 0.45 - (vStability * 0.35); // High stability = sharp edge
            float alpha = 1.0 - smoothstep(edgeSoftness, 0.5, dist);
            
            // Add a "Crystalline" core for high stability
            // Additive "lattice" pulse
            float latticePulse = sin(vStability * 10.0 + vAwareness * 5.0) * 0.5 + 0.5;
            vec3 finalColor = vColor + (vStability * 0.9) + (latticePulse * 0.2);
            
            // Intensity modulation by Awareness
            float intensity = vAwareness * 1.5;
            
            gl_FragColor = vec4(finalColor * intensity, alpha * vPrecipitation);
            
            // Glow effect
            float glow = (1.0 - dist * 2.0) * 0.5;
            gl_FragColor.rgb += vColor * glow * vStability;
        }
    `
};
