/**
 * Simple Camera Controller for 3D Graph
 * Provides orbit, zoom, and pan controls without external dependencies
 */

import * as THREE from 'three';

export class CameraController {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  
  private isMouseDown = false;
  private mouseButton = 0;
  private previousMousePosition = { x: 0, y: 0 };
  
  private spherical = new THREE.Spherical(100, Math.PI / 4, 0);
  private target = new THREE.Vector3(0, 0, 0);
  
  // Damping
  enableDamping = true;
  dampingFactor = 0.05;
  
  // Zoom
  minDistance = 10;
  maxDistance = 500;
  
  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;
    
    this.bindEvents();
    this.update();
  }
  
  private bindEvents() {
    this.domElement.addEventListener('mousedown', this.onMouseDown.bind(this));
    this.domElement.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.domElement.addEventListener('mouseup', this.onMouseUp.bind(this));
    this.domElement.addEventListener('wheel', this.onWheel.bind(this));
    this.domElement.addEventListener('contextmenu', (e) => e.preventDefault());
  }
  
  private onMouseDown(event: MouseEvent) {
    this.isMouseDown = true;
    this.mouseButton = event.button;
    this.previousMousePosition = {
      x: event.clientX,
      y: event.clientY,
    };
  }
  
  private onMouseMove(event: MouseEvent) {
    if (!this.isMouseDown) return;
    
    const deltaX = event.clientX - this.previousMousePosition.x;
    const deltaY = event.clientY - this.previousMousePosition.y;
    
    if (this.mouseButton === 0) {
      // Left click - orbit
      this.spherical.theta -= deltaX * 0.01;
      this.spherical.phi -= deltaY * 0.01;
      
      // Clamp phi to prevent gimbal lock
      this.spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.spherical.phi));
    } else if (this.mouseButton === 2) {
      // Right click - pan
      const panSpeed = 0.1;
      const right = new THREE.Vector3();
      const up = new THREE.Vector3(0, 1, 0);
      
      this.camera.getWorldDirection(right);
      right.cross(up).normalize();
      
      this.target.addScaledVector(right, -deltaX * panSpeed);
      this.target.addScaledVector(up, deltaY * panSpeed);
    }
    
    this.previousMousePosition = {
      x: event.clientX,
      y: event.clientY,
    };
  }
  
  private onMouseUp() {
    this.isMouseDown = false;
  }
  
  private onWheel(event: WheelEvent) {
    event.preventDefault();
    
    const zoomSpeed = 0.1;
    this.spherical.radius += event.deltaY * zoomSpeed;
    this.spherical.radius = Math.max(this.minDistance, Math.min(this.maxDistance, this.spherical.radius));
  }
  
  update() {
    // Convert spherical to cartesian
    const offset = new THREE.Vector3();
    offset.setFromSpherical(this.spherical);
    
    // Apply to camera
    this.camera.position.copy(this.target).add(offset);
    this.camera.lookAt(this.target);
  }
  
  dispose() {
    this.domElement.removeEventListener('mousedown', this.onMouseDown.bind(this));
    this.domElement.removeEventListener('mousemove', this.onMouseMove.bind(this));
    this.domElement.removeEventListener('mouseup', this.onMouseUp.bind(this));
    this.domElement.removeEventListener('wheel', this.onWheel.bind(this));
  }
}
