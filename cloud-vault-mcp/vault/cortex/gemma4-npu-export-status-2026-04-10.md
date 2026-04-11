# Gemma 4 NPU Export - Current Status

**Date**: 2026-04-10
**Session**: post-hf-token-rocm-gfx1151-onnx-export

## Summary
Successfully established complete ONNX export pipeline for Gemma 4 family using HuggingFace token authentication. Quantization blocked by protobuf 2GB limit on large external data files.

## Working Infrastructure

### 1. HuggingFace Authentication ✅
- **Token**: `REDACTED_HF_TOKEN`
- **Status**: Valid and functional
- **Models accessible**: google/gemma-4-E2B-it, gemma-4-31B-it, etc.

### 2. Python Environment ✅
- **Location**: `/home/mike-anderson/gemma4-npu-conversion/venv/`
- **Python**: 3.14.3 (linuxbrew)
- **Key packages**:
  - torch: 2.11.0+cu130
  - transformers: 5.5.3
  - onnx: 1.21.0
  - onnxscript: latest

### 3. Export Pipeline ✅
**Script**: `export_gemma4_simple.py`
```python
# Key technique: use_cache=False to bypass DynamicCache
class ModelWrapper(torch.nn.Module):
    def forward(self, input_ids):
        outputs = self.model(input_ids=input_ids, use_cache=False)
        return outputs.logits
```

**Result** (google/gemma-4-E2B-it):
- ONNX file: 11 MB
- External data: 8.7 GB
- OPSET: 18
- Format: External tensor data (protobuf > 2GB)

## Blocked: NPU Quantization ❌

### AMD Quark
- **Path**: `/opt/ryzen-ai/bin/`
- **Python**: 3.12.3
- **Quark version**: 0.11.1
- **Error**: 
  ```
  google.protobuf.message.EncodeError: Failed to serialize proto
  # Occurs at ByteSize() check in ModelQuantizer
  ```

### Root Cause
External data format models cannot be serialized through protobuf's C API. AMD Quark's quantize_model() loads full model into memory then attempts ByteSize() check which fails for external data.

### Alternatives Considered
1. **ONNX Runtime quantize_static()** with use_external_data_format=True
   - Works for serialization
   - But may not produce NPU-optimized quantization
   
2. **Convert external data → internal**
   - Would require >10GB combined protobuf
   - Exceeds protobuf 2GB hard limit

3. **Use pre-quantized models**
   - Unsloth provides GGUF formats
   - AMD may provide pre-optimized ONNX

## Working Compute Backends

| Backend | Status | TPS | Models | Notes |
|---------|--------|-----|--------|-------|
| NPU (FLM) | ✅ Available | 75 | ≤4B | Gemma 3 4B tested |
| GPU Vulkan | ✅ Available | 100 | ≤31B | RADV GFX1151 |
| GPU ROCm | ❌ Blocked | - | - | Issue #6027 |
| Cloud | ✅ Available | 50 | Any | Ollama bridge |

## Recommended User Paths

### For Gemma 3 (4B): NPU
```bash
flm run gemma-3-4b-it
# 75 TPS, 15ms latency
```

### For Gemma 4 (Any): GPU Vulkan
```bash
llama-server -m gemma-4-E2B-it.gguf --port 8890
# 100 TPS, 131GB VRAM available
```

### For Quantization Research
```bash
cd ~/gemma4-npu-conversion/
source venv/bin/activate
python3 export_gemma4_simple.py  # Export
# Quantization: Blocked pending AMD/SDK updates
```

## Next Steps (When Unblocked)

1. **Monitor AMD Quark updates** for external data support
2. **Test smaller Gemma 4 variants** (if sub-2GB versions appear)
3. **Use GGUF → ONNX conversion** tools (if available)
4. **Leverage GPU Vulkan** for all Gemma 4 inference (current solution)

## Files in Conversion Directory
- `export_gemma4_simple.py` - Working PyTorch → ONNX export
- `quantize_gemma4_sdk.py` - AMD Quark quantizer (blocked)
- `quantize_large_model.py` - ONNX Runtime quantizer (untested)
- `GEMMA4_EXPORT_STATUS.md` - Detailed status
- `gemma4_e2b_export/` - Exported model files

## References
- HuggingFace token: `.env` file, HF_TOKEN variable
- Ryzen AI SDK: `/opt/ryzen-ai/`
- Conversion dir: `~/gemma4-npu-conversion/`
- Original summary: `GFX1151_HYBRID_STRATEGY_RESEARCH.md`
