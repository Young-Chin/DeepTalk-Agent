// frontend/src/components/Waveform.tsx
import { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import * as THREE from 'three'
import { ConversationState } from '../types'

interface WaveformProps {
  state: ConversationState
  frequencyData: Uint8Array | null
  isRecording: boolean
}

// Perlin noise vertex shader for organic deformation
const vertexShader = `
  varying vec2 vUv;
  varying float vDisplacement;
  uniform float uTime;
  uniform float uIntensity;
  uniform float uAudioIntensity;

  vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
  vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
  vec3 fade(vec3 t) {return t*t*t*(t*(t*6.0-15.0)+10.0);}

  float cnoise(vec3 P){
    vec3 Pi0 = floor(P); vec3 Pi1 = Pi0 + vec3(1.0);
    Pi0 = mod(Pi0, 289.0); Pi1 = mod(Pi1, 289.0);
    vec3 Pf0 = fract(P); vec3 Pf1 = Pf0 - vec3(1.0);
    vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
    vec4 iy = vec4(Pi0.yy, Pi1.yy);
    vec4 iz0 = Pi0.zzzz; vec4 iz1 = Pi1.zzzz;
    vec4 ixy = permute(permute(ix) + iy);
    vec4 ixy0 = permute(ixy + iz0); vec4 ixy1 = permute(ixy + iz1);
    vec4 gx0 = ixy0 / 7.0; vec4 gy0 = fract(floor(gx0) / 7.0) - 0.5;
    gx0 = fract(gx0);
    vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
    vec4 sz0 = step(gz0, vec4(0.0));
    gx0 -= sz0 * (step(0.0, gx0) - 0.5);
    gy0 -= sz0 * (step(0.0, gy0) - 0.5);
    vec4 gx1 = ixy1 / 7.0; vec4 gy1 = fract(floor(gx1) / 7.0) - 0.5;
    gx1 = fract(gx1);
    vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
    vec4 sz1 = step(gz1, vec4(0.0));
    gx1 -= sz1 * (step(0.0, gx1) - 0.5);
    gy1 -= sz1 * (step(0.0, gy1) - 0.5);
    vec3 g000 = vec3(gx0.x,gy0.x,gz0.x); vec3 g100 = vec3(gx0.y,gy0.y,gz0.y);
    vec3 g010 = vec3(gx0.z,gy0.z,gz0.z); vec3 g110 = vec3(gx0.w,gy0.w,gz0.w);
    vec3 g001 = vec3(gx1.x,gy1.x,gz1.x); vec3 g101 = vec3(gx1.y,gy1.y,gz1.y);
    vec3 g011 = vec3(gx1.z,gy1.z,gz1.z); vec3 g111 = vec3(gx1.w,gy1.w,gz1.w);
    vec4 norm0 = taylorInvSqrt(vec4(dot(g000,g000),dot(g100,g100),dot(g010,g010),dot(g110,g110)));
    g000 *= norm0.x; g100 *= norm0.y; g010 *= norm0.z; g110 *= norm0.w;
    vec4 norm1 = taylorInvSqrt(vec4(dot(g001,g001),dot(g101,g101),dot(g011,g011),dot(g111,g111)));
    g001 *= norm1.x; g101 *= norm1.y; g011 *= norm1.z; g111 *= norm1.w;
    float n000 = dot(g000, Pf0); float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
    float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z)); float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
    float n001 = dot(g001, vec3(Pf0.xy, Pf1.z)); float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
    float n011 = dot(g011, vec3(Pf0.x, Pf1.yz)); float n111 = dot(g111, Pf1);
    vec3 fade_xyz = fade(Pf0);
    vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
    vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
    float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
    return 2.2 * n_xyz;
  }

  void main() {
    vUv = uv;
    float noise = cnoise(position * 2.0 + uTime * 0.5);
    float audioNoise = cnoise(position * 4.0 + uTime * 2.0) * uAudioIntensity;
    vDisplacement = noise * uIntensity + audioNoise;
    vec3 newPosition = position + normal * vDisplacement;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
  }
`

const fragmentShader = `
  varying vec2 vUv;
  varying float vDisplacement;
  uniform vec3 uColorA;
  uniform vec3 uColorB;

  void main() {
    float strength = vDisplacement * 2.0;
    vec3 color = mix(uColorA, uColorB, strength + 0.5);
    gl_FragColor = vec4(color, 0.85);
  }
`

interface OrbMeshProps {
  state: ConversationState
  audioAmplitude: number
}

function OrbMesh({ state, audioAmplitude }: OrbMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uIntensity: { value: 0.15 },
    uAudioIntensity: { value: 0 },
    uColorA: { value: new THREE.Color('#4facfe') },
    uColorB: { value: new THREE.Color('#00f2fe') },
  }), [])

  useFrame((frameState) => {
    if (!meshRef.current) return
    const t = frameState.clock.getElapsedTime()
    uniforms.uTime.value = t

    // Audio-driven intensity
    const audioTarget = audioAmplitude * 0.6
    uniforms.uAudioIntensity.value = THREE.MathUtils.lerp(
      uniforms.uAudioIntensity.value, audioTarget, 0.15
    )

    // Status-driven base intensity
    let targetIntensity = 0.08
    if (state === 'DREAMING') targetIntensity = 0.08 + Math.sin(t * 1.5) * 0.03
    else if (state === 'SPEAKING') targetIntensity = 0.35 + Math.sin(t * 8) * 0.08
    else if (state === 'LISTENING') targetIntensity = 0.15 + Math.sin(t * 4) * 0.04
    else if (state === 'THINKING') targetIntensity = 0.12 + Math.sin(t * 2) * 0.02
    else if (state === 'TRANSCRIBING') targetIntensity = 0.2 + Math.sin(t * 6) * 0.05
    uniforms.uIntensity.value = THREE.MathUtils.lerp(uniforms.uIntensity.value, targetIntensity, 0.08)

    // Status-driven colors
    if (state === 'DREAMING') {
      uniforms.uColorA.value.lerp(new THREE.Color('#8b5cf6'), 0.04)
      uniforms.uColorB.value.lerp(new THREE.Color('#a78bfa'), 0.04)
    } else if (state === 'THINKING' || state === 'TRANSCRIBING') {
      uniforms.uColorA.value.lerp(new THREE.Color('#8e44ad'), 0.04)
      uniforms.uColorB.value.lerp(new THREE.Color('#3498db'), 0.04)
    } else if (state === 'SPEAKING') {
      uniforms.uColorA.value.lerp(new THREE.Color('#00c6ff'), 0.04)
      uniforms.uColorB.value.lerp(new THREE.Color('#0072ff'), 0.04)
    } else if (state === 'LISTENING') {
      uniforms.uColorA.value.lerp(new THREE.Color('#4facfe'), 0.04)
      uniforms.uColorB.value.lerp(new THREE.Color('#00f2fe'), 0.04)
    }

    meshRef.current.rotation.y += 0.008
    meshRef.current.rotation.z += 0.004
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[2, 128, 128]} />
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        wireframe
      />
    </mesh>
  )
}

export function Waveform({ state, frequencyData }: WaveformProps) {
  const amplitudeRef = useRef(0)

  useEffect(() => {
    if (!frequencyData || frequencyData.length === 0) {
      amplitudeRef.current *= 0.95
      return
    }
    let sum = 0
    for (let i = 0; i < frequencyData.length; i++) sum += frequencyData[i]
    amplitudeRef.current = sum / frequencyData.length / 255
  }, [frequencyData])

  return (
    <div className="relative w-full h-[280px] flex items-center justify-center">
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <OrbMesh state={state} audioAmplitude={amplitudeRef.current} />
        </Float>
      </Canvas>

      {/* Decorative Rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[280px] h-[280px] border border-white/5 rounded-full animate-[spin_20s_linear_infinite]" />
        <div className="absolute w-[320px] h-[320px] border border-white/[0.03] rounded-full animate-[spin_30s_linear_infinite_reverse]" />
      </div>
    </div>
  )
}
