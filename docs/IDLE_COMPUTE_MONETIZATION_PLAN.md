# Idle Compute Monetization Plan

## System Specifications
| Resource | Specification | Monetization Potential |
|----------|---------------|------------------------|
| **CPU** | AMD RYZEN AI MAX+ 395 (16c/32t) | High - AI inference, validation |
| **GPU** | AMD Radeon 8060S (integrated) | Medium - Limited discrete GPU tasks |
| **RAM** | 125Gi total (~59Gi available) | High - LLM inference, node ops |
| **Storage** | 1.7TB ZFS (1.4TB avail) | High - Node storage, IPFS |
| **VMs** | 10 possible, 1 exists (ubuntu-guest - delete) | Scale monetization workers |

---

## Priority 1: Blockchain Validation Nodes (Highest ROI)

### Recommended Networks

| Network | APY | Min Stake | Hardware Fit | Priority |
|---------|-----|-----------|--------------|----------|
| **Cosmos (ATOM)** | ~15% | 1 ATOM | ✅ Perfect (low requirements) | 🔴 HIGH |
| **Polkadot (DOT)** | 10-12% | Variable | ✅ Good (16+ cores) | 🔴 HIGH |
| **Ethereum** | 4-7% | 32 ETH (~$120k) | ✅ Excellent | 🟡 Capital-intensive |
| **Solana** | 2-7% | None (delegated) | ⚠️ Needs NVMe tuning | 🟢 Medium |

### Docker Container Setup
```yaml
# docker-compose.validator.yml
version: '3.8'
services:
  cosmos-validator:
    image: cosmossdk/tendermint:latest
    cpus: 4
    mem_limit: 16G
    volumes:
      - cosmos-data:/data
    restart: unless-stopped
    
  polkadot-validator:
    image: parity/polkadot:latest
    cpus: 4
    mem_limit: 32G
    volumes:
      - polkadot-data:/polkadot
    restart: unless-stopped
```

---

## Priority 2: Distributed GPU/CPU Rental

### Platforms (CPU-focused for our specs)

| Platform | Resource | Token | Est. Monthly | Priority |
|----------|----------|-------|--------------|----------|
| **Akash Network** | CPU/Storage | AKT | $50-200 | 🔴 HIGH |
| **Flux** | CPU nodes | FLUX | $30-100 | 🟡 MEDIUM |
| **iExec** | CPU cycles | RLC | $20-80 | 🟡 MEDIUM |
| **Golem** | CPU tasks | GLM | $10-50 | 🟢 LOWER |

### Akash Provider Setup
```bash
# Install Akash provider
docker run -d \
  --name akash-provider \
  -v akash-keys:/keys \
  -e AKASH_NODE=https://rpc.akash.network:443 \
  akash/provider
```

---

## Priority 3: AI Inference / SLM Swarm Rental

### Leverage Our Unique Capability
We run **Ollama with local SLMs** (Gemma, Phi-3, Mistral). Monetize this:

| Approach | Description | Revenue Model |
|----------|-------------|---------------|
| **API Gateway** | Expose FastAPI for inference | Per-request pricing |
| **SaladCloud** | Join distributed AI network | Per-compute-hour |
| **Own Marketplace** | Cohezion Inference API | Subscription |

```python
# src/cohezion/monetization/inference_api.py
from fastapi import FastAPI
from cohezion.swarm import SmartRouter

app = FastAPI()
router = SmartRouter()

@app.post("/v1/inference")
async def inference(query: str, model: str = "auto"):
    # Route to cheapest available SLM
    result = await router.route_query(query, model)
    # Bill per 1K tokens
    return {"result": result, "tokens": result.tokens, "cost_usd": result.tokens * 0.0001}
```

---

## Priority 4: Storage/Bandwidth DePIN

| Platform | Resource | Token | Fit | Notes |
|----------|----------|-------|-----|-------|
| **Storj** | 1TB+ | STORJ | ✅ Have space | Stable income |
| **Filecoin** | 1TB+ | FIL | ✅ Have space | More setup |
| **Grass/Honeygain** | Bandwidth | Points | ✅ Passive | Low effort |

---

## Implementation Phases

### Phase 1: Quick Wins (Week 1)
1. Delete broken `ubuntu-guest` VM
2. Set up Cosmos validator container (~15% APY)
3. Install Akash provider for CPU rental
4. Join Grass network for passive bandwidth income

### Phase 2: Scale (Week 2-3)
1. Create 3-5 additional VMs for workload isolation
2. Add Polkadot validator if capital available
3. Deploy Cohezion Inference API for SLM monetization

### Phase 3: Optimize (Month 2+)
1. Use FLUME+QNS to analyze ROI per workload
2. Auto-scale containers based on demand
3. Democratic debate to select highest-yield opportunities

---

## Scaling Architecture
```
┌─────────────────────────────────────────────┐
│              HYPERVISOR (10 VMs max)        │
├─────────────────────────────────────────────┤
│  VM1: Cosmos       VM2: Polkadot            │
│  VM3: Akash        VM4: Inference API       │
│  VM5: Storj        VM6: Development         │
│  VM7-10: Reserved for scaling               │
├─────────────────────────────────────────────┤
│         Docker Swarm / Containerd           │
├─────────────────────────────────────────────┤
│  Container auto-scaling based on:           │
│  - Memory pressure (<70% threshold)         │
│  - CPU utilization (<80% threshold)         │
│  - Network demand                           │
└─────────────────────────────────────────────┘
```

---

## Estimated Monthly Revenue

| Source | Conservative | Optimistic |
|--------|--------------|------------|
| Cosmos Validator | $50 | $200 |
| Akash Provider | $50 | $200 |
| Inference API | $0 | $500 |
| Storage (Storj) | $20 | $50 |
| Bandwidth (Grass) | $5 | $20 |
| **TOTAL** | **$125** | **$970** |

---

## Safety Guardrails
1. **Memory Watchdog**: Never exceed 70% RAM for monetization
2. **Priority Queue**: Development work > Monetization tasks
3. **Container Limits**: Hard caps on CPU/RAM per container
4. **Protected Containers**: Never touch open notebooks containers

---

## Next Steps
1. ⏳ User approval of this plan
2. 🐳 Create Docker Compose for validators
3. 🔧 Delete ubuntu-guest VM, create fresh VMs
4. 📊 Set up monitoring dashboard (Marimo)
