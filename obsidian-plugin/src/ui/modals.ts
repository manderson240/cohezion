/**
 * Modal Windows and Dialogs
 */

import { Modal, App, Notice, ConfirmationModal } from 'obsidian';
import { AudioInputModalProps, AudioResult, TextResult, ErrorModalProps } from '../types';
import { AudioRecorder, AudioPlayer, AudioFileHandler } from '../services/audio-processor';

/**
 * Audio Input Modal - Choose between file upload or recording
 */
export class AudioInputModal extends Modal {
  private onConfirm: (audioPath: string) => void;
  private onCancel: () => void;
  private inputMethod: 'file' | 'record' = 'file';
  private selectedFile: File | null = null;
  private recordingBlob: Blob | null = null;
  private recorder: AudioRecorder | null = null;
  private isRecording: boolean = false;

  constructor(app: App, props: AudioInputModalProps) {
    super(app);
    this.onConfirm = props.onConfirm;
    this.onCancel = props.onCancel;
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('kyutai-audio-input-modal');

    const titleEl = contentEl.createEl('h2', { text: 'Audio Input' });
    titleEl.addClass('modal-title');

    // Input method selector
    const methodContainer = contentEl.createDiv({ cls: 'input-method-selector' });
    methodContainer.createEl('label', { text: 'Choose Input Method:' });

    const fileLabel = methodContainer.createEl('label', { cls: 'radio-option' });
    const fileRadio = fileLabel.createEl('input', {
      attr: { type: 'radio', name: 'input-method', value: 'file' },
    }) as HTMLInputElement;
    fileRadio.checked = true;
    fileLabel.createEl('span', { text: 'Upload File' });
    fileRadio.addEventListener('change', () => {
      this.inputMethod = 'file';
      this.renderContent();
    });

    const recordLabel = methodContainer.createEl('label', { cls: 'radio-option' });
    const recordRadio = recordLabel.createEl('input', {
      attr: { type: 'radio', name: 'input-method', value: 'record' },
    }) as HTMLInputElement;
    recordLabel.createEl('span', { text: 'Record from Microphone' });
    recordRadio.addEventListener('change', () => {
      this.inputMethod = 'record';
      this.renderContent();
    });

    this.renderContent();
  }

  private renderContent() {
    const { contentEl } = this;
    const contentDiv = contentEl.querySelector('.modal-content') || contentEl.createDiv({ cls: 'modal-content' });
    contentDiv.empty();

    if (this.inputMethod === 'file') {
      this.renderFileUpload(contentDiv);
    } else {
      this.renderRecording(contentDiv);
    }
  }

  private renderFileUpload(container: HTMLElement) {
    const fileInputSection = container.createDiv({ cls: 'file-input-section' });

    const fileInput = fileInputSection.createEl('input', {
      attr: { type: 'file', accept: AudioFileHandler.SUPPORTED_FORMATS.map(f => `.${f}`).join(',') },
    }) as HTMLInputElement;

    const fileInfo = fileInputSection.createEl('div', { cls: 'file-info' });

    fileInput.addEventListener('change', async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const validation = await AudioFileHandler.validateFile(file);
      if (!validation.valid) {
        new Notice(`Error: ${validation.error}`, 5000);
        return;
      }

      this.selectedFile = file;
      fileInfo.setText(
        `${file.name} (${AudioFileHandler.formatFileSize(file.size)})`
      );
    });

    fileInputSection.createEl('p', {
      text: `Supported: ${AudioFileHandler.SUPPORTED_FORMATS.join(', ').toUpperCase()}`,
      cls: 'supported-formats',
    });

    this.renderButtonGroup(container);
  }

  private renderRecording(container: HTMLElement) {
    const recordingSection = container.createDiv({ cls: 'recording-section' });

    const timerEl = recordingSection.createEl('div', { cls: 'timer', text: '0:00' });
    const controlsDiv = recordingSection.createDiv({ cls: 'recording-controls' });

    const recordBtn = controlsDiv.createEl('button', { text: '● Record' });
    const stopBtn = controlsDiv.createEl('button', { text: '■ Stop', cls: 'hidden' });

    let timerInterval: NodeJS.Timeout | null = null;

    recordBtn.addEventListener('click', async () => {
      this.recorder = new AudioRecorder();
      try {
        await this.recorder.startRecording();
        this.isRecording = true;
        recordBtn.addClass('hidden');
        stopBtn.removeClass('hidden');

        // Update timer
        timerInterval = setInterval(() => {
          const duration = this.recorder?.getRecordingDuration() || 0;
          timerEl.setText(AudioFileHandler.formatDuration(duration / 1000));
        }, 100);
      } catch (error) {
        new Notice(`Recording failed: ${error}`, 5000);
      }
    });

    stopBtn.addEventListener('click', async () => {
      if (timerInterval) clearInterval(timerInterval);
      try {
        this.recordingBlob = await this.recorder!.stopRecording();
        this.isRecording = false;
        recordBtn.removeClass('hidden');
        stopBtn.addClass('hidden');
        new Notice('Recording saved. Click Continue to proceed.', 3000);
      } catch (error) {
        new Notice(`Stop recording failed: ${error}`, 5000);
      }
    });

    this.renderButtonGroup(container);
  }

  private renderButtonGroup(container: HTMLElement) {
    const buttonGroup = container.createDiv({ cls: 'button-group' });
    buttonGroup.style.display = 'flex';
    buttonGroup.style.gap = '10px';
    buttonGroup.style.justifyContent = 'flex-end';
    buttonGroup.style.marginTop = '20px';

    const cancelBtn = buttonGroup.createEl('button', { text: 'Cancel' });
    const continueBtn = buttonGroup.createEl('button', { text: 'Continue' });
    continueBtn.addClass('mod-cta');

    cancelBtn.addEventListener('click', () => {
      if (this.recorder?.isRecording()) {
        this.recorder.stopRecording();
      }
      this.onCancel();
      this.close();
    });

    continueBtn.addEventListener('click', async () => {
      if (this.inputMethod === 'file' && this.selectedFile) {
        // For now, pass base64 encoded file
        const base64 = await AudioFileHandler.fileToBase64(this.selectedFile);
        this.onConfirm(base64);
        this.close();
      } else if (this.inputMethod === 'record' && this.recordingBlob) {
        const base64 = await AudioFileHandler.blobToBase64(this.recordingBlob);
        this.onConfirm(base64);
        this.close();
      } else {
        new Notice('Please select a file or record audio first', 3000);
      }
    });
  }
}

/**
 * Result Display Modal - Show TTS/STT results
 */
export class ResultDisplayModal extends Modal {
  private resultType: 'audio' | 'text' | 'bilingual';
  private content: AudioResult | TextResult;
  private onInsert: (content: string) => void;
  private audioPlayer: AudioPlayer | null = null;
  private isEditMode: boolean = false;
  private editedText: string = '';

  constructor(
    app: App,
    resultType: 'audio' | 'text' | 'bilingual',
    content: AudioResult | TextResult,
    onInsert: (content: string) => void
  ) {
    super(app);
    this.resultType = resultType;
    this.content = content;
    this.onInsert = onInsert;
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('kyutai-result-modal');

    if (this.resultType === 'audio') {
      this.renderAudioResult(contentEl, this.content as AudioResult);
    } else if (this.resultType === 'text') {
      this.renderTextResult(contentEl, this.content as TextResult);
    }
  }

  private renderAudioResult(container: HTMLElement, content: AudioResult) {
    const titleEl = container.createEl('h2', { text: 'Audio Result' });
    titleEl.addClass('modal-title');

    const infoDiv = container.createDiv({ cls: 'result-info' });
    infoDiv.createEl('p', {
      text: `Duration: ${AudioFileHandler.formatDuration(content.duration)}`,
    });

    // Audio player
    const playerDiv = container.createDiv({ cls: 'audio-player' });
    this.audioPlayer = new AudioPlayer(content.audioPath);
    const audioEl = this.audioPlayer.getElement();

    if (audioEl) {
      audioEl.setAttribute('aria-label', 'Audio playback');
      playerDiv.appendChild(audioEl);

      const controlsDiv = playerDiv.createDiv({ cls: 'player-controls' });
      controlsDiv.style.display = 'flex';
      controlsDiv.style.gap = '10px';
      controlsDiv.style.marginTop = '10px';
      controlsDiv.style.alignItems = 'center';

      const playBtn = controlsDiv.createEl('button', { text: '▶ Play' });
      playBtn.addEventListener('click', () => this.audioPlayer?.play());

      const pauseBtn = controlsDiv.createEl('button', { text: '⏸ Pause' });
      pauseBtn.addEventListener('click', () => this.audioPlayer?.pause());

      const progressDiv = controlsDiv.createDiv({ cls: 'progress', style: 'flex: 1;' });
      const progressBar = progressDiv.createEl('input', {
        attr: {
          type: 'range',
          min: '0',
          max: '100',
          value: '0',
          'aria-label': 'Audio progress',
        },
      }) as HTMLInputElement;
      progressBar.style.width = '100%';

      const timeDisplay = controlsDiv.createEl('span', { text: '0:00 / 0:00' });
      timeDisplay.style.minWidth = '80px';

      // Update progress
      audioEl.addEventListener('timeupdate', () => {
        const progress = this.audioPlayer?.getProgress() || 0;
        progressBar.value = String(progress);
        const current = this.audioPlayer?.getCurrentTime() || 0;
        const duration = this.audioPlayer?.getDuration() || 0;
        timeDisplay.setText(
          `${AudioFileHandler.formatDuration(current)} / ${AudioFileHandler.formatDuration(duration)}`
        );
      });

      progressBar.addEventListener('input', (e) => {
        const value = parseFloat((e.target as HTMLInputElement).value);
        const duration = this.audioPlayer?.getDuration() || 0;
        this.audioPlayer?.seek((value / 100) * duration);
      });
    }

    this.renderResultButtonGroup(container, content.audioPath);
  }

  private renderTextResult(container: HTMLElement, content: TextResult) {
    const titleEl = container.createEl('h2', { text: 'Transcription Result' });
    titleEl.addClass('modal-title');

    const infoDiv = container.createDiv({ cls: 'result-info' });
    infoDiv.createEl('p', {
      text: `Confidence: ${(content.confidence * 100).toFixed(1)}%`,
    });

    const textDiv = container.createDiv({ cls: 'transcript-display' });

    if (this.isEditMode) {
      const textarea = textDiv.createEl('textarea', {
        attr: { 'aria-label': 'Edit transcript' },
      }) as HTMLTextAreaElement;
      textarea.value = this.editedText;
      textarea.style.width = '100%';
      textarea.style.minHeight = '200px';
      textarea.style.padding = '10px';
      textarea.style.fontFamily = 'monospace';

      textarea.addEventListener('change', (e) => {
        this.editedText = (e.target as HTMLTextAreaElement).value;
      });
    } else {
      const displayEl = textDiv.createEl('div', { text: content.text });
      displayEl.style.padding = '10px';
      displayEl.style.backgroundColor = 'var(--background-secondary)';
      displayEl.style.borderRadius = '4px';
      displayEl.style.minHeight = '100px';
      displayEl.style.whiteSpace = 'pre-wrap';
      displayEl.style.wordWrap = 'break-word';
    }

    this.renderTextButtonGroup(container);
  }

  private renderResultButtonGroup(container: HTMLElement, filePath: string) {
    const buttonGroup = container.createDiv({ cls: 'button-group' });
    buttonGroup.style.display = 'flex';
    buttonGroup.style.gap = '10px';
    buttonGroup.style.justifyContent = 'flex-end';
    buttonGroup.style.marginTop = '20px';

    const downloadBtn = buttonGroup.createEl('button', { text: '⬇ Download' });
    downloadBtn.addEventListener('click', () => {
      // Trigger download (implementation depends on Obsidian API)
      new Notice('Download not yet implemented', 3000);
    });

    const insertBtn = buttonGroup.createEl('button', { text: '📝 Insert' });
    insertBtn.addClass('mod-cta');
    insertBtn.addEventListener('click', () => {
      this.onInsert(filePath);
      this.close();
    });

    const closeBtn = buttonGroup.createEl('button', { text: 'Close' });
    closeBtn.addEventListener('click', () => this.close());
  }

  private renderTextButtonGroup(container: HTMLElement) {
    const buttonGroup = container.createDiv({ cls: 'button-group' });
    buttonGroup.style.display = 'flex';
    buttonGroup.style.gap = '10px';
    buttonGroup.style.justifyContent = 'flex-end';
    buttonGroup.style.marginTop = '20px';

    const copyBtn = buttonGroup.createEl('button', { text: '📋 Copy' });
    copyBtn.addEventListener('click', () => {
      const textToCopy = this.isEditMode ? this.editedText : (this.content as TextResult).text;
      navigator.clipboard.writeText(textToCopy);
      new Notice('Copied to clipboard', 2000);
    });

    const editBtn = buttonGroup.createEl('button', {
      text: this.isEditMode ? '✓ Done Editing' : '✏ Edit',
    });
    editBtn.addEventListener('click', () => {
      this.isEditMode = !this.isEditMode;
      if (this.isEditMode) {
        this.editedText = (this.content as TextResult).text;
      }
      this.onOpen();
    });

    const insertBtn = buttonGroup.createEl('button', { text: '📝 Insert' });
    insertBtn.addClass('mod-cta');
    insertBtn.addEventListener('click', () => {
      const textContent = this.isEditMode ? this.editedText : (this.content as TextResult).text;
      const formatted = `\`\`\`\n[Transcription: ${new Date().toISOString()}]\n${textContent}\n\`\`\``;
      this.onInsert(formatted);
      this.close();
    });

    const closeBtn = buttonGroup.createEl('button', { text: 'Close' });
    closeBtn.addEventListener('click', () => this.close());
  }

  onClose() {
    if (this.audioPlayer) {
      this.audioPlayer.destroy();
    }
  }
}

/**
 * Error Modal - Display errors with helpful information
 */
export class ErrorModal extends Modal {
  private title: string;
  private message: string;
  private severity: 'info' | 'warning' | 'error' | 'fatal';
  private details?: string;
  private actions: Array<{ label: string; callback: () => void }>;

  constructor(app: App, props: ErrorModalProps) {
    super(app);
    this.title = props.title;
    this.message = props.message;
    this.severity = props.severity;
    this.details = props.details;
    this.actions = props.actions || [];
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('kyutai-error-modal');

    const titleEl = contentEl.createEl('h2', { text: this.title });
    titleEl.addClass('modal-title');

    const icon = this.getIconForSeverity(this.severity);
    const messageEl = contentEl.createEl('p', { text: `${icon} ${this.message}` });
    messageEl.style.marginTop = '15px';
    messageEl.style.marginBottom = '15px';

    if (this.details) {
      const detailsDiv = contentEl.createDiv({ cls: 'error-details' });
      detailsDiv.createEl('p', { text: 'Error Details:' });
      const code = detailsDiv.createEl('code', { text: this.details });
      code.style.display = 'block';
      code.style.padding = '10px';
      code.style.backgroundColor = 'var(--background-secondary)';
      code.style.borderRadius = '4px';
      code.style.overflow = 'auto';
    }

    const buttonGroup = contentEl.createDiv({ cls: 'button-group' });
    buttonGroup.style.display = 'flex';
    buttonGroup.style.gap = '10px';
    buttonGroup.style.justifyContent = 'flex-end';
    buttonGroup.style.marginTop = '20px';

    // Custom action buttons
    this.actions.forEach(action => {
      const btn = buttonGroup.createEl('button', { text: action.label });
      btn.addEventListener('click', () => {
        action.callback();
        this.close();
      });
    });

    // Close button
    const closeBtn = buttonGroup.createEl('button', { text: 'OK' });
    closeBtn.addClass('mod-cta');
    closeBtn.addEventListener('click', () => this.close());
  }

  private getIconForSeverity(severity: string): string {
    return {
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌',
      fatal: '🔴',
    }[severity] || '❌';
  }
}
