# AMD Speedrun Work Saved

## Backup Information
**Date:** 2026-04-02 13:55:56 EDT  
**Location:** /home/mike-anderson/dev/cohezion/backup_20260402_135556/  
**Archive:** amd_speedrun_backup_20260402_135556.tar.gz  
**Total Files:** 106

## Submission Summary

### MLA (amd-mixed-mla)
- **9 submission variants**
- Latest: submission.py (677959) - ✅ done
- Key variants: aggressive, hyper, no_cache, sdpa, fastmode, triton_cdna4

### MoE (amd-moe-mxfp4)
- **7 submission variants**
- Latest: submission.py (677786) - ✅ done
- Key variants: minimal, ultra_sorting, asm_moe, fp8_blockscale

### GEMM (amd-mxfp4-mm)
- **22 submission variants**
- Latest: submission.py (677637) - ✅ done
- Key variants: inline, prealloc, loadinline, tritonblas

## Scripts & Tools
- autosubmit.py - Continuous pipeline
- batch_submit.sh - Batch submission
- rotate_submit.sh - Rotation submission
- monitor.sh - Monitor script
- save_work.sh - This backup script

## Autoresearch Infrastructure
- driver.py - K-Search driver
- ksearch_tree.py - Tree data structures
- gpu_kernel_scientist.py - Kernel generation
- popcorn.py - Submission API

## Status
All submissions complete. Work is safe to reboot.

## Post-Reboot Instructions
1. Extract backup if needed: `tar -xzf amd_speedrun_backup_*.tar.gz`
2. Check leaderboard standings
3. Continue optimization from latest variants
4. Focus on MoE (smallest gap to leader)
