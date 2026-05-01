# ROCm Path Research: Ubuntu 26.04 LTS + Linux Kernel 7.0

**Research Date**: April 26, 2026  
**Question**: Will ROCm support gfx1151 (Strix Halo) on Ubuntu 26.04 LTS with Kernel 7.0?

---

## Summary

**ANSWER**: Linux Kernel 7.0 improves hardware support, but ROCm support for gfx1151 is still **NOT production-ready**. The environment is technically capable, but ROCm upstream does not consider gfx1151 "Release Ready" yet.

### Key Finding
ROCm classifies gfx1151 as:
- ✅ Build Passing
- ✅ Sanity Tested  
- ❌ **NOT Release Ready** (as of ROCm Roadmap Q1 2026)

---

## Ubuntu 26.04 LTS Status

### ✅ Released: April 23, 2026
- **Codename**: Resolute Raccoon
- **Kernel**: Linux 7.0 (primary feature)
- **Support Cycle**: April 2026 → April 2031 (5 years standard)
- **ESM**: Additional 5 years with Ubuntu Pro (to 2036)

### Linux Kernel 7.0 Features (Relevant to ROCm)

**AMD GPU Updates in Kernel 7.0**:
```
- AMDGPU driver updates for GC 12.1, GC 11.5.4
- SDMA 7.1, SDMA 6.1.4 support
- SMUIO 15.x, PSP 15.x support
- IH 7.1, IH 6.1.1 support
- MMHUB 3.4, MMHUB 4.2 support
```

**GC 11.5.4 = gfx1151 (Strix Halo RDNA 3.5)**

The kernel now has **native support** for the Strix Halo hardware. This removes the need for AMDGPU DKMS, solving the "ROCm DKMS conflict" issue.

---

## ROCm Support for gfx1151

### Official ROCm Roadmap (ROCm/TheRock)
**As of April 2026**:

| Architecture | LLVM Target | Build Passing | Sanity Tested | Release Ready |
|-------------|-------------|---------------|---------------|---------------|
| **RDNA3.5** | **gfx1151** | ✅ | ✅ | ❌ |

**Status**: ROCm will **build** for gfx1151 and passes basic tests, but is **not validated** for production use.

### What This Means

1. **Building from source**: Should work (HSA_OVERRIDE_GFX_VERSION=11.0.0)
2. **Pre-built packages**: May not include gfx1151 optimization
3. **Official support timeline**: **Unknown** - AMD has not committed to a date

### Recent Activity (March-April 2026)

**Pull Request: ROCm/rocm-systems #4402**
- **Title**: "[rocprofiler-compute] Strix halo(gfx1151) support"
- **Status**: Open, under review
- **Activity**: 46 files changed, extensive YAML configs added for gfx1151
- **Components**: Memory chart, speed-of-light metrics, roofline analysis
- **Note**: This is for profiling tools, not core compute runtime

**Issue: ROCm/rccl #2026**
- **Request**: RCCL support for gfx1151
- **Official Response**: "At the moment, we do not have plans to support Strix Halo for RCCL. Please stay tuned for future updates."
- **Status**: Issue closed, tracking in rocm-systems #2788

---

## Comparison: Current vs Ubuntu 26.04 + Kernel 7.0

### Current System (Likely 24.04 / Kernel 6.x)

| Component | Status | Impact |
|-----------|--------|--------|
| Kernel support | ⚠️ Via AMDGPU DKMS | ROCm conflicts |
| ROCm Compute | ❌ Not supported | llama-server ROCm hangs |
| ROCm RCCL | ❌ Not supported | Multi-GPU fails |
| Vulkan Compute | ✅ Working | 105.6 TPS achieved |

### Ubuntu 26.04 + Kernel 7.0

| Component | Status | Impact |
|-----------|--------|--------|
| Kernel support | ✅ Native in Kernel 7.0 | No DKMS needed |
| ROCm Compute | ⚠️ **Same status** | Still not "Release Ready" |
| ROCm RCCL | ⚠️ **Same status** | No official support |
| Vulkan Compute | ✅ Native Mesa 26.x | RADV improvements |

---

## The Critical Blocker

### ROCm "Release Ready" Definition

**Why gfx1151 hasn't been validated**:

1. **Testing Gap**: AMD hasn't validated on consumer Strix Halo hardware
2. **RCCL Priority**: Collective communications (RCCL) prioritized for datacenter, not desktop/laptop
3. **Resource Allocation**: AMD focused on CDNA4 (gfx950) and RDNA4 (gfx1201/1200) for production

### What AMD Has Said

**@huanrwan-amd (AMD Engineer), Nov 2025**:
> "At the moment, we do not have plans to support Strix Halo for RCCL. Please stay tuned for future updates."

**ROCm/TheRock ROADMAP.md**:
> gfx1151: Build Passing ✅, Sanity Tested ✅, Release Ready ❌

---

## Prediction: When Will gfx1151 ROCm Work?

### Scenario A: Best Case (.optimistic)
- **ROCm 6.4 or 6.5** adds gfx1151 validation
- **Timeline**: Late 2026 - 2027
- **Requirement**: Community pressure + resource availability

### Scenario B: More Likely
- **ROCm 7.0** (next major version) includes consumer RDNA3.5
- **Timeline**: 2027-2028
- **Requirement**: Sufficient market adoption of Strix Halo

### Scenario C: Never Officially
- ROCm remains datacenter-focused (CDNA)
- Consumer RDNA uses Vulkan / DirectML exclusively
- **Timeline**: Ongoing

---

## Recommendation

### For Ubuntu 26.04 LTS Migration

**DO**: Upgrade to Ubuntu 26.04 LTS
- ✅ Better hardware support in Kernel 7.0
- ✅ Native AMDGPU (no DKMS conflicts)
- ✅ Mesa 26.0 with RADV improvements
- ✅ Security updates until 2036

**DO NOT**: Expect ROCm support to magically appear
- Same gfx1151 status in ROCm
- Vulkan remains the optimal backend
- ROCm override (HSA_OVERRIDE_GFX_VERSION) may still work but unvalidated

### For ROCm Support

**Option 1: Wait (Recommended)**
- Monitor ROCm/TheRock releases
- Wait for "Release Ready" status
- Continue using Vulkan (105.6 TPS is excellent)

**Option 2: Build from Source (Advanced)**
```bash
# Build ROCm components with gfx1151 target
git clone https://github.com/ROCm/TheRock.git
cd TheRock
# Edit build configs to enable gfx1151
./build.sh
```
- ⚠️ Requires significant build time
- ⚠️ No guarantee of functionality
- ⚠️ Must override HSA_GFX_VERSION

**Option 3: Use Windows (Alternative)**
- ROCm Windows support shows gfx1151 as "Release Ready" in tables
- Windows ROCm stack more mature for consumer GPUs
- Not applicable to Linux users

---

## Conclusion

**Fact**: Ubuntu 26.04 LTS + Linux Kernel 7.0 are released and excellent for Strix Halo hardware.  
**Fact**: ROCm support for gfx1151 remains **not production-ready**.

**Verdict**: The infrastructure is in place, but AMD has not validated ROCm on gfx1151. The "unlock" requires AMD engineering resources, not just a newer kernel.

**Action**: 
1. ✅ Upgrade to Ubuntu 26.04 LTS for better hardware support
2. ⏳ Continue using Vulkan (optimal for now)
3. 👂 Follow ROCm/TheRock releases for gfx1151 "Release Ready" announcement
