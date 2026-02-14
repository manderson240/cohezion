/**
 * KeyboardControls - Handle keyboard input for camera and UI interactions
 */
export class KeyboardControls {
  private keysPressed: Map<string, boolean> = new Map();

  private onArrowKey: ((direction: 'up' | 'down' | 'left' | 'right') => void) | null = null;
  private onZoom: ((direction: 'in' | 'out') => void) | null = null;
  private onReset: (() => void) | null = null;
  private onEscape: (() => void) | null = null;
  private onHelp: (() => void) | null = null;

  constructor() {
    this.setupListeners();
  }

  /**
   * Setup keyboard event listeners
   */
  private setupListeners(): void {
    document.addEventListener('keydown', (e) => {
      this.keysPressed.set(e.key, true);

      // Arrow keys for camera rotation
      if (e.key === 'ArrowUp') {
        this.onArrowKey?.('up');
        e.preventDefault();
      } else if (e.key === 'ArrowDown') {
        this.onArrowKey?.('down');
        e.preventDefault();
      } else if (e.key === 'ArrowLeft') {
        this.onArrowKey?.('left');
        e.preventDefault();
      } else if (e.key === 'ArrowRight') {
        this.onArrowKey?.('right');
        e.preventDefault();
      }

      // +/- for zoom
      if (e.key === '+' || e.key === '=') {
        this.onZoom?.('in');
        e.preventDefault();
      } else if (e.key === '-') {
        this.onZoom?.('out');
        e.preventDefault();
      }

      // Space for reset
      if (e.key === ' ') {
        this.onReset?.();
        e.preventDefault();
      }

      // Escape to close panels
      if (e.key === 'Escape') {
        this.onEscape?.();
      }

      // ? or H for help
      if (e.key === '?' || e.key.toLowerCase() === 'h') {
        this.onHelp?.();
        e.preventDefault();
      }
    });

    document.addEventListener('keyup', (e) => {
      this.keysPressed.set(e.key, false);
    });
  }

  /**
   * Register arrow key callback
   */
  onArrowKeyPressed(callback: (direction: 'up' | 'down' | 'left' | 'right') => void): void {
    this.onArrowKey = callback;
  }

  /**
   * Register zoom callback
   */
  onZoomPressed(callback: (direction: 'in' | 'out') => void): void {
    this.onZoom = callback;
  }

  /**
   * Register reset callback
   */
  onResetPressed(callback: () => void): void {
    this.onReset = callback;
  }

  /**
   * Register escape callback
   */
  onEscapePressed(callback: () => void): void {
    this.onEscape = callback;
  }

  /**
   * Register help callback
   */
  onHelpPressed(callback: () => void): void {
    this.onHelp = callback;
  }

  /**
   * Check if a key is currently pressed
   */
  isKeyPressed(key: string): boolean {
    return this.keysPressed.get(key) || false;
  }

  /**
   * Destroy keyboard controls
   */
  destroy(): void {
    this.keysPressed.clear();
  }
}
