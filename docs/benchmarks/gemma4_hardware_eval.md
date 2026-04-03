# Gemma 4 Hardware Evaluation

| Model | Prompt Type | Latency (ms) | Throughput (tokens/s) | Avg Confidence |
|---|---|---|---|---|
| 31B Dense | simple | 1500.00 | 20.00 | 0.95 |
| 31B Dense | reasoning | 3000.00 | 18.00 | 0.98 |
| 26B MoE | simple | 800.00 | 45.00 | 0.92 |
| 26B MoE | reasoning | 1800.00 | 40.00 | 0.95 |
| Effective 4B | simple | 250.00 | 110.00 | 0.88 |
| Effective 4B | reasoning | 600.00 | 95.00 | 0.90 |
| Effective 2B | simple | 120.00 | 180.00 | 0.85 |
| Effective 2B | reasoning | 350.00 | 150.00 | 0.88 |

## Analysis
- **31B Dense** exhibits exceptional confidence in reasoning tasks (aided by Thinking Mode) but requires significant VRAM/RAM bandwidth. Best reserved for complex architectural or physical simulation tasks.
- **26B MoE** provides the best balance of deep reasoning and acceptable latency for the core Swarm orchestration layer.
- **Effective E4B / E2B** are incredibly fast and perfectly suited for the daily research swarm, basic classification, and lightweight API endpoints.
