export class Scene {
  add = jest.fn();
  remove = jest.fn();
  children: any[] = [];
}

export class PerspectiveCamera {
  position = new Vector3();
  lookAt = jest.fn();
  updateProjectionMatrix = jest.fn();
}

export class WebGLRenderer {
  domElement = document.createElement('canvas');
  setSize = jest.fn();
  render = jest.fn();
  dispose = jest.fn();
  setPixelRatio = jest.fn();
}

export class Vector3 {
  x = 0; y = 0; z = 0;
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set = jest.fn(() => this);
  copy = jest.fn(() => this);
  add = jest.fn(() => this);
  sub = jest.fn(() => this);
  multiplyScalar = jest.fn(() => this);
  normalize = jest.fn(() => this);
  length = jest.fn(() => 0);
  distanceTo = jest.fn(() => 0);
  clone = jest.fn(() => new Vector3());
}

export class Color {
  constructor(_color?: string | number) {}
  set = jest.fn(() => this);
}

export class SphereGeometry {}
export class BoxGeometry {}
export class BufferGeometry {
  setAttribute = jest.fn();
  setFromPoints = jest.fn();
}

export class MeshBasicMaterial {}
export class MeshStandardMaterial {}
export class LineBasicMaterial {}
export class ShaderMaterial {}
export class SpriteMaterial {}

export class Mesh {
  position = new Vector3();
  material: any;
  geometry: any;
  userData: any = {};
  constructor(geometry?: any, material?: any) {
    this.geometry = geometry;
    this.material = material;
  }
}

export class Line {
  position = new Vector3();
  geometry: any;
  material: any;
}

export class Sprite {
  position = new Vector3();
  scale = new Vector3();
  material: any;
}

export class Group {
  add = jest.fn();
  remove = jest.fn();
  children: any[] = [];
  position = new Vector3();
}

export class Raycaster {
  setFromCamera = jest.fn();
  intersectObjects = jest.fn(() => []);
}

export class Vector2 {
  x = 0; y = 0;
  constructor(x = 0, y = 0) { this.x = x; this.y = y; }
}

export class AmbientLight {}
export class DirectionalLight {
  position = new Vector3();
}
export class PointLight {
  position = new Vector3();
}

export class CanvasTexture {}
export class TextureLoader {
  load = jest.fn();
}

export class BufferAttribute {
  constructor(_array: any, _itemSize: number) {}
}

export class Float32BufferAttribute extends BufferAttribute {}
