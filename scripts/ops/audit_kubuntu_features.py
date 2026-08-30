#!/usr/bin/env python3
"""Audit advanced Kubuntu / Linux host features for local inference on Strix Halo."""

import os
import shutil
import subprocess

features = {
    "cgroups_v2": os.path.exists("/sys/fs/cgroup/cgroup.controllers"),
    "hugepages_2mb": os.path.exists("/sys/kernel/mm/hugepages/hugepages-2048kB"),
    "transparent_hugepages": os.path.exists("/sys/kernel/mm/transparent_hugepage/enabled"),
    "zram_swap": os.path.exists("/dev/zram0") or shutil.which("zramctl") is not None,
    "systemd_run": shutil.which("systemd-run") is not None,
    "bubblewrap_namespaces": shutil.which("bwrap") is not None,
    "numactl": shutil.which("numactl") is not None,
    "taskset_affinity": shutil.which("taskset") is not None,
    "perf_profiling": shutil.which("perf") is not None,
    "bpftrace_ebpf": shutil.which("bpftrace") is not None,
    "rocm_smi": shutil.which("rocm-smi") is not None,
}

print("=== KUBUNTU / LINUX ADVANCED INFERENCE FEATURES AUDIT ===")
for k, v in features.items():
    print(f"  {'✓' if v else '✗'} {k:25}: {'AVAILABLE' if v else 'NOT FOUND'}")
