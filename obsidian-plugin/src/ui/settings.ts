/**
 * Settings Tab - Plugin configuration UI
 */

import { App, PluginSettingTab, Setting, Notice } from 'obsidian';
import KyutaiPlugin from '../main';
import { KyutaiPluginSettings } from '../types';

export class KyutaiSettingsTab extends PluginSettingTab {
  plugin: KyutaiPlugin;

  constructor(app: App, plugin: KyutaiPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Kyutai Plugin Settings' });

    // ===== GENERAL SETTINGS =====
    this.createCollapsibleSection(containerEl, 'General', () => {
      new Setting(containerEl)
        .setName('Enable Kyutai Plugin')
        .setDesc('Turn the plugin on/off')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.enabled)
            .onChange(async (value) => {
              this.plugin.settings.enabled = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Feature Tier')
        .setDesc('Controls which features are available: Basic (TTS/STT), Enhanced (+ Voice cloning), Advanced (+ Full conversation)')
        .addDropdown((dropdown) =>
          dropdown
            .addOption('basic', 'Basic (TTS, STT)')
            .addOption('enhanced', 'Enhanced (+ Voice cloning, translation)')
            .addOption('advanced', 'Advanced (+ Full conversation)')
            .setValue(this.plugin.settings.defaultTier)
            .onChange(async (value) => {
              this.plugin.settings.defaultTier = value as any;
              await this.plugin.saveSettings();
              this.display(); // Refresh to show/hide features
            })
        );

      new Setting(containerEl)
        .setName('Default Language')
        .setDesc('Language for speech recognition and synthesis')
        .addDropdown((dropdown) =>
          dropdown
            .addOption('en', 'English')
            .addOption('fr', 'French')
            .setValue(this.plugin.settings.language)
            .onChange(async (value) => {
              this.plugin.settings.language = value;
              await this.plugin.saveSettings();
            })
        );
    });

    // ===== TTS SETTINGS =====
    this.createCollapsibleSection(containerEl, 'Text-to-Speech', () => {
      new Setting(containerEl)
        .setName('TTS Model')
        .setDesc('Choose TTS model: Pocket TTS (CPU) or TTS 1.6B (GPU)')
        .addDropdown((dropdown) =>
          dropdown
            .addOption('pocket-tts', 'Pocket TTS (CPU, recommended)')
            .addOption('tts-1.6b-en_fr', 'TTS 1.6B (GPU, higher quality)')
            .setValue(this.plugin.settings.tts.model)
            .onChange(async (value) => {
              this.plugin.settings.tts.model = value as any;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Default Voice')
        .setDesc('Voice to use when reading notes')
        .addDropdown((dropdown) => {
          dropdown.addOption('default', 'Default (English, Neutral)');
          this.plugin.settings.voices.forEach((voice) => {
            dropdown.addOption(voice.id, voice.name);
          });
          dropdown
            .setValue(this.plugin.settings.tts.defaultVoice)
            .onChange(async (value) => {
              this.plugin.settings.tts.defaultVoice = value;
              await this.plugin.saveSettings();
            });
        });

      new Setting(containerEl)
        .setName('Speech Speed')
        .setDesc('0.5x (slow) to 2.0x (fast), default 1.0x')
        .addSlider((slider) =>
          slider
            .setLimits(0.5, 2.0, 0.1)
            .setValue(this.plugin.settings.tts.speed)
            .setDynamicTooltip()
            .onChange(async (value) => {
              this.plugin.settings.tts.speed = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Speech Pitch')
        .setDesc('80-120%, default 100%')
        .addSlider((slider) =>
          slider
            .setLimits(80, 120, 1)
            .setValue(this.plugin.settings.tts.pitch)
            .setDynamicTooltip()
            .onChange(async (value) => {
              this.plugin.settings.tts.pitch = value;
              await this.plugin.saveSettings();
            })
        );
    });

    // ===== STT SETTINGS =====
    this.createCollapsibleSection(containerEl, 'Speech-to-Text', () => {
      new Setting(containerEl)
        .setName('STT Model')
        .setDesc('Choose STT model')
        .addDropdown((dropdown) =>
          dropdown
            .addOption('stt-1b-en_fr', 'STT 1B (CPU, bilingual)')
            .addOption('stt-2.6b-en', 'STT 2.6B (GPU, English only, higher quality)')
            .setValue(this.plugin.settings.stt.model)
            .onChange(async (value) => {
              this.plugin.settings.stt.model = value as any;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Language')
        .setDesc('Language for transcription')
        .addDropdown((dropdown) =>
          dropdown
            .addOption('en', 'English')
            .addOption('fr', 'French')
            .setValue(this.plugin.settings.stt.language)
            .onChange(async (value) => {
              this.plugin.settings.stt.language = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Include Word-Level Timestamps')
        .setDesc('Provides precise timing for each word')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.stt.includeTimestamps)
            .onChange(async (value) => {
              this.plugin.settings.stt.includeTimestamps = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Auto-capitalize')
        .setDesc('Automatically capitalize sentences')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.stt.autoCapitalize)
            .onChange(async (value) => {
              this.plugin.settings.stt.autoCapitalize = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Confidence Threshold')
        .setDesc('Minimum confidence level for transcription (0.0-1.0)')
        .addSlider((slider) =>
          slider
            .setLimits(0, 1, 0.05)
            .setValue(this.plugin.settings.stt.confidenceThreshold)
            .setDynamicTooltip()
            .onChange(async (value) => {
              this.plugin.settings.stt.confidenceThreshold = value;
              await this.plugin.saveSettings();
            })
        );
    });

    // ===== VOICE MANAGEMENT =====
    if (this.plugin.settings.defaultTier !== 'basic') {
      this.createCollapsibleSection(containerEl, 'Voice Management', () => {
        const voiceCount = this.plugin.settings.voices.length;
        new Setting(containerEl)
          .setName('Registered Voices')
          .setDesc(`${voiceCount} custom voices saved`)
          .addButton((btn) =>
            btn
              .setButtonText(voiceCount > 0 ? `View / Manage (${voiceCount})` : 'No voices yet')
              .onClick(() => {
                // Open voice manager
                new Notice('Voice management UI coming soon', 3000);
              })
          );
      });
    }

    // ===== API CONFIGURATION =====
    this.createCollapsibleSection(containerEl, 'API Configuration', () => {
      new Setting(containerEl)
        .setName('MCP Server URL')
        .setDesc('Default: http://localhost:8000')
        .addText((text) =>
          text
            .setPlaceholder('http://localhost:8000')
            .setValue(this.plugin.settings.api.serverUrl)
            .onChange(async (value) => {
              this.plugin.settings.api.serverUrl = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Test Connection')
        .setDesc('Verify MCP server is reachable')
        .addButton((btn) =>
          btn.setButtonText('Test').onClick(async () => {
            try {
              const result = await this.plugin.mcpClient.healthCheck();
              if (result.status === 'ok') {
                new Notice('✓ MCP server is online and responding', 3000);
              } else {
                new Notice('✗ MCP server responded with error: ' + result.message, 5000);
              }
            } catch (error) {
              new Notice('✗ Could not connect to MCP server. Check URL and ensure server is running.', 5000);
            }
          })
        );

      new Setting(containerEl)
        .setName('Use GPU if Available')
        .setDesc('Enable GPU acceleration for faster processing')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.api.useGpu)
            .onChange(async (value) => {
              this.plugin.settings.api.useGpu = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Timeout (seconds)')
        .setDesc('How long to wait for operations before timing out')
        .addText((text) =>
          text
            .setPlaceholder('30')
            .setValue(String(this.plugin.settings.api.timeoutSeconds))
            .onChange(async (value) => {
              const num = parseInt(value);
              if (!isNaN(num)) {
                this.plugin.settings.api.timeoutSeconds = num;
                await this.plugin.saveSettings();
              }
            })
        );
    });

    // ===== CACHE SETTINGS =====
    this.createCollapsibleSection(containerEl, 'Cache Settings', () => {
      new Setting(containerEl)
        .setName('Enable Caching')
        .setDesc('Cache generated audio and transcriptions to avoid re-processing')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.cache.enabled)
            .onChange(async (value) => {
              this.plugin.settings.cache.enabled = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Max Cache Size (MB)')
        .setDesc('Delete oldest items when cache exceeds this size')
        .addText((text) =>
          text
            .setPlaceholder('500')
            .setValue(String(this.plugin.settings.cache.maxSizeMB))
            .onChange(async (value) => {
              const num = parseInt(value);
              if (!isNaN(num)) {
                this.plugin.settings.cache.maxSizeMB = num;
                await this.plugin.saveSettings();
              }
            })
        );

      new Setting(containerEl)
        .setName('Retention (days)')
        .setDesc('Auto-delete cache entries older than this')
        .addText((text) =>
          text
            .setPlaceholder('30')
            .setValue(String(this.plugin.settings.cache.retentionDays))
            .onChange(async (value) => {
              const num = parseInt(value);
              if (!isNaN(num)) {
                this.plugin.settings.cache.retentionDays = num;
                await this.plugin.saveSettings();
              }
            })
        );

      new Setting(containerEl)
        .setName('Clear Cache Now')
        .setDesc('Permanently delete all cached audio and results')
        .addButton((btn) =>
          btn.setButtonText('Clear Cache').onClick(async () => {
            // Implement cache clearing
            new Notice('Cache clearing not yet implemented', 3000);
          })
        );
    });

    // ===== PLUGIN BEHAVIOR =====
    this.createCollapsibleSection(containerEl, 'Plugin Behavior', () => {
      new Setting(containerEl)
        .setName('Show Status Bar')
        .setDesc('Display status indicator at bottom of window')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.ui.showStatusBar)
            .onChange(async (value) => {
              this.plugin.settings.ui.showStatusBar = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Show Progress Notifications')
        .setDesc('Display notifications while processing')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.ui.showProgressNotifications)
            .onChange(async (value) => {
              this.plugin.settings.ui.showProgressNotifications = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Insert Results as Code Blocks')
        .setDesc('Wrap inserted text in code blocks')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.ui.insertResultsAsCodeBlocks)
            .onChange(async (value) => {
              this.plugin.settings.ui.insertResultsAsCodeBlocks = value;
              await this.plugin.saveSettings();
            })
        );
    });

    // ===== ACCESSIBILITY =====
    this.createCollapsibleSection(containerEl, 'Accessibility', () => {
      new Setting(containerEl)
        .setName('Screen Reader Mode')
        .setDesc('Optimize UI for screen readers')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.accessibility.screenReaderMode)
            .onChange(async (value) => {
              this.plugin.settings.accessibility.screenReaderMode = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('High Contrast')
        .setDesc('Increase contrast for better visibility')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.accessibility.highContrast)
            .onChange(async (value) => {
              this.plugin.settings.accessibility.highContrast = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Large Text')
        .setDesc('Increase font size throughout UI')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.accessibility.largeText)
            .onChange(async (value) => {
              this.plugin.settings.accessibility.largeText = value;
              await this.plugin.saveSettings();
            })
        );

      new Setting(containerEl)
        .setName('Reduce Animations')
        .setDesc('Minimize motion and animations')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.accessibility.reduceAnimations)
            .onChange(async (value) => {
              this.plugin.settings.accessibility.reduceAnimations = value;
              await this.plugin.saveSettings();
            })
        );
    });

    // ===== EXPERIMENTAL FEATURES =====
    if (this.plugin.settings.defaultTier === 'advanced') {
      this.createCollapsibleSection(containerEl, 'Experimental Features', () => {
        new Setting(containerEl)
          .setName('Enable Moshi (Voice Conversation)')
          .setDesc('Full-duplex voice conversation with AI (requires GPU with 24GB+ VRAM)')
          .addToggle((toggle) =>
            toggle
              .setValue(this.plugin.settings.experimental.enableMoshi)
              .onChange(async (value) => {
                this.plugin.settings.experimental.enableMoshi = value;
                await this.plugin.saveSettings();
              })
          );

        new Setting(containerEl)
          .setName('Enable Hibiki (Speech Translation)')
          .setDesc('Translate speech between English and French')
          .addToggle((toggle) =>
            toggle
              .setValue(this.plugin.settings.experimental.enableHibiki)
              .onChange(async (value) => {
                this.plugin.settings.experimental.enableHibiki = value;
                await this.plugin.saveSettings();
              })
          );
      });
    }
  }

  private createCollapsibleSection(
    container: HTMLElement,
    title: string,
    renderFn: () => void
  ): void {
    const section = container.createDiv({ cls: 'settings-section' });
    const header = section.createEl('div', { cls: 'settings-section-header' });
    header.style.cursor = 'pointer';
    header.style.paddingTop = '10px';
    header.style.paddingBottom = '10px';

    const titleEl = header.createEl('h3', { text: `▼ ${title}` });
    titleEl.style.margin = '0';

    const contentDiv = section.createDiv({ cls: 'settings-section-content' });

    header.addEventListener('click', () => {
      const isHidden = contentDiv.style.display === 'none';
      contentDiv.style.display = isHidden ? 'block' : 'none';
      titleEl.setText(isHidden ? `▼ ${title}` : `► ${title}`);
    });

    renderFn();
  }
}
