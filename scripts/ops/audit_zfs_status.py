#!/usr/bin/env python3
"""ZFS Storage Pool & ARC (Adaptive Replacement Cache) Telemetry Audit."""

import subprocess
import time

def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 80)
    print("💾 ZFS STORAGE POOL & ARC CACHE AUDIT")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 80)

    # 1. zpool status
    zpool_out = run("zpool list 2>&1")
    print(f"1. ZFS Pool Status:\n{zpool_out or 'No zpools detected or standard NVMe mount'}")

    # 2. zfs datasets
    zfs_out = run("zfs list 2>&1")
    print(f"\n2. ZFS Datasets:\n{zfs_out or 'N/A'}")

    # 3. ZFS ARC memory usage if /proc/spl/kstat/zfs/arcstats exists
    arc_stat_path = "/proc/spl/kstat/zfs/arcstats"
    try:
        with open(arc_stat_path) as f:
            lines = f.readlines()
            stats = {}
            for l in lines[2:]:
                parts = l.strip().split()
                if len(parts) >= 3:
                    stats[parts[0]] = parts[2]
            size_mb = int(stats.get("size", 0)) / (1024 * 1024)
            c_max_mb = int(stats.get("c_max", 0)) / (1024 * 1024)
            print(f"\n3. ZFS ARC (Adaptive Replacement Cache):")
            print(f"   • Current ARC Size: {size_mb:.2f} MB")
            print(f"   • Max ARC Target  : {c_max_mb:.2f} MB")
            print(f"   • ARC Hit Ratio   : {stats.get('hits', 'N/A')} hits / {stats.get('misses', 'N/A')} misses")
    except FileNotFoundError:
        print("\n3. ZFS ARC (/proc/spl/kstat/zfs/arcstats): ZFS module not active in kernel or NVMe root ext4/btrfs/xfs.")

    # 4. Storage layout
    df_out = run("df -h / /home /home/mike-anderson/dev/cohezion")
    print(f"\n4. Filesystem Storage Allocation:\n{df_out}")
    print("=" * 80)

if __name__ == "__main__":
    main()
