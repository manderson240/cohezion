/**
 * Audio Processor - Recording, playback, and file handling
 */

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private startTime: number = 0;

  async startRecording(): Promise<void> {
    try {
      this.chunks = [];
      this.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.audioStream);
      this.startTime = Date.now();

      this.mediaRecorder.ondataavailable = (event) => {
        this.chunks.push(event.data);
      };

      this.mediaRecorder.start();
    } catch (error) {
      console.error('[AudioRecorder] Failed to start recording:', error);
      throw new Error('Microphone access denied. Please check browser permissions.');
    }
  }

  stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('Recording not started'));
        return;
      }

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: 'audio/wav' });
        this.stopAudioStream();
        resolve(blob);
      };

      this.mediaRecorder.onerror = (event) => {
        this.stopAudioStream();
        reject(new Error(`Recording error: ${event.error}`));
      };

      this.mediaRecorder.stop();
    });
  }

  private stopAudioStream(): void {
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
  }

  isRecording(): boolean {
    return this.mediaRecorder?.state === 'recording';
  }

  getRecordingDuration(): number {
    return this.startTime > 0 ? Date.now() - this.startTime : 0;
  }
}

export class AudioPlayer {
  private audioElement: HTMLAudioElement | null = null;
  private currentTime: number = 0;
  private duration: number = 0;
  private isPlaying: boolean = false;

  constructor(audioPath: string) {
    this.audioElement = new Audio(audioPath);
    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    if (!this.audioElement) return;

    this.audioElement.addEventListener('timeupdate', () => {
      this.currentTime = this.audioElement?.currentTime || 0;
    });

    this.audioElement.addEventListener('loadedmetadata', () => {
      this.duration = this.audioElement?.duration || 0;
    });

    this.audioElement.addEventListener('play', () => {
      this.isPlaying = true;
    });

    this.audioElement.addEventListener('pause', () => {
      this.isPlaying = false;
    });

    this.audioElement.addEventListener('ended', () => {
      this.isPlaying = false;
    });
  }

  play(): Promise<void> {
    if (!this.audioElement) {
      return Promise.reject(new Error('Audio element not initialized'));
    }
    return this.audioElement.play();
  }

  pause(): void {
    if (this.audioElement) {
      this.audioElement.pause();
    }
  }

  stop(): void {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    }
  }

  seek(time: number): void {
    if (this.audioElement) {
      this.audioElement.currentTime = time;
    }
  }

  setVolume(volume: number): void {
    if (this.audioElement) {
      this.audioElement.volume = Math.max(0, Math.min(1, volume));
    }
  }

  setPlaybackRate(rate: number): void {
    if (this.audioElement) {
      this.audioElement.playbackRate = rate;
    }
  }

  getCurrentTime(): number {
    return this.currentTime;
  }

  getDuration(): number {
    return this.duration;
  }

  getProgress(): number {
    return this.duration > 0 ? (this.currentTime / this.duration) * 100 : 0;
  }

  isPlayingNow(): boolean {
    return this.isPlaying;
  }

  getElement(): HTMLAudioElement | null {
    return this.audioElement;
  }

  destroy(): void {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.src = '';
      this.audioElement = null;
    }
  }
}

export class AudioFileHandler {
  static readonly SUPPORTED_FORMATS = ['mp3', 'wav', 'flac', 'ogg', 'm4a'];
  static readonly MAX_FILE_SIZE_MB = 500;

  static async validateFile(file: File): Promise<{ valid: boolean; error?: string }> {
    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > this.MAX_FILE_SIZE_MB) {
      return {
        valid: false,
        error: `File too large (${fileSizeMB.toFixed(1)}MB). Maximum is ${this.MAX_FILE_SIZE_MB}MB.`,
      };
    }

    // Check file type
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !this.SUPPORTED_FORMATS.includes(extension)) {
      return {
        valid: false,
        error: `Unsupported format: .${extension}. Supported: ${this.SUPPORTED_FORMATS.join(', ')}`,
      };
    }

    return { valid: true };
  }

  static async blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        resolve(result.split(',')[1]); // Remove data:audio/... prefix
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  static async fileToBase64(file: File): Promise<string> {
    return this.blobToBase64(file);
  }

  static formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }

  static formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }
}
