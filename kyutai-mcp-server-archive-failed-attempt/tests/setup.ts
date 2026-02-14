/**
 * Jest setup file for Kyutai plugin tests
 * Runs before any tests execute
 */

// Mock Obsidian API globally
jest.mock('obsidian', () => ({
  Plugin: class MockPlugin {
    app: any;
    manifest: any;
    loadSettings: jest.Mock;
    saveSettings: jest.Mock;
    addCommand: jest.Mock;
    addRibbonIcon: jest.Mock;
    addSettingTab: jest.Mock;
    registerEvent: jest.Mock;

    constructor() {
      this.loadSettings = jest.fn();
      this.saveSettings = jest.fn();
      this.addCommand = jest.fn();
      this.addRibbonIcon = jest.fn();
      this.addSettingTab = jest.fn();
      this.registerEvent = jest.fn();
    }
  },
  PluginSettingTab: class MockPluginSettingTab {
    containerEl: any;
    plugin: any;
    constructor(app: any, plugin: any) {
      this.plugin = plugin;
    }
    display() {}
  },
  App: class MockApp {
    vault: any;
    workspace: any;
  },
  Notice: class MockNotice {
    constructor(message: string) {}
  },
  Setting: class MockSetting {
    constructor(el: any) {}
    setName(name: string) { return this; }
    setDesc(desc: string) { return this; }
    addToggle(cb: any) { return this; }
    addDropdown(cb: any) { return this; }
    addSlider(cb: any) { return this; }
    addText(cb: any) { return this; }
    addButton(cb: any) { return this; }
  },
}));

// Mock Web Audio API
global.AudioContext = jest.fn(() => ({
  createMediaStreamSource: jest.fn(),
  createScriptProcessor: jest.fn(),
  createGain: jest.fn(),
  destination: {},
})) as any;

global.MediaRecorder = jest.fn(() => ({
  start: jest.fn(),
  stop: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
})) as any;

// Suppress console logs during tests
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Set up test environment
beforeAll(() => {
  // Any global setup
});

afterEach(() => {
  // Clear mocks after each test
  jest.clearAllMocks();
});
