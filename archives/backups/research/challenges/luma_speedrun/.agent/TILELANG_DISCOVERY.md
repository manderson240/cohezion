# 🎯 MAJOR DISCOVERY: TileLang Supports MI355X!

**Time:** 3:00 AM EDT (T+7h)  
**Discovery:** TileLang intermediate language now supports AMD MI355X

---

## 🔍 What is TileLang?

TileLang is a Python-based intermediate language for tile-based GPU kernel optimization from MIT.

**Key Features:**
- Higher-level than CK-Tile (C++)
- Cleaner than Triton
- Automatic layout inference
- Proven AMD MI300X performance

---

## ✅ MI355X Support Confirmed

Recent PRs (Jan-Feb 2026):
- **PR #1718**: MI350/MI355 FP8 support (`__hip_fp8_e4m3`)
- **PR #1878**: gfx950 CI and MFMA 16x16x32 instructions
- **160KB LDS**: Uses MI355X's increased shared memory

---

## 🎯 Impact on Competition

| Kernel | Lines | vs Triton | vs CK-Tile |
|--------|-------|-----------|------------|
| **MLA** | ~80 | FlashMLA parity | 500+ in CUTLASS |
| **GEMM** | ~100 | Excellent | Complex |
| **MoE** | Custom | Possible | Would need custom |

---

## ⚠️ Integration Considerations

### Pros
- ✅ Much faster development than hand-written HIP
- ✅ Automatic layout inference (no MFMA register puzzles)
- ✅ Python productivity
- ✅ Actively maintained (5.5k GitHub stars)

### Cons
- ⚠️ Popcorn runner compatibility unknown
- ⚠️ May need TileLang runtime in submission
- ⚠️ MXFP4 support would need custom handling
- ⚠️ JIT compilation time constraints

---

## 📊 Recommendation

| Use Case | Verdict |
|----------|---------|
| **Research/Rapid Prototyping** | ✅ **Strong Yes** |
| **MLA kernel** | ✅ **Yes** - Showcase feature |
| **Direct submission** | ⚠️ **Maybe** - Test runner first |
| **Next competition** | ✅ **High potential** |

---

## 🔗 Resources

- **GitHub**: https://github.com/tile-ai/tilelang
- **Paper**: arXiv:2504.17577
- **Example**: `examples/deepseek_mla/`

---

**This discovery could be game-changing for future iterations!**
