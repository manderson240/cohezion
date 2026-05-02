# V-Model Systems Engineering for Tri-Compute Phase Connections

**V-Model Application**: Systems engineering lifecycle for heterogeneous compute orchestration

```
                    Requirements Analysis
                           |
                    System Design
                       /       \
                 /               \
            /                       \
    Architecture Design      Acceptance Testing
          |                           |
    Module Design            System Testing
          |                           |
    Unit Design         Integration Testing
          |                           |
   Implementation   ←────────→   Unit Testing
          |                           |
          └────────── Validation ───┘
```

---

## Left Side: Decomposition

### Level 1: Requirements Analysis
**Stakeholder Needs** → **System Requirements**

| ID | Requirement | Priority | Verification Method |
|----|-------------|----------|---------------------|
| R1.1 | Use all three AMD compute units (NPU, iGPU, CPU) | Critical | Architecture review |
| R1.2 | Execute 6-phase experimental framework | Critical | System test |
| R1.3 | Latency < 200ms for NPU inference | High | Performance test |
| R1.4 | Throughput > 100 TPS for iGPU simulation | High | Benchmark |
| R1.5 | Fault tolerance and error recovery | Medium | Fault injection |

### Level 2: System Design
**System Requirements** → **Component Specification**

**System**: Tri-Compute Phase Connection Orchestrator

**Subsystems**:
1. **NPU Inference Subsystem** (XDNA2)
2. **iGPU Simulation Subsystem** (Vulkan)
3. **CPU Orchestration Subsystem** (Zen 5)
4. **Integration & Communication Layer**
5. **Monitoring & Validation Layer**

**Interfaces**:
```
NPU ←──REST/HTTP──→ CPU ←──Shared Memory──→ iGPU
 ↓                                              ↓
Inference                                  Simulation
Results                                      Results
 ↓                                              ↓
└──────────→ Validation ←──────────────────────┘
```

### Level 3: Architecture Design
**Component Specification** → **Software Architecture**

**Architecture Pattern**: **Pipes and Filters** with **Broker**

```
┌─────────────────────────────────────────────────────────┐
│                   CPU Orchestrator                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Scheduler  │→ │   Broker     │→ │   Validator  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
           │                            ↑
           ↓                            │
    ┌──────────────┐            ┌──────────────┐
    │ NPU Worker   │            │ iGPU Worker  │
    │ (Port 8004)  │            │ (Vulkan)     │
    └──────────────┘            └──────────────┘
```

### Level 4: Module Design
**Software Architecture** → **Module Interfaces**

**Module: NPUInferenceEngine**
```python
class NPUInferenceEngine:
    """NPU (XDNA2) inference module."""
    
    # Input: prompt (str), max_tokens (int)
    # Output: response (str), latency_ms (float)
    # Exception: NPUGeneratedResponse, NPUTimeoutError
    async def infer(self, prompt: str, max_tokens: int = 256) -> str:
        ...
    
    # Input: phase (int), previous_results (dict)
    # Output: params (dict)
    def generate_experiment_params(self, phase: int, ...) -> dict:
        ...
```

**Module: iGPUSimulationEngine**
```python
class iGPUSimulationEngine:
    """iGPU (Vulkan) simulation module."""
    
    # Input: agents (list), n_steps (int)
    # Output: evolved_agents (list)
    def simulate_flume_batch(self, agents: list, n_steps: int) -> list:
        ...
    
    # Input: positions (ndarray), masses (ndarray), dt (float)
    # Output: forces (ndarray)
    def nbody_gravity(self, positions, masses, dt) -> np.ndarray:
        ...
    
    # Input: b_field (ndarray), velocity (ndarray), dt (float)
    # Output: updated_b (ndarray)
    def mhd_field_update(self, b_field, velocity, dt) -> np.ndarray:
        ...
```

**Module: CPUOrchestrationEngine**
```python
class CPUOrchestrationEngine:
    """CPU (Zen 5) orchestration module."""
    
    # Input: phase (ExperimentPhase), previous_results (dict)
    # Output: tasks (list[ComputeTask])
    def schedule_phase(self, phase, previous_results) -> list:
        ...
    
    # Input: phase_results (list[ComputeTask])
    # Output: aggregated (dict)
    def aggregate_results(self, phase_results) -> dict:
        ...
```

### Level 5: Unit Design
**Module Interfaces** → **Implementation Specification**

**Unit: ComputeTask Data Structure**
```python
@dataclass
class ComputeTask:
    task_id: str      # Format: "P{phase_id}_{compute_unit}_{sequence}"
    task_type: str    # Enum: "npu", "igpu", "cpu"
    payload: dict     # Serialization required
    priority: int     # 0 (high) to 9 (low)
    created_at: float # time.time()
    started_at: Optional[float]
    completed_at: Optional[float]
    result: Any
    error: Optional[str]
```

**Unit: ExperimentPhase Data Structure**
```python
@dataclass
class ExperimentPhase:
    phase_id: int           # 0-5 for phase connections
    name: str               # Human-readable
    npu_workload: Callable  # Type: (dict) -> dict
    igpu_workload: Callable # Type: (dict) -> list
    cpu_workload: Callable  # Type: (dict) -> dict
    dependencies: list[int] # Phase IDs that must complete first
    status: str             # "pending", "running", "completed", "failed"
```

---

## Right Side: Integration & Verification

### Level 5: Unit Testing
**Module Implementation** ←→ **Unit Verification**

| Module | Unit Test | Acceptance Criteria | Status |
|--------|-----------|---------------------|--------|
| ComputeTask | `test_task_tracks_timing` | times accurate | ⬜ |
| | `test_task_stores_result` | result persisted | ⬜ |
| | `test_task_stores_errors` | error captured | ⬜ |
| NPUInference | `test_npu_latency_under_100ms` | < 100ms | ⬜ |
| | `test_npu_generates_params` | valid JSON | ⬜ |
| iGPUSimulation | `test_igpu_throughput_over_100_tps` | > 100 TPS | ⬜ |
| | `test_igpu_simulates_flume` | batch processes | ⬜ |
| CPUOrchestration | `test_cpu_uses_full_cores` | 16 workers | ⬜ |
| | `test_cpu_schedules_correctly` | 3 tasks/phase | ⬜ |

**Test Implementation**:
```python
# File: tests/test_tri_compute_unit.py
def test_npu_latency_under_100ms():
    """Verify NPU meets latency requirement."""
    npu = NPUInferenceEngine()
    assert npu.latency_ms <= 100  # Design constraint
```

### Level 4: Integration Testing
**Module Assembly** ←→ **Interface Verification**

| Integration | Test | Acceptance Criteria | Status |
|-------------|------|---------------------|--------|
| NPU→CPU | `test_npu_results_reach_cpu` | data integrity | ⬜ |
| CPU→iGPU | `test_cpu_dispatches_to_igpu` | batch sent | ⬜ |
| iGPU→CPU | `test_igpu_returns_to_cpu` | results valid | ⬜ |
| All→Validation | `test_end_to_end_phase_execution` | full cycle | ⬜ |

**Test Implementation**:
```python
# File: tests/test_tri_compute_integration.py
@pytest.mark.asyncio
async def test_npu_cpu_integration():
    """NPU results properly reach CPU validator."""
    npu = NPUInferenceEngine()
    cpu = CPUOrchestrationEngine()
    
    params = await npu.infer("generate params")
    validated = cpu.validate(params)
    
    assert validated is not None
```

### Level 3: System Testing
**Subsystem Integration** ←→ **Requirements Verification**

| System Test | Requirement | Acceptance Criteria | Status |
|-------------|-------------|---------------------|--------|
| Phase 0 Complete | R1.3 R1.4 | NPU < 200ms, iGPU > 100 TPS | ⬜ |
| Phase 1-2 Coupling | R1.2 | Latent→Physical coupling measurable | ⬜ |
| Phase 3 MHD | R1.2 | Magnetic field divergence < 1e-6 | ⬜ |
| Phase 4 SWIFT | R1.2 | IC generation successful | ⬜ |
| Phase 5 Unified | R1.1 | All three compute units utilized | ⬜ |

**Test Implementation**:
```python
# File: tests/test_tri_compute_system.py
@pytest.mark.asyncio
async def test_phase_0_baseline_system():
    """Phase 0 meets all system requirements."""
    results = await run_phase_0()
    
    assert results["npu_latency_ms"] < 200
    assert results["igpu_throughput_tps"] > 100
```

### Level 2: Validation Testing
**System Validation** ←→ **Stakeholder Needs**

| Validation Activity | Stakeholder Need | Success Criteria | Status |
|--------------------|-----------------|------------------|--------|
| Performance Review | "Fast experimentation" | < 30 min/phase | ⬜ |
| Resource Audit | "Use all hardware" | > 90% utilization each | ⬜ |
| Science Validation | "Meaningful cosmology" | SWIFT runs complete | ⬜ |
| Reproducibility | "Trust results" | 3/3 runs identical | ⬜ |

### Level 1: Acceptance Testing
**System Acceptance** ←→ **Requirements Analysis**

| Acceptance Test | Requirement ID | Criteria | Status |
|-----------------|----------------|----------|--------|
| Tri-Compute Pipeline | R1.1 | All 3 units active in single run | ⬜ |
| Phase Completion | R1.2 | All 6 phases execute | ⬜ |
| NPU Response | R1.3 | < 200ms sustained | ⬜ |
| iGPU Throughput | R1.4 | > 100 TPS sustained | ⬜ |
| Error Recovery | R1.5 | Continues after simulated fault | ⬜ |

---

## V-Model Traceability Matrix

| Requirement | Design | Code | Unit Test | Integration | System | Acceptance |
|-------------|--------|------|-----------|-------------|--------|------------|
| R1.1 Tri-Compute | Architecture | 3 engines | ⬜ | ⬜ | ⬜ | ⬜ |
| R1.2 6 Phases | System Design | Phase classes | ⬜ | ⬜ | ⬜ | ⬜ |
| R1.3 NPU Latency | Module Design | latency_ms attr | ⬜ | ⬜ | ⬜ | ⬜ |
| R1.4 iGPU Throughput | Module Design | throughput_tps attr | ⬜ | ⬜ | ⬜ | ⬜ |
| R1.5 Fault Tolerance | Error Handling | try/except | ⬜ | ⬜ | ⬜ | ⬜ |

---

## Implementation Order (V-Model)

### Phase 1: Requirements & Design (Left Side - Top)
1. ✅ Requirements Analysis (Stakeholder needs captured)
2. ✅ System Design (3-subsystem architecture)
3. ✅ Module Design (Interface specifications)
4. ✅ Unit Design (Data structures)

### Phase 2: Implementation (Bottom)
5. ⬜ Unit Implementation (write code to pass tests)
6. ⬜ Module Implementation (integrate units)
7. ⬜ Subsystem Implementation (integrate modules)
8. ⬜ System Implementation (full orchestrator)

### Phase 3: Verification (Right Side - Bottom Up)
9. ⬜ Unit Testing (make existing tests pass)
10. ⬜ Integration Testing (verify interfaces)
11. ⬜ System Testing (verify requirements)
12. ⬜ Validation Testing (stakeholder review)
13. ⬜ Acceptance Testing (final sign-off)

---

## Current Status

```
Requirements Analysis    ✅ Complete
System Design          ✅ Complete  
Architecture Design    ✅ Complete
Module Design          ✅ Complete
Unit Design            ✅ Complete
Unit Implementation    ⬜ Starting
Unit Testing           ⬜ Starting
Integration Testing    ⬜ Not Started
System Testing         ⬜ Not Started
Validation             ⬜ Not Started
Acceptance             ⬜ Not Started
```

**Next Actions**:
1. Write failing unit tests (TDD)
2. Implement to make tests pass
3. Integrate modules
4. Verify system meets requirements

**Ready to proceed with Phase 2: Implementation?**
