# WD-MyBook Networked HDD Troubleshooting Guide

## Local Silicon Analysis
To diagnose why the user cannot access their local networked WD-MyBook HDD on a Linux system, we'll follow a **step-by-step diagnostic workflow** that addresses **network discovery, protocol compatibility, and Linux configuration**. This will help identify the root cause and provide a solution.

---

## 🔍 Step 1: Network Discovery & Addressing

### 🔍 1.1. Check for Local Resolutions (mDNS / Avahi)
```bash
sudo mDNS -a
sudo avahi -a
```
- `mDNS` will show the local DNS servers and their IP addresses.
- `avahi` will show the local IP addresses and DNS servers.

### 🔍 1.2. Check for Static IP Address (Static vs DHCP)
```bash
sudo ip a show
sudo ip addr show
```
- Look for static IP addresses assigned to the WD-MyBook HDD.
- Check if the HDD is assigned a static IP via `ip addr` or `ip route`.

### 🔍 1.3. Check Router Client Isolation
- Ensure the WD-MyBook HDD is not being blocked by the router.
- Check the router's firewall rules (e.g., `ufw` or `iptables`) to ensure ports 137, 138, 139, and 445 are open.
- Run:
  ```bash
  sudo ufw status
  ```
  - If any port is blocked, disable it or add it to the allowed list.

### 🔍 1.4. Check for Network Discovery (DNS Resolution)
- If the system is using `mDNS` or `avahi`, ensure the DNS server is correctly configured.
- Check the DNS server's IP address and port (e.g., `192.168.1.100` on port 535).

---

## 🔍 Step 2: Protocol & Version Compatibility

### 🔍 2.1. Check for SMB1 vs SMB2/SMB3
```bash
sudo cinstatus
```
- This will show the supported SMB versions (e.g., SMB1, SMB2, SMB3).

### 🔍 2.2. Check for NTLM vs NTLMv2
```bash
sudo nlm -v
sudo nlmv2 -v
```
- If the system is using NTLM (v2), ensure the user has NTLMv2 enabled.

### 🔍 2.3. Check for SMB1 vs SMB2/SMB3
- Ensure the system is using the correct SMB version (e.g., SMB2).
- Check the `cifs-utils` version:
  ```bash
  cifs-utils --version
  ```
- Check the `vers` parameter in `cifs-utils`:
  ```bash
  cifs-utils --vers=1.0
  ```
- Check if the system is using the correct SMB protocol (e.g., SMB2, SMB3).

### 🔍 2.4. Check for SMB1 vs Legacy SMB (NTLM)
- If the system is using `ntlm`, ensure the user has NTLMv2 enabled.
- Check the `vers` parameter in `cifs-utils`:
  ```bash
  cifs-utils --vers=1.0
  ```
- Ensure the system is using the correct SMB protocol (e.g., SMB2, SMB3).

---

## 🔍 Step 3: Linux Mount & Driver Configuration

### 🔍 3.1. Check for Missing Mount Tools
```bash
sudo apt update && sudo apt install -y cifs-utils nfs-common
```
- Install required tools for CIFS and NFS.

### 🔍 3.2. Check `/etc/fstab` Configuration
- Ensure the HDD is mounted correctly in `/etc/fstab`.
- Example:
  ```bash
  /dev/sdX /mnt/wdmybook /mnt/wdmybook / 0 0 cifs
  ```
- Verify that the HDD is mounted with the correct device path and mount type.

### 🔍 3.3. Check for UID/GID Mapping
- Ensure the user has proper UID and GID mapping:
  ```bash
  sudo udev -l
  sudo udevadm --setuid /dev/sdX
  sudo udevadm --setgid /dev/sdX
  ```
- If the user is not mapped, the system may not recognize the HDD.

### 🔍 3.4. Check for Firewall Rules
- Ensure the firewall is not blocking the required ports (e.g., 137, 138, 139, 445).
- Run:
  ```bash
  sudo ufw status
  sudo ufw allow 137 138 139 445
  ```
- If the firewall is blocking, configure it to allow these ports.

### 🔍 3.5. Check for NFS Common Configuration
- If the system is using NFS, ensure the NFS server is configured to accept connections from the WD-MyBook HDD.
- Check the NFS server's configuration file (e.g., `/etc/nfs/nfs.conf`).

---

## 🔍 Summary of Root Causes

| Issue | Possible Cause | Solution |
|------|-------------|--------|
| **Network Discovery** | mDNS / Avahi not resolving the HDD IP, or router blocking ports | Use `avahi` for DNS resolution, disable router firewall if needed. |
| **Protocol Version Compatibility** | HDD is using an incompatible SMB version (e.g., SMB1 vs SMB2) | Update `cifs-utils` to use the correct version, check `vers` parameter. |
| **Linux Mount & Driver Configuration** | Missing `cifs-utils`, `nfs-common`, or incorrect permissions | Install required tools, configure `/etc/fstab`, and ensure UID/GID mapping is set. |

---

## 🔍 Step-by-Step Diagnostic Workflow

### 🔍 1.1. Network Discovery
```bash
sudo mDNS -a
sudo avahi -a
```

### 🔍 1.2. Static vs DHCP
```bash
sudo ip a show
sudo ip addr show
```

### 🔍 1.3. Router Isolation
```bash
sudo ufw status
sudo ufw allow 137 138 139 445
```

### 🔍 2.1. SMB1 vs SMB2
```bash
sudo cinstatus
sudo cifs-utils --vers=1.0
```

### 🔍 2.2. NTLM vs NTLMv2
```bash
sudo nlm -v
sudo nlmv2 -v
```

### 🔍 3.1. Mount Tools
```bash
sudo apt update && sudo apt install -y cifs-utils nfs-common
```

### 🔍 3.2. Mount Configuration
```bash
sudo udev -l
sudo udevadm --setuid /dev/sdX
sudo udevadm --setgid /dev/sdX
```

### 🔍 3.3. UID/GID Mapping
```bash
sudo udev -l
sudo udevadm --setuid /dev/sdX
sudo udevadm --setgid /dev/sdX
```

### 🔍 3.4. Firewall Rules
```bash
sudo ufw status
sudo ufw allow 137 138 139 445
```

### 🔍 3.5. NFS Configuration
```bash
sudo systemctl status nfs
sudo systemctl enable nfs
```

---

## 🔍 Final Recommendations

1. **Update System Tools**: Install `cifs-utils`, `nfs-common`, and `nfs-utils` if not already installed.
2. **Check `/etc/fstab`**: Ensure the HDD is mounted with the correct device path and type.
3. **Verify UID/GID Mapping**: Ensure the user has proper UID and GID mapping enabled.
4. **Check Network Discovery**: Ensure the system is using the correct DNS resolution (e.g., `avahi` or `mDNS`).
5. **Firewall Rules**: Ensure the firewall is configured to allow the required ports (e.g., 137, 138, 139, 445).
6. **Check for SMB Version Compatibility**: Ensure the system is using the correct SMB version (e.g., SMB2).

---

## 🔍 Summary of Steps to Take

1. Run `mDNS -a` and `avahi -a` to check for local DNS resolution.
2. Check `ip a show` and `ip addr show` to verify static vs DHCP IP mapping.
3. Ensure the router is not blocking ports 137, 138, 139, and 445.
4. Install and configure `cifs-utils`, `nfs-common`, and `nfs-utils`.
5. Check `/etc/fstab` and ensure the HDD is mounted correctly.
6. Confirm UID and GID mapping is set.
7. Run `ufw status` and `ufw allow` to check firewall rules.
8. Check NFS server configuration and ensure it accepts connections from the HDD.

---

Let me know if you'd like a **complete script** or **tool** to automate this process!

## Cloud Peer Synthesis & Diagnostic Workflow
Below is a clean, safe, and self-contained Bash script you can save as `scripts/check_wd_mybook.sh`.

It **diagnoses** the WD-MyBook by:

- Resolving mDNS names (`wdmybook.local`, `mybook.local`)
- Scanning the local subnet for hosts listening on SMB ports **139/445**
- Probing SMB shares with both SMB1/NTLM and SMB2/SMB3
- Checking for required packages (`cifs-utils`, `smbclient`, `avahi-daemon`)
- Printing a modern, safe `/etc/fstab` entry and a manual mount command

By default it only **reports**. If you run it with `--repair`, it will attempt to install missing packages (requires `sudo`/root and an apt-based distro; other distros will print manual install commands instead).

```bash
#!/usr/bin/env bash
# scripts/check_wd_mybook.sh
# Diagnostic & repair script for a networked WD-MyBook HDD from Linux.
# Usage:
#   ./check_wd_mybook.sh                # diagnose only
#   ./check_wd_mybook.sh --repair       # diagnose and install missing packages
#   ./check_wd_mybook.sh --net 192.168.1.0/24 --user myuser --password mypass
#
# WARNING: SMB1/NT1 is insecure. It is only probed for legacy NAS compatibility.
#          Prefer SMB 3.0 or higher whenever possible.

set -uo pipefail
IFS=$'\n\t'

# ---------- Configuration ----------
declare -a HOSTNAMES=("wdmybook.local" "mybook.local")
REPORT_FILE="/tmp/wd_mybook_diag_$(date +%Y%m%d_%H%M%S).log"
REPAIR=0
SUBNET=""
SMB_USER=""
SMB_PASS=""
TIMEOUT=3

# ---------- Helpers ----------
log() {
    echo -e "$@" | tee -a "$REPORT_FILE"
}

run_cmd() {
    # Run a command, suppress errors, return 0/1 status.
    "$@" >/dev/null 2>&1
}

header() {
    log "\n\e[1;34m=== $1 ===\e[0m"
}

warn() {
    log "\e[1;33mWARN:\e[0m $*"
}

error() {
    log "\e[1;31mERROR:\e[0m $*"
}

ok() {
    log "\e[1;32mOK:\e[0m   $*"
}

require_root() {
    if [[ $EUID -ne 0 ]]; then
        warn "This step works best with root privileges. Try: sudo $0 $*"
        return 1
    fi
    return 0
}

detect_distro() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "debian"
    elif command -v dnf >/dev/null 2>&1; then
        echo "fedora-dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "fedora-yum"
    elif command -v pacman >/dev/null 2>&1; then
        echo "arch"
    else
        echo "unknown"
    fi
}

package_name() {
    local distro="$1"
    local pkg="$2"
    case "$distro" in
        debian) echo "$pkg" ;;
        fedora-dnf|fedora-yum)
            case "$pkg" in
                cifs-utils) echo "cifs-utils" ;;
                smbclient) echo "samba-client" ;;
                avahi-daemon) echo "avahi" ;;
            esac
            ;;
        arch)
            case "$pkg" in
                cifs-utils) echo "cifs-utils" ;;
                smbclient) echo "smbclient" ;;
                avahi-daemon) echo "avahi" ;;
            esac
            ;;
        *) echo "$pkg" ;;
    esac
}

install_pkg() {
    local distro="$1"
    local pkg="$2"
    local real_pkg
    real_pkg=$(package_name "$distro" "$pkg")

    log "Attempting to install \e[1m${real_pkg}\e[0m on ${distro}..."

    case "$distro" in
        debian)
            if require_root; then
                apt-get update -qq && apt-get install -y "$real_pkg"
            fi
            ;;
        fedora-dnf)
            if require_root; then
                dnf install -y "$real_pkg"
            fi
            ;;
        fedora-yum)
            if require_root; then
                yum install -y "$real_pkg"
            fi
            ;;
        arch)
            if require_root; then
                pacman -Sy --noconfirm "$real_pkg"
            fi
            ;;
        *)
            warn "Unknown distro. Please install '$real_pkg' manually."
            return 1
            ;;
    esac
}

# ---------- Argument parsing ----------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -r|--repair)
                REPAIR=1
                shift
                ;;
            -n|--net)
                SUBNET="$2"
                shift 2
                ;;
            -u|--user)
                SMB_USER="$2"
                shift 2
                ;;
            -p|--password)
                SMB_PASS="$2"
                shift 2
                ;;
            -h|--help)
                cat <<'EOF'
Usage: check_wd_mybook.sh [OPTIONS]

  -r, --repair            Install missing packages (requires root)
  -n, --net  SUBNET       Scan this subnet, e.g. 192.168.1.0/24
  -u, --user  USER        SMB username for share listing/mount
  -p, --password PASS     SMB password for share listing/mount
  -h, --help              Show this help
EOF
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# ---------- Subnet detection ----------
detect_subnet() {
    local iface subnets
    subnets=$(ip -4 route show | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+.*scope link/ {print $1}' | head -n5)
    if [[ -z "$subnets" ]]; then
        warn "Could not auto-detect a local subnet. Specify with --net <subnet>."
        return 1
    fi
    log "Auto-detected local subnet(s):"
    echo "$subnets" | while read -r s; do
        log "  - $s"
    done
    # Use the first one if not user-supplied
    if [[ -z "$SUBNET" ]]; then
        SUBNET=$(echo "$subnets" | head -n1)
    fi
    return 0
}

# ---------- mDNS resolution ----------
probe_mdns() {
    header "mDNS / Avahi Resolution"
    local found=0
    for h in "${HOSTNAMES[@]}"; do
        log "Resolving ${h} ..."
        if command -v avahi-resolve-host-name >/dev/null 2>&1; then
            local result
            result=$(avahi-resolve-host-name -4 "$h" 2>/dev/null | awk '{print $2}')
            if [[ -n "$result" ]]; then
                ok "${h} -> ${result}"
                FOUND_HOSTS+=("$result")
                found=1
            else
                warn "${h} not found via avahi-resolve-host-name"
            fi
        else
            warn "avahi-resolve-host-name not installed; cannot resolve .local names"
        fi
    done
    if [[ $found -eq 0 ]]; then
        warn "No mDNS hostname resolved. This is normal if the NAS uses plain NetBIOS or a static IP."
    fi
}

# ---------- Host discovery / port scan ----------
scan_subnet() {
    header "Subnet scan for SMB ports (139, 445) on ${SUBNET}"
    local hosts=()

    if command -v nmap >/dev/null 2>&1; then
        log "Using nmap for fast scan ..."
        while read -r line; do
            local ip ports
            ip=$(echo "$line" | grep -oP 'Host: \K[0-9.]+')
            ports=$(echo "$line" | grep -oP '\d+/open' | cut -d'/' -f1 | tr '\n' ' ')
            if [[ -n "$ip" && -n "$ports" ]]; then
                ok "Host ${ip} has open SMB ports: ${ports}"
                hosts+=("$ip")
            fi
        done < <(nmap -p 139,445 --open -oG - "$SUBNET" 2>/dev/null | grep "/open")
    else
        warn "nmap not found. Falling back to slower /dev/tcp scan."
        log "Install nmap to speed this up: sudo apt-get install nmap"
        local netbase
        netbase=$(echo "$SUBNET" | sed -E 's|/([0-9]+)||')
        local prefix
        prefix=$(echo "$netbase" | cut -d. -f1-3)
        local start end
        start=$(echo "$netbase" | cut -d. -f4)
        end=254
        # crude assumption: /24
        if [[ "$SUBNET" == */16 ]]; then
            warn "Fallback scan only supports /24 comfortably; limiting to ${prefix}.0/24"
        fi
        for i in $(seq "$start" "$end"); do
            local ip="${prefix}.${i}"
            if (echo >/dev/tcp/"${ip}"/445) >/dev/null 2>&1; then
                ok "Host ${ip}:445 is reachable"
                hosts+=("$ip")
            fi
        done
    fi

    # Merge with any mDNS-resolved hosts
    for h in "${FOUND_HOSTS[@]:-}"; do
        [[ -n "${h:-}" ]] && hosts+=("$h")
    done

    # Deduplicate
    FOUND_HOSTS=($(printf "%s\n" "${hosts[@]:-}" | sort -u))
    if [[ ${#FOUND_HOSTS[@]} -eq 0 ]]; then
        error "No SMB hosts discovered. Verify the NAS is powered on and on the same network."
        return 1
    fi
    return 0
}

# ---------- SMB protocol negotiation ----------
smb_creds() {
    if [[ -n "$SMB_USER" ]]; then
        if [[ -n "$SMB_PASS" ]]; then
            echo "-U ${SMB_USER}%${SMB_PASS}"
        else
            echo "-U ${SMB_USER}"
        fi
    else
        echo "-N"
    fi
}

probe_smb() {
    header "SMB protocol negotiation tests"
    local creds
    creds=$(smb_creds)

    if ! command -v smbclient >/dev/null 2>&1; then
        warn "smbclient not installed; skipping SMB share listing."
        return 1
    fi

    for ip in "${FOUND_HOSTS[@]}"; do
        log "\n--- Testing host: ${ip} ---"

        # SMB1/NT1 (legacy, insecure, often needed for old WD firmware)
        log "Trying SMB1/NT1 ..."
        if smbclient -L "//${ip}" ${creds} -m NT1 --socket-options='TCP_NODELAY IPTOS_LOWDELAY SO_KEEPALIVE' -t "$TIMEOUT" 2>/dev/null | tee -a "$REPORT_FILE" | grep -q "Sharename"; then
            warn "Host ${ip} responded to SMB1/NT1. Consider enabling SMB2/SMB3 on the NAS for security."
        else
            log "  SMB1/NT1 did not return shares (this is expected on modern firmware)."
        fi

        # SMB2
        log "Trying SMB2 ..."
        if smbclient -L "//${ip}" ${creds} -m SMB2 --socket-options='TCP_NODELAY IPTOS_LOWDELAY SO_KEEPALIVE' -t "$TIMEOUT" 2>/dev/null | tee -a "$REPORT_FILE" | grep -q "Sharename"; then
            ok "Host ${ip} supports SMB2 and returned shares."
        else
            log "  SMB2 probe did not return shares."
        fi

        # SMB3
        log "Trying SMB3 ..."
        if smbclient -L "//${ip}" ${creds} -m SMB3 --socket-options='TCP_NODELAY IPTOS_LOWDELAY SO_KEEPALIVE' -t "$TIMEOUT" 2>/dev/null | tee -a "$REPORT_FILE" | grep -q "Sharename"; then
            ok "Host ${ip} supports SMB3 and returned shares."
        else
            log "  SMB3 probe did not return shares."
        fi
    done
}

# ---------- Package checks ----------
check_packages() {
    header "Package / Kernel checks"
    local distro
    distro=$(detect_distro)
    log "Detected distro family: ${distro}"

    local -a required=("cifs-utils" "smbclient" "avahi-daemon")
    local missing=()

    for pkg in "${required[@]}"; do
        local real_pkg
        real_pkg=$(package_name "$distro" "$pkg")

        local installed=0
        case "$pkg" in
            cifs-utils)
                command -v mount.cifs >/dev/null 2>&1 && installed=1
                ;;
            smbclient)
                command -v smbclient >/dev/null 2>&1 && installed=1
                ;;
            avahi-daemon)
                command -v avahi-resolve-host-name >/dev/null 2>&1 && installed=1
                ;;
        esac

        if [[ $installed -eq 1 ]]; then
            ok "${real_pkg} appears installed"
        else
            warn "${real_pkg} is missing"
            missing+=("$pkg")
        fi
    done

    # Kernel module check
    if lsmod 2>/dev/null | grep -q "^cifs"; then
        ok "cifs kernel module is loaded"
    else
        warn "cifs kernel module is not currently loaded"
        if require_root; then
            modprobe cifs 2>/dev/null && ok "cifs module loaded" || warn "Failed to load cifs module"
        fi
    fi

    # Repair missing packages if requested
    if [[ ${#missing[@]} -gt 0 && $REPAIR -eq 1 ]]; then
        header "Repair: installing missing packages"
        for pkg in "${missing[@]}"; do
            install_pkg "$distro" "$pkg"
        done
    elif [[ ${#missing[@]} -gt 0 ]]; then
        log "\nTo install missing packages, run:\n  sudo $0 --repair"
    fi
}

# ---------- Recommendations ----------
recommend_mount() {
    header "Recommended mount configuration"

    if [[ ${#FOUND_HOSTS[@]} -eq 0 ]]; then
        warn "No host discovered; cannot generate a specific mount recommendation."
        return 1
    fi

    local target_ip="${FOUND_HOSTS[0]}"
    local target_share=""

    # Try to pick a non-default share name if smbclient worked
    if command -v smbclient >/dev/null 2>&1; then
        local creds
        creds=$(smb_creds)
        local shares
        shares=$(smbclient -L "//${target_ip}" ${creds} -m SMB3 -t "$TIMEOUT" 2>/dev/null |
                 awk '/^\s+[A-Za-z0-9_\-]/ {print $1}' |
                 grep -vE '^(Sharename|------|IPC\$|print\$|ADMIN\$|C\$|D\$$)' | head -n1)
        if [[ -n "$shares" ]]; then
            target_share="$shares"
        fi
    fi

    if [[ -z "$target_share" ]]; then
        target_share="Public"   # common default for WD MyBook
        warn "Could not auto-detect share name; defaulting to '${target_share}'"
    fi

    local mount_point="/mnt/wdmybook"
    local credentials_file="/etc/samba/wdmybook.creds"

    log "Detected target: //${target_ip}/${target_share}"
    log "Suggested local mount point: ${mount_point}"

    if [[ -n "$SMB_USER" ]]; then
        log "\nCreate a credential file:"
        log "  sudo mkdir -p /etc/samba"
        log "  sudo tee ${credentials_file} <<EOF"
        log "username=${SMB_USER}"
        log "password=${SMB_PASS:-<your_password>}"
        log "domain=WORKGROUP"
        log "EOF"
        log "  sudo chmod 600 ${credentials_file}\n"
    fi

    log "\n----- Manual mount (test first) -----"
    if [[ -n "$SMB_USER" ]]; then
        log "sudo mkdir -p ${mount_point}"
        log "sudo mount -t cifs //${target_ip}/${target_share} ${mount_point} \\\\"
        log "  -o credentials=${credentials_file},vers=3.0,iocharset=utf8,uid=\$USER,gid=\$USER,file_mode=0644,dir_mode=0755,nofail,_netdev"
    else
        log "sudo mkdir -p ${mount_point}"
        log "sudo mount -t cifs //${target_ip}/${target_share} ${mount_point} \\\\"
        log "  -o guest,vers=3.0,iocharset=utf8,uid=\$USER,gid=\$USER,file_mode=0644,dir_mode=0755,nofail,_netdev"
    fi

    log "\n----- /etc/fstab entry -----"
    if [[ -n "$SMB_USER" ]]; then
        log "//${target_ip}/${target_share} ${mount_point} cifs credentials=${credentials_file},vers=3.0,iocharset=utf8,uid=1000,gid=1000,file_mode=0644,dir_mode=0755,nofail,_netdev,x-systemd.automount,x-systemd.requires=network-online.target 0 0"
    else
        log "//${target_ip}/${target_share} ${mount_point} cifs guest,vers=3.0,iocharset=utf8,uid=1000,gid=1000,file_mode=0644,dir_mode=0755,nofail,_netdev,x-systemd.automount,x-systemd.requires=network-online.target 0 0"
    fi

    log "\nAfter adding the fstab entry, run:"
    log "  sudo systemctl daemon-reload"
    log "  sudo mount ${mount_point}"
}

# ---------- Main ----------
main() {
    parse_args "$@"

    : > "$REPORT_FILE"
    log "WD-MyBook Linux diagnostic report started at $(date)"
    log "Log file: ${REPORT_FILE}"

    check_packages

    # Global array for discovered hosts
    declare -ga FOUND_HOSTS=()
    probe_mdns

    if ! detect_subnet; then
        error "Cannot determine subnet; use --net <subnet>."
        exit 1
    fi

    scan_subnet
    probe_smb
    recommend_mount

    header "Done"
    log "Full report saved to: ${REPORT_FILE}"
}

main "$@"
```

### Quick start

1. Make it executable:
   ```bash
   chmod +x scripts/check_wd_mybook.sh
   ```

2. Run a read-only diagnosis:
   ```bash
   ./scripts/check_wd_mybook.sh
   ```

3. If a username/password is required:
   ```bash
   ./scripts/check_wd_mybook.sh --user alice --password secret
   ```

4. To install missing tools (requires root):
   ```bash
   sudo ./scripts/check_wd_mybook.sh --repair
   ```

### Notes / safety
- The script **defaults to reporting only**. `--repair` is required to install packages.
- SMB1/NT1 is probed only for compatibility with older WD firmware; modern systems should prefer `vers=3.0`.
- The generated `/etc/fstab` line uses `nofail`, `_netdev`, and `x-systemd.automount` so boot is not blocked if the NAS is offline.
- Always test a mount manually before adding it to `/etc/fstab`.
