---
name: appimage-desktop-integration
description: |
  Create desktop launcher icons for AppImages on Linux, especially Electron apps
  on Wayland. Use when: (1) AppImage runs but no visible window appears, (2) user
  wants clickable desktop icon for AppImage, (3) XDG_SESSION_TYPE=wayland and
  Electron app window is invisible. Key insight: Wayland requires --no-sandbox
  and --ozone-platform-hint=auto flags for Electron AppImages.
author: Claude Code
version: 1.0.0
---

# AppImage Desktop Integration

## Problem

Electron AppImages on Wayland can run successfully (process starts, no errors) but spawn invisible windows due to sandboxing and platform detection issues. Users also want clickable desktop icons rather than launching from terminal.

## Context / Trigger Conditions

Use this skill when:

1. **Invisible Window**: AppImage launches (`pgrep` shows process) but no window appears
2. **Wayland Session**: `echo $XDG_SESSION_TYPE` returns `wayland`
3. **Desktop Icon Request**: User wants to launch AppImage via desktop icon
4. **Electron Apps**: Particularly Obsidian, VSCode, Discord, Slack (Electron-based)

## Solution

### Step 1: Extract Icon from AppImage

```bash
# Extract icon assets (creates /tmp/squashfs-root/)
cd /tmp
~/.local/bin/App.AppImage --appimage-extract usr/share/icons

# Find best quality icon
find /tmp/squashfs-root -name "*.png" -o -name "*.svg" | grep -E "(256|512)" | head -1

# Copy to local icons directory
mkdir -p ~/.local/share/icons
cp /tmp/squashfs-root/usr/share/icons/hicolor/256x256/apps/app.png ~/.local/share/icons/app.png

# Clean up
rm -rf /tmp/squashfs-root
```

### Step 2: Create .desktop Entry

Create `~/.local/share/applications/app.desktop`:

```ini
[Desktop Entry]
Name=AppName
Comment=Brief description
Exec=/path/to/App.AppImage --no-sandbox --ozone-platform-hint=auto %u
Icon=/home/username/.local/share/icons/app.png
Type=Application
Categories=Office;  # Or Utility;Development; etc.
MimeType=x-scheme-handler/appscheme;
StartupWMClass=appname
```

**Critical flags for Wayland:**
- `--no-sandbox` - Allows Electron to bypass sandboxing that breaks Wayland
- `--ozone-platform-hint=auto` - Enables Wayland native support

### Step 3: Register and Install

```bash
# Register URI handler (if app uses custom URI scheme)
xdg-mime default app.desktop x-scheme-handler/appscheme

# Update desktop database
update-desktop-database ~/.local/share/applications/

# Copy to Desktop for clickable icon
cp ~/.local/share/applications/app.desktop ~/Desktop/app.desktop
chmod +x ~/Desktop/app.desktop
```

### Step 4: Enable in Desktop Environment

**GNOME**: Right-click desktop icon → "Allow Launching" or "Trust and Launch"

**KDE**: Desktop icon should work immediately

## Verification

```bash
# Test via gtk-launch (simulates desktop click)
gtk-launch app 2>&1 &
sleep 3
pgrep -f "App.AppImage"  # Should show process

# Check window appears
# Press Super key to see Activities overview with app window
```

## Example: Obsidian on Wayland

**Symptom**: `Obsidian.AppImage` runs but no window visible

**Diagnosis**:
```bash
echo $XDG_SESSION_TYPE  # wayland
pgrep -fa Obsidian      # Shows running processes
# But no visible window in activities overview
```

**Solution**:
```bash
# 1. Extract icon
cd /tmp
~/.local/bin/Obsidian.AppImage --appimage-extract usr/share/icons
mkdir -p ~/.local/share/icons
cp /tmp/squashfs-root/usr/share/icons/hicolor/256x256/apps/obsidian.png \
   ~/.local/share/icons/obsidian.png
rm -rf /tmp/squashfs-root

# 2. Create .desktop file
cat > ~/.local/share/applications/obsidian.desktop <<'EOF'
[Desktop Entry]
Name=Obsidian
Comment=Knowledge base and note-taking
Exec=/home/mike-anderson/.local/bin/Obsidian.AppImage --no-sandbox --ozone-platform-hint=auto %u
Icon=/home/mike-anderson/.local/share/icons/obsidian.png
Type=Application
Categories=Office;
MimeType=x-scheme-handler/obsidian;
StartupWMClass=obsidian
EOF

# 3. Install
xdg-mime default obsidian.desktop x-scheme-handler/obsidian
update-desktop-database ~/.local/share/applications/
cp ~/.local/share/applications/obsidian.desktop ~/Desktop/obsidian.desktop
chmod +x ~/Desktop/obsidian.desktop

# 4. Test
gtk-launch obsidian
```

**Result**: Window visible, desktop icon works

## Common Issues

### Icon Still Doesn't Launch

**Check permissions**:
```bash
ls -la ~/Desktop/app.desktop  # Should be executable
chmod +x ~/Desktop/app.desktop
```

**Try direct launch**:
```bash
~/.local/bin/App.AppImage --no-sandbox --ozone-platform-hint=auto
```

If direct launch works but icon doesn't, desktop environment needs to trust the launcher.

### Process Runs But No Window

**Add more Electron flags**:
```ini
Exec=/path/to/App.AppImage --no-sandbox --ozone-platform-hint=auto --disable-gpu-sandbox %u
```

**Check Wayland support**:
```bash
# Some older Electron apps don't support Wayland
# Force X11 mode:
Exec=env GDK_BACKEND=x11 /path/to/App.AppImage --no-sandbox %u
```

## References

- [Electron Wayland Support](https://www.electronjs.org/docs/latest/api/command-line-switches#--ozone-platform-hintplatform-hint)
- [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry-spec/latest/)
- [AppImage Best Practices](https://docs.appimage.org/packaging-guide/optional/desktop-integration.html)
