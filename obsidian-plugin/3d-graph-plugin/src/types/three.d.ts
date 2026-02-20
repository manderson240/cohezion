/**
 * Type declarations for THREE.js
 * THREE.js v0.150.x doesn't provide its own TypeScript definitions
 * This file provides minimal type stubs to satisfy the TypeScript compiler
 */

declare module 'three' {
  // Vectors and Math
  export class Vector3 {
    x: number;
    y: number;
    z: number;
    constructor(x?: number, y?: number, z?: number);
    copy(v: Vector3): Vector3;
    set(x: number, y: number, z: number): Vector3;
    add(v: Vector3): Vector3;
    sub(v: Vector3): Vector3;
    multiplyScalar(scalar: number): Vector3;
    length(): number;
    normalize(): Vector3;
    clone(): Vector3;
  }

  export class Vector2 {
    x: number;
    y: number;
    constructor(x?: number, y?: number);
    copy(v: Vector2): Vector2;
    set(x: number, y: number): Vector2;
  }

  export class Quaternion {
    x: number;
    y: number;
    z: number;
    w: number;
    constructor(x?: number, y?: number, z?: number, w?: number);
  }

  export class Euler {
    x: number;
    y: number;
    z: number;
    order: string;
    constructor(x?: number, y?: number, z?: number, order?: string);
  }

  export class Matrix4 {
    elements: number[];
    identity(): Matrix4;
    copy(m: Matrix4): Matrix4;
    multiplyMatrices(a: Matrix4, b: Matrix4): Matrix4;
    multiply(m: Matrix4): Matrix4;
    makeTranslation(x: number, y: number, z: number): Matrix4;
    makeRotationX(theta: number): Matrix4;
    makeRotationY(theta: number): Matrix4;
    makeRotationZ(theta: number): Matrix4;
    makeScale(x: number, y: number, z: number): Matrix4;
    compose(position: Vector3, quaternion: Quaternion, scale: Vector3): Matrix4;
    decompose(position: Vector3, quaternion: Quaternion, scale: Vector3): Matrix4;
  }

  // Geometry
  export class BufferGeometry {
    attributes: any;
    index: BufferAttribute | null;
    boundingBox: any;
    boundingSphere: any;
    addAttribute(name: string, attribute: BufferAttribute): BufferGeometry;
    setAttribute(name: string, attribute: BufferAttribute): BufferGeometry;
    getAttribute(name: string): BufferAttribute | undefined;
    deleteAttribute(name: string): BufferGeometry;
    addGroup(start: number, count: number, materialIndex?: number): void;
    clearGroups(): void;
    setIndex(index: BufferAttribute | number[]): BufferGeometry;
    computeBoundingBox(): void;
    computeBoundingSphere(): void;
    computeVertexNormals(): BufferGeometry;
    dispose(): void;
    clone(): BufferGeometry;
    copy(source: BufferGeometry): BufferGeometry;
  }

  export class BufferAttribute {
    array: ArrayLike<number>;
    itemSize: number;
    count: number;
    needsUpdate: boolean;
    constructor(array: ArrayLike<number>, itemSize: number);
    getX(index: number): number;
    getY(index: number): number;
    getZ(index: number): number;
    setX(index: number, x: number): BufferAttribute;
    setY(index: number, y: number): BufferAttribute;
    setZ(index: number, z: number): BufferAttribute;
    setXY(index: number, x: number, y: number): BufferAttribute;
    setXYZ(index: number, x: number, y: number, z: number): BufferAttribute;
  }

  export class SphereGeometry extends BufferGeometry {
    parameters: any;
    constructor(radius?: number, widthSegments?: number, heightSegments?: number, phiStart?: number, phiLength?: number, thetaStart?: number, thetaLength?: number);
  }

  export class BoxGeometry extends BufferGeometry {
    parameters: any;
    constructor(width?: number, height?: number, depth?: number, widthSegments?: number, heightSegments?: number, depthSegments?: number);
  }

  export class CylinderGeometry extends BufferGeometry {
    parameters: any;
    constructor(radiusTop?: number, radiusBottom?: number, height?: number, radialSegments?: number, heightSegments?: number, openEnded?: boolean, thetaStart?: number, thetaLength?: number);
  }

  export class PlaneGeometry extends BufferGeometry {
    parameters: any;
    constructor(width?: number, height?: number, widthSegments?: number, heightSegments?: number);
  }

  export class LineGeometry extends BufferGeometry {}

  // Materials
  export interface MaterialParameters {
    color?: number | string;
    emissive?: number | string;
    emissiveIntensity?: number;
    opacity?: number;
    transparent?: boolean;
    side?: number;
    wireframe?: boolean;
    blending?: number;
    blendSrc?: number;
    blendDst?: number;
    blendEquation?: number;
  }

  export class Material {
    uuid: string;
    name: string;
    blending: number;
    side: number;
    flatShading: boolean;
    opacity: number;
    transparent: boolean;
    wireframe: boolean;
    needsUpdate: boolean;
    dispose(): void;
    clone(): Material;
    copy(source: Material): Material;
  }

  export class MeshBasicMaterial extends Material {
    color: Color;
    emissive: Color;
    emissiveIntensity: number;
    map: any;
    lightMap: any;
    aoMap: any;
    emissiveMap: any;
    bumpMap: any;
    normalMap: any;
    displacementMap: any;
    alphaMap: any;
    envMap: any;
    combine: number;
    reflectivity: number;
    refractionRatio: number;
    fog: boolean;
    constructor(parameters?: MaterialParameters);
  }

  export interface MeshStandardMaterialParameters extends MaterialParameters {
    metalness?: number;
    roughness?: number;
    map?: any;
    lightMap?: any;
    aoMap?: any;
    emissiveMap?: any;
    bumpMap?: any;
    normalMap?: any;
    displacementMap?: any;
    roughnessMap?: any;
    metalnessMap?: any;
    alphaMap?: any;
    envMap?: any;
    envMapIntensity?: number;
  }

  export class MeshStandardMaterial extends Material {
    color: Color;
    emissive: Color;
    emissiveIntensity: number;
    metalness: number;
    roughness: number;
    map: any;
    lightMap: any;
    aoMap: any;
    emissiveMap: any;
    bumpMap: any;
    normalMap: any;
    displacementMap: any;
    roughnessMap: any;
    metalnessMap: any;
    alphaMap: any;
    envMap: any;
    envMapIntensity: number;
    fog: boolean;
    constructor(parameters?: MeshStandardMaterialParameters);
  }

  export class LineBasicMaterial extends Material {
    color: Color;
    linewidth: number;
    fog: boolean;
    constructor(parameters?: MaterialParameters);
  }

  export class Color {
    r: number;
    g: number;
    b: number;
    constructor(color?: number | string | Color);
    copy(color: Color): Color;
    copyGammaToLinear(color: Color, gammaFactor?: number): Color;
    copyLinearToGamma(color: Color, gammaFactor?: number): Color;
    convertGammaToLinear(gammaFactor?: number): Color;
    convertLinearToGamma(gammaFactor?: number): Color;
    getHex(): number;
    getHexString(): string;
    getRGB(target?: any): any;
    getHSL(target?: any): any;
    getStyle(): string;
    offsetHSL(h: number, s: number, l: number): Color;
    add(color: Color): Color;
    addColors(color1: Color, color2: Color): Color;
    addScalar(s: number): Color;
    sub(color: Color): Color;
    multiply(color: Color): Color;
    multiplyScalar(s: number): Color;
    lerp(color: Color, alpha: number): Color;
    equals(color: Color): boolean;
    fromArray(array: number[], offset?: number): Color;
    toArray(array?: number[], offset?: number): number[];
    clone(): Color;
    setHex(hex: number): Color;
    setRGB(r: number, g: number, b: number): Color;
    setHSL(h: number, s: number, l: number): Color;
    setStyle(style: string): Color;
  }

  // Cameras
  export class Camera {
    matrix: Matrix4;
    matrixWorld: Matrix4;
    matrixWorldInverse: Matrix4;
    projectionMatrix: Matrix4;
    projectionMatrixInverse: Matrix4;
    position: Vector3;
    up: Vector3;
    lookAt(x: number | Vector3, y?: number, z?: number): void;
    clone(): Camera;
    copy(source: Camera): Camera;
    getWorldPosition(target: Vector3): Vector3;
    getWorldQuaternion(target: Quaternion): Quaternion;
    getWorldScale(target: Vector3): Vector3;
    getWorldDirection(target: Vector3): Vector3;
    raycast(raycaster: Raycaster, intersects: any[]): void;
    traverse(callback: (object: Object3D) => void): void;
    traverseVisible(callback: (object: Object3D) => void): void;
    traverseAncestors(callback: (object: Object3D) => void): void;
    updateMatrix(): void;
    updateMatrixWorld(force?: boolean): void;
    updateWorldMatrix(updateParents: boolean, updateChildren: boolean): void;
    toJSON(meta?: any): any;
  }

  export class PerspectiveCamera extends Camera {
    fov: number;
    aspect: number;
    near: number;
    far: number;
    zoom: number;
    focus: number;
    view: any;
    constructor(fov?: number, aspect?: number, near?: number, far?: number);
    setFocalLength(focalLength: number): void;
    getFocalLength(): number;
    getEffectiveFieldOfView(): number;
    getFilmWidth(): number;
    getFilmHeight(): number;
    getCodex(): any;
    setViewOffset(fullWidth: number, fullHeight: number, x: number, y: number, width: number, height: number): void;
    clearViewOffset(): void;
  }

  export class OrthographicCamera extends Camera {
    zoom: number;
    view: any;
    left: number;
    right: number;
    top: number;
    bottom: number;
    near: number;
    far: number;
    constructor(left?: number, right?: number, top?: number, bottom?: number, near?: number, far?: number);
    setViewOffset(fullWidth: number, fullHeight: number, x: number, y: number, width: number, height: number): void;
    clearViewOffset(): void;
  }

  // Objects
  export class Object3D {
    uuid: string;
    name: string;
    type: string;
    parent: Object3D | null;
    children: Object3D[];
    up: Vector3;
    position: Vector3;
    rotation: Euler;
    quaternion: Quaternion;
    scale: Vector3;
    modelViewMatrix: Matrix4;
    normalMatrix: any;
    matrix: Matrix4;
    matrixWorld: Matrix4;
    matrixAutoUpdate: boolean;
    matrixWorldAutoUpdate: boolean;
    matrixWorldNeedsUpdate: boolean;
    visible: boolean;
    castShadow: boolean;
    receiveShadow: boolean;
    frustumCulled: boolean;
    renderOrder: number;
    animations: any[];
    userData: any;
    customDepthMaterial: Material | undefined;
    customDistanceMaterial: Material | undefined;
    readonly isObject3D: true;

    constructor();
    onBeforeRender(renderer: WebGLRenderer, scene: Scene, camera: Camera, geometry: BufferGeometry, material: Material, group: any): void;
    onAfterRender(renderer: WebGLRenderer, scene: Scene, camera: Camera, geometry: BufferGeometry, material: Material, group: any): void;
    applyMatrix4(matrix: Matrix4): Object3D;
    applyQuaternion(quaternion: Quaternion): Object3D;
    setRotationFromAxisAngle(axis: Vector3, angle: number): Object3D;
    setRotationFromEuler(euler: Euler): Object3D;
    setRotationFromMatrix(m: Matrix4): Object3D;
    setRotationFromQuaternion(q: Quaternion): Object3D;
    rotateOnWorldAxis(axis: Vector3, angle: number): Object3D;
    rotateOnAxis(axis: Vector3, angle: number): Object3D;
    rotateX(angle: number): Object3D;
    rotateY(angle: number): Object3D;
    rotateZ(angle: number): Object3D;
    translateOnAxis(axis: Vector3, distance: number): Object3D;
    translateX(distance: number): Object3D;
    translateY(distance: number): Object3D;
    translateZ(distance: number): Object3D;
    localToWorld(vector: Vector3): Vector3;
    worldToLocal(vector: Vector3): Vector3;
    lookAt(x: number | Vector3, y?: number, z?: number): void;
    add(...object: Object3D[]): Object3D;
    remove(...object: Object3D[]): Object3D;
    removeFromParent(): Object3D;
    clear(): Object3D;
    getObjectById(id: number): Object3D | undefined;
    getObjectByName(name: string): Object3D | undefined;
    getObjectByProperty(name: string, value: any): Object3D | undefined;
    getWorldPosition(target: Vector3): Vector3;
    getWorldQuaternion(target: Quaternion): Quaternion;
    getWorldScale(target: Vector3): Vector3;
    getWorldDirection(target: Vector3): Vector3;
    raycast(raycaster: Raycaster, intersects: any[]): void;
    traverse(callback: (object: Object3D) => void): void;
    traverseVisible(callback: (object: Object3D) => void): void;
    traverseAncestors(callback: (object: Object3D) => void): void;
    updateMatrix(): void;
    updateMatrixWorld(force?: boolean): void;
    updateWorldMatrix(updateParents: boolean, updateChildren: boolean): void;
    toJSON(meta?: any): any;
    clone(recursive?: boolean): Object3D;
    copy(source: Object3D, recursive?: boolean): Object3D;
    getObjectsByProperty(name: string, value: any): Object3D[];
    attach(object: Object3D): Object3D;
  }

  export class Mesh extends Object3D {
    geometry: BufferGeometry;
    material: Material | Material[];
    morphTargetInfluences?: number[];
    morphTargetDictionary?: { [key: string]: number };
    isMesh: true;

    constructor(geometry?: BufferGeometry, material?: Material | Material[]);
    updateMorphTargets(): void;
    getVertexPosition(index: number, target: Vector3): Vector3;
  }

  export class Line extends Object3D {
    geometry: BufferGeometry;
    material: Material | Material[];
    isLine: true;

    constructor(geometry?: BufferGeometry, material?: Material | Material[]);
  }

  export class LineSegments extends Line {
    isLineSegments: true;
  }

  export class Points extends Object3D {
    geometry: BufferGeometry;
    material: Material | Material[];
    isPoints: true;

    constructor(geometry?: BufferGeometry, material?: Material | Material[]);
  }

  export class Scene extends Object3D {
    isScene: true;
    background: Color | any;
    fog: Fog | FogExp2 | null;
    overrideMaterial: Material | null;
    autoUpdate: boolean;
    children: Object3D[];

    constructor();
    copy(source: Scene, recursive?: boolean): Scene;
    toJSON(meta?: any): any;
    dispose(): void;
  }

  export class Fog {
    name: string;
    color: Color;
    near: number;
    far: number;

    constructor(color?: number | string, near?: number, far?: number);
    clone(): Fog;
    toJSON(): any;
  }

  export class FogExp2 {
    name: string;
    color: Color;
    density: number;

    constructor(color?: number | string, density?: number);
    clone(): FogExp2;
    toJSON(): any;
  }

  // Lights
  export class Light extends Object3D {
    color: Color;
    intensity: number;

    constructor(color?: number | string, intensity?: number);
    dispose(): void;
    copy(source: Light): Light;
    toJSON(meta?: any): any;
  }

  export class AmbientLight extends Light {
    isAmbientLight: true;

    constructor(color?: number | string, intensity?: number);
  }

  export class PointLight extends Light {
    distance: number;
    decay: number;
    shadow: LightShadow;

    constructor(color?: number | string, intensity?: number, distance?: number, decay?: number);
  }

  export class LightShadow {
    camera: Camera;
    bias: number;
    normalBias: number;
    radius: number;
    blurSamples: number;
    mapSize: Vector2;
    map: RenderTarget | null;
    mapAutoUpdate: boolean;
    autoUpdate: boolean;
    needsUpdate: boolean;
    dispose(): void;
    copy(source: LightShadow): LightShadow;
    clone(): LightShadow;
    toJSON(): any;
  }

  // Rendering
  export class WebGLRenderer {
    domElement: HTMLCanvasElement;
    canvas: HTMLCanvasElement;
    context: any;
    autoClear: boolean;
    autoClearColor: boolean;
    autoClearDepth: boolean;
    autoClearStencil: boolean;
    clearColor: Color;
    clearAlpha: number;
    sortObjects: boolean;
    clipping: any;
    localClippingEnabled: boolean;
    extensions: any;
    capabilities: any;
    properties: any;
    renderLists: any;
    state: any;
    shadowMap: any;
    pixelRatio: number;
    size: any;
    vr: any;
    xr: any;
    debug: any;

    constructor(parameters?: any);
    getContext(): any;
    getContextAttributes(): any;
    forceContextLoss(): void;
    forceContextRestore(): void;
    getPixelRatio(): number;
    setPixelRatio(value: number): void;
    getSize(target: Vector2): Vector2;
    setSize(width: number, height: number, updateStyle?: boolean): void;
    getDrawingBufferSize(target: Vector2): Vector2;
    setDrawingBufferSize(width: number, height: number, pixelRatio: number): void;
    getCurrentViewport(target: Vector4): Vector4;
    getViewport(target: Vector4): Vector4;
    setViewport(x: number | Vector4, y?: number, width?: number, height?: number): void;
    getScissor(target: Vector4): Vector4;
    setScissor(x: number | Vector4, y?: number, width?: number, height?: number): void;
    getScissorTest(): boolean;
    setScissorTest(enable: boolean): void;
    getClearColor(target: Color): Color;
    setClearColor(color: number | string | Color, alpha?: number): void;
    getClearAlpha(): number;
    setClearAlpha(alpha: number): void;
    clear(color?: boolean, depth?: boolean, stencil?: boolean): void;
    clearColor(): void;
    clearDepth(): void;
    clearStencil(): void;
    clearTarget(renderTarget: RenderTarget, color: boolean, depth: boolean, stencil: boolean): void;
    resetGLState(): void;
    render(scene: Object3D, camera: Camera): void;
    getRenderTarget(): RenderTarget | null;
    setRenderTarget(renderTarget: RenderTarget | null, activeCubeFace?: number, activeMipmapLevel?: number): void;
    getRenderObjectList(): any;
    resetState(): void;
    readRenderTargetPixels(
      renderTarget: RenderTarget,
      x: number,
      y: number,
      width: number,
      height: number,
      pixelBuffer: any,
      activeCubeFaceIndex?: number,
    ): void;
    copyFramebufferToTexture(position: Vector2, texture: any, level?: number): void;
    copyTextureToTexture(sourceTexture: any, targetTexture: any, level?: number): void;
    copyTextureToTexture3D(sourceTexture: any, targetTexture: any, sourceRegion?: any, targetPosition?: Vector3, level?: number): void;
    initRenderTarget(renderTarget: RenderTarget): void;
    initTexture(texture: any): void;
    resetRenderTarget(renderTarget: RenderTarget): void;
    setMsaa(msaa: number): void;
    getMsaa(): number;
    dispose(): void;
    setAnimationLoop(callback: (time: number) => void): void;
    compile(scene: Object3D, camera: Camera): void;
  }

  export class RenderTarget {
    width: number;
    height: number;
    depth: number;
    scissor: Vector4;
    scissorTest: boolean;
    viewport: Vector4;
    textures: any[];
    depthBuffer: boolean;
    stencilBuffer: boolean;
    depthTexture: any;
    samples: number;

    setSize(width: number, height: number, depth?: number): void;
    clone(): RenderTarget;
    copy(source: RenderTarget): RenderTarget;
    dispose(): void;
  }

  export class WebGLRenderTarget extends RenderTarget {
    isWebGLRenderTarget: true;

    constructor(width: number, height: number, options?: any);
  }

  // Raycasting
  export class Raycaster {
    ray: Ray;
    near: number;
    far: number;
    camera: Camera;
    layers: any;
    params: any;

    constructor(origin?: Vector3 | undefined, direction?: Vector3 | undefined, near?: number | undefined, far?: number | undefined);
    set(origin: Vector3, direction: Vector3): void;
    setFromCamera(coords: Vector2, camera: Camera): void;
    intersectObject(object: Object3D, recursive?: boolean): any[];
    intersectObjects(objects: Object3D[], recursive?: boolean): any[];
  }

  export class Ray {
    origin: Vector3;
    direction: Vector3;

    constructor(origin?: Vector3, direction?: Vector3);
    set(origin: Vector3, direction: Vector3): Ray;
    copy(ray: Ray): Ray;
    getPoint(t: number, target?: Vector3): Vector3;
    getPointAt(t: number, target?: Vector3): Vector3;
    lookAt(v: Vector3): Ray;
    recast(t: number): Ray;
    closestPointToPoint(point: Vector3, target?: Vector3): Vector3;
    distanceToPoint(point: Vector3): number;
    distanceSqToPoint(point: Vector3): number;
    distanceSqToSegment(v0: Vector3, v1: Vector3, optionalPointOnRay?: Vector3, optionalPointOnSegment?: Vector3): number;
    intersectSphere(sphere: any, target?: Vector3): Vector3 | null;
    intersectTriangle(a: Vector3, b: Vector3, c: Vector3, backfaceCulling: boolean, target?: Vector3): Vector3 | null;
  }

  // Vector 4
  export class Vector4 {
    x: number;
    y: number;
    z: number;
    w: number;

    constructor(x?: number, y?: number, z?: number, w?: number);
    copy(v: Vector4): Vector4;
    set(x: number, y: number, z: number, w: number): Vector4;
  }

  // Constants
  export const DoubleSide: number;
  export const FrontSide: number;
  export const BackSide: number;
  export const NeverBlending: number;
  export const NormalBlending: number;
  export const AdditiveBlending: number;
  export const SubtractiveBlending: number;
  export const MultiplyBlending: number;
  export const CustomBlending: number;
  export const AddEquation: number;
  export const SubtractEquation: number;
  export const ReverseSubtractEquation: number;
  export const MinEquation: number;
  export const MaxEquation: number;
  export const ZeroFactor: number;
  export const OneFactor: number;
  export const SrcColorFactor: number;
  export const OneMinusSrcColorFactor: number;
  export const SrcAlphaFactor: number;
  export const OneMinusSrcAlphaFactor: number;
  export const DstAlphaFactor: number;
  export const OneMinusDstAlphaFactor: number;
  export const DstColorFactor: number;
  export const OneMinusDstColorFactor: number;
  export const SrcAlphaSaturateFactor: number;
}
