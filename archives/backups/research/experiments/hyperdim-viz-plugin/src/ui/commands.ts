/**
 * Ribbon Commands - Main action buttons
 */

import { App, Editor, MarkdownView, Notice } from 'obsidian';
import { KyutaiPluginSettings } from '../types';
import { MCPClient } from '../services/mcp-client';
import { AudioInputModal, ResultDisplayModal, ErrorModal } from './modals';

export class RibbonCommandManager {
  constructor(
    private app: App,
    private mcpClient: MCPClient,
    private settings: KyutaiPluginSettings
  ) {}

  /**
   * Register all ribbon commands
   */
  registerCommands(plugin: any): void {
    // Read Note Aloud
    plugin.addRibbonIcon('volume-2', 'Read Note Aloud', () => {
      this.readNoteAloud();
    });

    // Transcribe Audio
    plugin.addRibbonIcon('mic', 'Transcribe Audio', () => {
      this.transcribeAudio();
    });

    // Clone Voice (only in enhanced tier)
    if (this.settings.defaultTier !== 'basic') {
      plugin.addRibbonIcon('user-voice', 'Clone Voice', () => {
        this.cloneVoice();
      });
    }

    // Model Status
    plugin.addRibbonIcon('activity', 'Model Status', () => {
      this.showModelStatus();
    });

    // Settings (auto-opens plugin settings)
    plugin.addRibbonIcon('settings', 'Kyutai Settings', () => {
      this.app.setting.open();
      this.app.setting.openTabById('kyutai-obsidian-plugin');
    });
  }

  /**
   * Command: Read Note Aloud
   */
  private async readNoteAloud(): Promise<void> {
    const editor = this.app.workspace.activeEditor?.editor;
    if (!editor) {
      new Notice('No active note. Please open a note first.', 3000);
      return;
    }

    // Extract markdown text (excluding code blocks and frontmatter)
    const text = this.extractNoteText(editor);
    if (!text) {
      new Notice('Note is empty or contains only code/frontmatter.', 3000);
      return;
    }

    // Validate text length
    if (text.length > 50000) {
      new Notice('Text too long (>50KB). Please select a shorter section.', 3000);
      return;
    }

    try {
      const voiceId = this.settings.tts.defaultVoice;
      const model = this.settings.tts.model;
      const speed = this.settings.tts.speed;

      new Notice('Generating audio...', 0);

      const result = await this.mcpClient.ttsGenerate(text, voiceId, model, speed);

      new Notice('Audio generated successfully!', 2000);

      // Open result modal
      const modal = new ResultDisplayModal(
        this.app,
        'audio',
        {
          audioPath: result.audio_path,
          duration: result.duration,
          voiceId,
          model,
        },
        (content) => {
          this.insertIntoNote(content);
        }
      );
      modal.open();
    } catch (error) {
      const errorModal = new ErrorModal(this.app, {
        title: 'TTS Generation Failed',
        message: String(error),
        severity: 'error',
        details: String(error),
        actions: [
          {
            label: 'Open Settings',
            callback: () => {
              this.app.setting.open();
            },
          },
        ],
      });
      errorModal.open();
    }
  }

  /**
   * Command: Transcribe Audio
   */
  private async transcribeAudio(): Promise<void> {
    const modal = new AudioInputModal(this.app, {
      onConfirm: async (audioPath) => {
        try {
          new Notice('Transcribing audio...', 0);

          const result = await this.mcpClient.sttTranscribe(
            audioPath,
            this.settings.stt.model,
            this.settings.stt.language
          );

          new Notice('Transcription complete!', 2000);

          const resultModal = new ResultDisplayModal(
            this.app,
            'text',
            {
              text: result.text,
              language: result.language,
              confidence: result.confidence,
              segments: result.segments,
            },
            (content) => {
              this.insertIntoNote(content);
            }
          );
          resultModal.open();
        } catch (error) {
          const errorModal = new ErrorModal(this.app, {
            title: 'Transcription Failed',
            message: String(error),
            severity: 'error',
            details: String(error),
          });
          errorModal.open();
        }
      },
      onCancel: () => {
        // User cancelled
      },
    });
    modal.open();
  }

  /**
   * Command: Clone Voice (Enhanced tier only)
   */
  private async cloneVoice(): Promise<void> {
    const modal = new AudioInputModal(this.app, {
      onConfirm: async (audioPath) => {
        try {
          // Generate a unique voice ID
          const voiceId = `voice_${Date.now()}`;
          const voiceName = `Cloned Voice #${this.settings.voices.length + 1}`;

          // Register voice in settings
          this.settings.voices.push({
            id: voiceId,
            name: voiceName,
            type: 'cloned',
            referencePath: audioPath,
            createdAt: Date.now(),
          });

          new Notice(`Voice "${voiceName}" cloned successfully!`, 3000);
        } catch (error) {
          const errorModal = new ErrorModal(this.app, {
            title: 'Voice Cloning Failed',
            message: String(error),
            severity: 'error',
            details: String(error),
          });
          errorModal.open();
        }
      },
      onCancel: () => {
        // User cancelled
      },
    });
    modal.open();
  }

  /**
   * Command: Show Model Status
   */
  private async showModelStatus(): Promise<void> {
    try {
      new Notice('Fetching model status...', 0);

      const status = await this.mcpClient.modelStatus();

      const modal = new (class {
        constructor(private app: App, private status: any) {}
        open() {
          const { contentEl } = this;
          contentEl.empty();
          contentEl.addClass('kyutai-status-modal');

          const titleEl = contentEl.createEl('h2', { text: 'Model Status' });
          titleEl.addClass('modal-title');

          const statusDiv = contentEl.createDiv({ cls: 'status-content' });
          statusDiv.createEl('p', { text: `GPU Available: ${this.status.gpu_available ? '✓ Yes' : '✗ No'}` });
          statusDiv.createEl('p', { text: `VRAM Usage: ${this.status.vram_usage_gb.toFixed(2)} GB` });

          statusDiv.createEl('h3', { text: 'Models' });
          const modelsList = statusDiv.createEl('ul');
          this.status.models.forEach((model: any) => {
            modelsList.createEl('li', {
              text: `${model.name} (${model.status}) - ${model.vram_used_mb}MB`,
            });
          });

          const closeBtn = contentEl.createEl('button', { text: 'Close' });
          closeBtn.addEventListener('click', () => {
            // Close modal
          });
        }
      })(this.app, status);
      // Note: This is a simplified modal - in production use proper Modal class
    } catch (error) {
      const errorModal = new ErrorModal(this.app, {
        title: 'Status Check Failed',
        message: String(error),
        severity: 'warning',
        details: String(error),
      });
      errorModal.open();
    }
  }

  /**
   * Extract plain text from note (exclude code blocks, frontmatter)
   */
  private extractNoteText(editor: Editor): string {
    const content = editor.getValue();
    let text = content;

    // Remove YAML frontmatter
    if (text.startsWith('---')) {
      const secondDelimiter = text.indexOf('---', 3);
      if (secondDelimiter !== -1) {
        text = text.substring(secondDelimiter + 3);
      }
    }

    // Remove code blocks
    text = text.replace(/```[\s\S]*?```/g, '');

    // Remove inline code
    text = text.replace(/`[^`]*`/g, '');

    // Remove markdown formatting
    text = text.replace(/[#*_\[\]()]/g, ' ');

    // Remove extra whitespace
    text = text.replace(/\s+/g, ' ').trim();

    return text;
  }

  /**
   * Insert content into note at cursor
   */
  private insertIntoNote(content: string): void {
    const editor = this.app.workspace.activeEditor?.editor;
    if (!editor) {
      new Notice('No active note to insert into.', 3000);
      return;
    }

    editor.replaceSelection(content);
    new Notice('Content inserted into note!', 2000);
  }
}
