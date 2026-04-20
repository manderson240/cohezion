# Keybindings Guide: Kitty Super-Modified Shortcuts

Master the new 0.67.2+ keybinding system with Kitty super-modified shortcuts.

## Overview

Pi 0.67.2+ supports `super`-modified keybindings for Kitty terminal users. This enables more ergonomic shortcuts using the Command key (macOS) or Windows key (Linux/Windows).

## What are Super-Modified Shortcuts?

Super = Platform-specific modifier:
- **macOS**: Cmd (⌘)
- **Windows**: Windows key (⊞)
- **Linux**: Configurable (often Win key)

Supported combinations:
- `super+k` → Quick action key
- `super+enter` → Submit with modifier
- `ctrl+super+k` → Combined modifiers

## Cohezion Default Keybindings

File: `.pi/keybindings.json`

| Shortcut | Action | Default Fallback |
|----------|--------|------------------|
| `super+n` | New session | *(none)* |
| `super+t` | Open session tree | `Escape` twice |
| `super+shift+f` | Fork session | *(none)* |
| `super+m` | Model selector | `Ctrl+L` |
| `super+o` | Expand/collapse tools | `Ctrl+O` |
| `super+enter` | Submit + queue follow-up | `Enter`, `Alt+Enter` |
| `super+k` | Cancel/abort | `Escape` |

## Terminal Setup

### Kitty Terminal

**macOS:**
```bash
# ~/.config/kitty/kitty.conf
macos_option_as_alt no  # Ensure Alt keys work normally
```

**Linux:**
```bash
# ~/.config/kitty/kitty.conf
# Super key should work by default
# Verify with: kitty +kitten show_key -m super
```

### Other Terminals

| Terminal | Super Key Support | Notes |
|----------|-------------------|-------|
| Kitty | ✅ Full | Best experience |
| iTerm2 | ⚠️ Partial | Use Cmd as super |
| Alacritty | ⚠️ Partial | Config dependent |
| Windows Terminal | ⚠️ Partial | Win key may trigger OS actions |

## Customizing Keybindings

### Method 1: Edit `.pi/keybindings.json` (Project-Specific)

```json
{
  "_description": "My custom Cohezion bindings",
  "app.session.new": ["super+n", "ctrl+shift+n"],
  "app.session.tree": ["super+t"],
  "app.model.select": ["super+m"],
  "custom.shortcuts": ["super+1", "super+2"]
}
```

### Method 2: User-Wide Config `~/.pi/agent/keybindings.json`

```json
{
  "tui.editor.cursorUp": ["up", "ctrl+p"],
  "tui.editor.cursorDown": ["down", "ctrl+n"],
  "app.session.new": ["super+n"]
}
```

### Method 3: Per-Session Override

```bash
# Use different keybindings for specific projects
pi --keybindings /path/to/custom/keybindings.json
```

## Keybinding IDs Reference

### Application Actions

```
app.interrupt          # Cancel/abort
app.clear              # Clear editor
app.exit               # Exit (editor empty)
app.suspend            # Suspend (Ctrl+Z)
app.editor.external    # Open external editor
app.clipboard.pasteImage # Paste image
```

### Session Actions

```
app.session.new
app.session.tree
app.session.fork
app.session.resume
app.session.togglePath
app.session.rename
app.session.delete
```

### Model & Thinking

```
app.model.select        # Open model selector
app.model.cycleForward  # Cycle models (Ctrl+P)
app.model.cycleBackward # Reverse cycle (Shift+Ctrl+P)
app.thinking.cycle      # Cycle thinking level
app.thinking.toggle     # Collapse/expand thinking
```

### Tree Navigation

```
app.tree.foldOrUp
app.tree.unfoldOrDown
app.tree.editLabel
app.tree.toggleLabelTimestamp
```

### TUI Editor

```
tui.editor.cursorUp
tui.editor.cursorDown
tui.editor.cursorLeft
tui.editor.cursorRight
tui.editor.cursorWordLeft
tui.editor.cursorWordRight
tui.editor.deleteCharBackward
tui.editor.deleteCharForward
tui.editor.deleteWordBackward
tui.editor.yank
```

## Advanced: Extension Keybindings

Extensions can register custom keybindings:

```typescript
// my-extension.ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // Register keyboard shortcut
  pi.registerShortcut("super+c", async (ctx) => {
    ctx.ui.notify("Custom super+c triggered!");
    // Your custom logic here
  });

  // Register with context
  pi.registerShortcut("ctrl+shift+r", async (ctx) => {
    await ctx.compact();
  });
}
```

## Migration from Pre-0.67.2

### Old Format (Pre-namespaced)

```json
{
  "cursorUp": ["up"],
  "expandTools": ["ctrl+o"],
  "selectConfirm": ["enter"]
}
```

### New Format (Namespaced)

```json
{
  "tui.editor.cursorUp": ["up"],
  "app.tools.expand": ["ctrl+o"],
  "tui.select.confirm": ["enter"]
}
```

**Migration is automatic** - Pi converts old format on startup.

## Troubleshooting

### Super Key Not Working

```bash
# Test if terminal receives super key
# In Kitty:
kitty +kitten show_key -m super

# Should show super modifier in output
```

### Keybindings Not Loading

```bash
# Reload keybindings without restarting
/reload  # In Pi interactive mode
```

### Conflicts with OS Shortcuts

| OS Shortcut | Pi Alternative |
|-------------|----------------|
| `super+enter` (maximize) | Use `ctrl+enter` or `alt+enter` |
| `super+o` (open file) | Use `ctrl+o` |
| `super+n` (new window) | Use `ctrl+shift+n` |

## See Also

- [Pi Keybindings Docs](https://github.com/badlogic/pi-mono/blob/main/pi/packages/coding-agent/docs/keybindings.md)
- [Quick Start](00_QUICKSTART.md)
- [Troubleshooting](99_TROUBLESHOOTING.md)

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
