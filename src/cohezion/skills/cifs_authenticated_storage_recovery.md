---
name: cifs-authenticated-storage-recovery
description: "Diagnose and resolve CIFS/Samba guest permission denied errors on network storage mounts, configure authenticated credentials in /etc/fstab, reclaim space, and organize media downloads into clean artist/album directory trees."
category: infrastructure
tags: [cifs, samba, network-mounts, fstab, storage-recovery, media-organization]
metadata:
  version: "1.0.0"
  see_also: ["LOCAL_INFERENCE_ROUTING", "SYSTEM_MONITORING_PRIME"]
---

# SKILL: CIFS_AUTHENTICATED_STORAGE_RECOVERY

## DOMAIN EXPERTISE

You are a network storage & Linux system administration specialist for the Cohezion infrastructure. Your role is to resolve CIFS/Samba permission issues, manage network HDD mounts, recover disk space from temporary downloads, and organize unorganized media downloads into structured libraries.

## Samba Guest Permission Trap & Solution

### The Trap
When mounting a Samba share using `guest` or `sec=none` options:
- The Samba server maps client requests to an unprivileged guest UID (e.g., `nobody`).
- Files owned by server-side user `mike` (`0755`/`0644` permissions) will reject client deletion attempts with `rm: Permission denied` — even when running `sudo rm` on the client machine!

### The Authenticated Fix
Update `/etc/fstab` to use the authenticated credentials file (`/home/mike-anderson/.smbcredentials_t30`):

```fstab
//192.168.86.31/public /mnt/wd_mybook cifs vers=3.0,credentials=/home/mike-anderson/.smbcredentials_t30,iocharset=utf8,rw,uid=mike-anderson,gid=mike-anderson,file_mode=0775,dir_mode=0775,x-systemd.automount,_netdev 0 0
```

Re-mount the share:
```bash
sudo umount -l /mnt/wd_mybook
sudo mount -a
```

- **Result**: Grants full read, write, and delete permissions (`rwxrwxr-x`) over all files and folders on the share.

## Media Library Organization Protocol

When downloads accumulate loose in `/mnt/wd_mybook/downloads` instead of moving to destination libraries (`/mnt/wd_mybook/media/music`):

1. **Scaffolding vs Target**: Docker containers (`Lidarr`, `Radarr`, `Jellyfin`) create destination scaffolding (`/media/music`), but misconfigured root paths leave finished downloads in `/downloads`.
2. **Automated Organizer**: Execute `scripts/organize_music_library.py` to parse `Artist - Album [Year]` folder patterns and move them into clean `/media/music/Artist/Album/` trees.

```python
# Example parse logic
artist, album = parse_artist_album(folder_name)
target_dir = Path("/mnt/wd_mybook/media/music") / artist / folder_name
shutil.move(str(source_folder), str(target_dir))
```
