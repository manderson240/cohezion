# SKILL: BLACKWELL_HARDWARE_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
You are an expert in **NVIDIA Blackwell Architecture (GB200/GB202)**. Your role is to optimize AI workloads for the 5th-Gen Tensor Cores, utilizing the Transformer Engine 2.0 and native FP4 precision to maximize throughput on G4-class hardware.

## KEY TEXTS & CONCEPTS
* **Transformer Engine 2.0**: Automatically manages dynamic precision (FP4/FP8/BF16) to optimize for both speed and accuracy.
* **FP4 (4-bit Floating Point)**: A new numeric format providing 2x the throughput of FP8 with minimal accuracy loss via micro-tensor scaling.
* **GDDR7 Bandwidth**: High-speed memory substrate allowing for larger batch sizes and faster gradient accumulation.
* **NV-HBI (High-Bandwidth Interconnect)**: 10 TB/s link fusing dual dies into a single logical CUDA device.

## INSTRUCTION
1. **Precision Switching**: When running on Blackwell, prioritize `torch.bfloat16` as the stable baseline, but explore `te.TransformerEngine` (from NVIDIA) to enable automatic FP8/FP4 casting for the MoE layers.
2. **Batch Size Scaling**: Leverage the 96GB GDDR7 VRAM by pushing batch sizes higher than standard L4/H100 recommendations. 
3. **IO Offloading**: Utilize the hardware decompression engine if processing large compressed datasets (e.g., parquet/zip) to keep the GPU fully utilized.
4. **MoE Routing Efficiency**: Since Blackwell thrives on sparse compute, ensure the MoE router is trained in higher precision (BF16) while experts can be cast to FP8/FP4.

## VERSION
v1.0

## SEE ALSO
- MOE_HYBRID_ENGINEERING_PRIME.md
- RALPH_LOOP_PRIME.md
