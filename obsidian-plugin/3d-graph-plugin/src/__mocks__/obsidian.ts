export class App {
  vault = new Vault();
}

export class Vault {
  adapter = { basePath: '/mock/vault' };
  getAbstractFileByPath = jest.fn();
  getMarkdownFiles = jest.fn(() => []);
  read = jest.fn(async () => '');
  cachedRead = jest.fn(async () => '');
  modify = jest.fn(async () => {});
  create = jest.fn(async () => ({}));
  on = jest.fn();
  off = jest.fn();
}

export class TFile {
  path = '';
  basename = '';
  extension = 'md';
  stat = { mtime: Date.now(), ctime: Date.now(), size: 0 };
}

export class TFolder {
  path = '';
  children: TAbstractFile[] = [];
  isRoot = () => false;
}

export class TAbstractFile {
  path = '';
  name = '';
}

function createMockEl(): any {
  const el: any = {
    createEl: jest.fn(() => createMockEl()),
    createDiv: jest.fn(() => createMockEl()),
    empty: jest.fn(),
    setText: jest.fn(),
    addClass: jest.fn(),
    appendChild: jest.fn(),
    style: {},
    innerHTML: '',
    textContent: '',
    children: [],
    querySelector: jest.fn(() => null),
    querySelectorAll: jest.fn(() => []),
  };
  return el;
}

export class Modal {
  app: App;
  titleEl: any = createMockEl();
  contentEl: any = createMockEl();
  constructor(app: App) {
    this.app = app;
  }
  open = jest.fn();
  close = jest.fn();
  onOpen = jest.fn();
  onClose = jest.fn();
  setTitle = jest.fn((title: string) => {
    this.titleEl.textContent = title;
  });
}

export class Notice {
  constructor(_message: string) {}
}

export class Plugin {
  app: App;
  manifest: any;
  constructor(app: App, manifest: any) {
    this.app = app;
    this.manifest = manifest;
  }
  addRibbonIcon = jest.fn();
  addCommand = jest.fn();
  addSettingTab = jest.fn();
  loadData = jest.fn(async () => ({}));
  saveData = jest.fn(async () => {});
}

export class PluginSettingTab {
  app: App;
  plugin: Plugin;
  containerEl: any = {
    empty: jest.fn(),
    createEl: jest.fn(() => ({ createEl: jest.fn(), setText: jest.fn() })),
  };
  constructor(app: App, plugin: Plugin) {
    this.app = app;
    this.plugin = plugin;
  }
}

export class Setting {
  settingEl: any = {};
  constructor(_containerEl: any) {}
  setName = jest.fn(() => this);
  setDesc = jest.fn(() => this);
  addText = jest.fn(() => this);
  addToggle = jest.fn(() => this);
  addDropdown = jest.fn(() => this);
}
