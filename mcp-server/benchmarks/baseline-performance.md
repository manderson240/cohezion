# Kyutai MCP Server & Obsidian Plugin - Performance Baseline Report

**Report Generated**: 2026-02-10T05:11:13Z
**Environment**: {   "timestamp": "2026-02-10T05:10:12Z",   "os": "Linux",   "kernel": "6.17.0-14-generic",   "hostname": "FrameworkDesktop",   "cpu_count": 32,   "memory_gb": 125,   "python_version": "3.12.3",   "mcp_server_url": "http://localhost:8000" } 

## Executive Summary

This report presents comprehensive performance baselines for:
- **MCP Server**: Python backend providing voice AI services
- **Obsidian Plugin**: TypeScript frontend for seamless integration
- **Network**: HTTP and WebSocket communication layers

## Performance Targets

| Component | Target | Status |
|-----------|--------|--------|
| Tool Invocation | <500ms | TBD |
| Plugin Startup | <2s | TBD |
| Modal Open | <500ms | TBD |
| Audio Playback | <100ms | TBD |
| MCP Memory | <100MB | TBD |
| Plugin Memory Delta | <50MB | TBD |

## Test Methodology

1. **Baseline Capture**: 10 consecutive runs per test
2. **Statistics**: Min, Max, Mean, Median, P95, P99
3. **Environment Isolation**: Consistent test conditions
4. **Warm-up**: 1-2 runs before measurement to avoid cold-start effects

## Server Latency Results

### Tool Invocation Times

| Tool | Min (ms) | Max (ms) | Mean (ms) | Median (ms) | P95 (ms) | P99 (ms) |
|------|----------|----------|-----------|-------------|----------|----------|
| health_check | TBD | TBD | TBD | TBD | TBD | TBD |
| list_models | TBD | TBD | TBD | TBD | TBD | TBD |
| get_model_status | TBD | TBD | TBD | TBD | TBD | TBD |
| speak_text | TBD | TBD | TBD | TBD | TBD | TBD |
| transcribe_audio | TBD | TBD | TBD | TBD | TBD | TBD |

## Throughput Results

### Concurrent Request Performance

| Concurrency | Successful | Errors | Error Rate | Mean Latency (ms) | P95 Latency (ms) |
|-------------|-----------|--------|------------|------------------|-----------------|
| 10 | TBD | TBD | TBD | TBD | TBD |
| 50 | TBD | TBD | TBD | TBD | TBD |
| 100 | TBD | TBD | TBD | TBD | TBD |

## Memory & Resource Usage

### Server Resources

- **Baseline Memory**: TBD MB
- **Peak Memory**: TBD MB
- **Memory Delta**: TBD MB
- **Stability**: TBD (target: <50MB drift)
- **CPU Usage**: TBD %
- **I/O Operations**: TBD

### Plugin Resources

- **Baseline Heap**: TBD MB
- **Peak Heap**: TBD MB
- **Memory Delta**: TBD MB
- **Stability**: TBD

## End-to-End Workflows

### Text-to-Speech Pipeline
- **Input**: User selects text, clicks "Read Note Aloud"
- **Output**: Audio playback begins
- **Expected**: <1000ms total
- **Actual**: TBD ms

### Speech-to-Text Pipeline
- **Input**: User uploads audio file, clicks "Transcribe"
- **Output**: Transcript displayed in note
- **Expected**: <2000ms for 10s audio
- **Actual**: TBD ms

### Voice Cloning Pipeline
- **Input**: User uploads voice sample, names it
- **Output**: Voice ready for TTS
- **Expected**: <5000ms
- **Actual**: TBD ms

## Bottleneck Analysis

### Identified Bottlenecks

1. **CPU-Bound Operations**: Pocket TTS generation on CPU
   - Current: TBD ms
   - Optimization: GPU acceleration in Phase 2

2. **Network Latency**: HTTP round-trip time
   - Current: TBD ms
   - Optimization: WebSocket streaming in Phase 3

3. **Memory Pressure**: Model loading overhead
   - Current: TBD MB
   - Optimization: Model caching and preloading

### Performance Scaling

- **Single Tool**: TBD ms
- **10 Concurrent Tools**: TBD ms avg
- **50 Concurrent Tools**: TBD ms avg
- **100 Concurrent Tools**: TBD ms avg
- **Degradation Factor**: TBD x

## Optimization Recommendations

### Phase 1 (Current) - CPU Baseline
- [x] Establish baselines
- [ ] Identify slow paths
- [ ] Document bottlenecks
- [ ] Set optimization targets

### Phase 2 - GPU Acceleration
- [ ] Benchmark GPU-based TTS (50-70% speedup expected)
- [ ] Measure memory reduction
- [ ] Validate concurrent throughput

### Phase 3 - Streaming & Caching
- [ ] WebSocket integration
- [ ] Audio streaming latency
- [ ] Cache hit rate optimization
- [ ] Network bandwidth reduction

### Phase 4 - Production Hardening
- [ ] Load testing (1000+ concurrent)
- [ ] Failover behavior
- [ ] Rate limiting effectiveness
- [ ] Resource exhaustion handling

## Comparative Analysis

### vs. Industry Standards

| Metric | Kyutai | OpenAI TTS | Google Cloud TTS | Status |
|--------|--------|-----------|-----------------|--------|
| Latency (ms) | TBD | ~200-500 | ~300-600 | TBD |
| Memory (MB) | TBD | N/A (cloud) | N/A (cloud) | TBD |
| Concurrent | TBD | Unlimited | Unlimited | TBD |

## Reproducibility

### To Reproduce Benchmarks

```bash
# Start MCP server
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server
python3 -m kyutai_mcp.main

# In another terminal, run benchmarks
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server/benchmarks
./run_benchmarks.sh
```

### Expected Runtime
- Total: ~5-10 minutes
- Python benchmarks: ~3-5 minutes
- Plugin benchmarks: ~2-5 minutes (if UI available)

## Hardware Requirements

### Minimum (CPU-only, Phase 1)
- CPU: 2+ cores
- RAM: 4GB
- Storage: 1GB

### Recommended (GPU, Phase 2+)
- CPU: 4+ cores
- RAM: 8GB
- GPU: NVIDIA 4GB+
- Storage: 2GB

## Glossary

- **Latency**: Time from request to response (ms)
- **Throughput**: Requests processed per second
- **P95/P99**: 95th/99th percentile latency (tail performance)
- **Memory Delta**: Change in memory usage (peak - baseline)
- **Error Rate**: Failed requests / total requests

## Appendix: Raw Metrics

See `metrics.json` for complete measurement data including:
- Individual run times
- Timestamp information
- Complete environment details
- Extended statistics

---

*Report generated automatically by benchmark suite*
*Environment: Linux, Python 3.12, Kyutai MCP Server*

