# Experimental Framework: Phase Connections with Local Inference

**Objective**: Use local inference (AMD GPU) to execute experiments connecting FLUME, EVO, MHD, and SWIFT physics layers.

---

## Phase Architecture

```
Phase 0: Baseline Local Inference
    ↓
Phase 1: FLUME Latent Space Dynamics
    ↓
Phase 2: Agentic EVO Coupling
    ↓
Phase 3: MHD Plasma Physics
    ↓
Phase 4: SWIFT Cosmological Integration
    ↓
Phase 5: Unified Observations
```

Each phase uses **local inference** (Lemonade on AMD GPU) to:
1. Generate configurations/parameters
2. Execute simulations
3. Analyze results
4. Feed forward to next phase

---

## Phase 0: Baseline Local Inference

**Goal**: Establish optimal inference parameters for experiment orchestration.

**Experiments**:

### Exp 0.1: Inference Latency Benchmark
```python
# Use optimized AMD settings
configs = [
    {"concurrency": 1, "backend": "vulkan"},
    {"concurrency": 4, "backend": "vulkan"},
    {"concurrency": 4, "backend": "vulkan", "env": "RADV_PERFTEST=aco,gpl"},
]

for config in configs:
    latency = benchmark_inference(config)
    throughput = measure_tokens_per_sec(config)
    log(f"Config {config}: {latency}ms, {throughput} TPS")
```

**Metrics**:
- Latency: TTFT (time to first token)
- Throughput: TPS at optimal concurrency
- Stability: Variance across 100 calls

**Local Inference Role**: Determine fastest configuration for parameter generation.

---

## Phase 1: FLUME Latent Space Dynamics

**Goal**: Validate HIHO physics and latent coherence evolution.

**Experiments**:

### Exp 1.1: HIHO Convergence Study
```python
# Generate 100 random initial latent vectors
initial_vectors = local_inference.generate(
    prompt="Generate diverse 256D latent vectors for EVO initialization",
    n=100,
    max_tokens=256
)

# Evolve each with HIHO dynamics
results = []
for z0 in initial_vectors:
    trajectory = []
    z = z0
    for step in range(1000):
        z = hiho_step(z, damping=0.05)
        coherence = compute_coherence(z)
        trajectory.append(coherence)
    results.append(trajectory)

# Analyze convergence rates
plot_coherence_vs_time(results)
```

**Metrics**:
- Convergence time to equilibrium (coherence ~0.5)
- Variance reduction over time
- Exotic vs standard divergence rates

### Exp 1.2: Latent Information Accumulation
```python
# Use local inference to score information content
for agent in evo_population:
    info_score = local_inference.evaluate(
        prompt=f"Rate information content of journey: {agent.journey}"
    )
    agent.information_content = info_score
```

**Metrics**:
- Information growth rate
- Correlation with physical state changes
- Entropy of latent trajectories

**Local Inference Role**: 
- Generate diverse initial conditions
- Score information content
- Validate trajectory quality

---

## Phase 2: Agentic EVO Coupling

**Goal**: Measure bidirectional coupling between latent and physical spaces.

**Experiments**:

### Exp 2.1: Latent→Physical Influence
```python
# Fix physical ICs, vary latent coherence
physical_state = fixed_ic()
for coherence_target in [0.1, 0.3, 0.5, 0.7, 0.9]:
    latent = generate_latent_with_coherence(coherence_target)
    # Run physical simulation
    physical_evolution = nbody_step(latent, physical_state, dt=0.01, n=100)
    
    # Local inference analyzes coupling
    coupling_strength = local_inference.score(
        prompt=f"How much does coherence={coherence_target} affect physical evolution?"
    )
    results[coherence_target] = coupling_strength
```

### Exp 2.2: Physical→Latent Feedback
```python
# Fix latent state, vary physical environment
latent_state = fixed_latent()
for environment in ['vacuum', 'gas_cloud', 'dense_cluster']:
    physical = setup_environment(environment)
    # Observe latent drift under physical stress
    latent_evolution = simulate_stress_feedback(latent, physical)
    
    # Local inference validates
    feedback_valid = local_inference.check(
        prompt=f"Does {environment} plausibly affect latent state?"
    )
```

**Metrics**:
- Coupling coefficient magnitude
- Directionality (latent→physical vs physical→latent)
- Exotic agent divergence from standard

**Local Inference Role**:
- Generate physical configurations
- Score coupling quality
- Validate physical plausibility

---

## Phase 3: MHD Plasma Physics

**Goal**: Validate magnetic field generation and Alfven wave coupling.

**Experiments**:

### Exp 3.1: Latent→B-Field Generation
```python
for agent in evo_agents:
    # Local inference generates latent trajectory
    trajectory = local_inference.generate_trajectory(
        prompt=f"Generate journey for agent with type={agent.type}"
    )
    
    # Compute B-field from latent
    agent.generate_magnetic_field()
    
    # Measure
    b_magnitude = np.linalg.norm(agent.magnetic_state.B_field)
    
    # Correlation: information_content ↔ |B|
    plot_correlation(agent.information_content, b_magnitude)
```

### Exp 3.2: Alfven Wave Propagation
```python
# Set up chain of agents along B-field line
agents = create_chain(n=20, spacing=10.0)
agents[0].perturb_latent(amplitude=0.5)  # Initial pulse

# Evolve and measure propagation
for step in range(100):
    system.step()
    
    # Local inference tracks wavefront
    wavefront = local_inference.detect(
        prompt=f"Locate coherence perturbation in agent chain at step {step}"
    )
    
    # Compare to Alfven speed prediction
    v_alfven = compute_alfven_speed(agents)
    expected_position = step * dt * v_alfven
    
    measure_propagation_accuracy(wavefront, expected_position)
```

### Exp 3.3: Magnetic Reconnection Events
```python
# Create anti-parallel field configurations
pair_counter = 0
for i, agent_i in enumerate(agents):
    for j, agent_j in enumerate(agents[i+1:], start=i+1):
        if check_reconnection_trigger(agent_i, agent_j):
            # Local inference witnesses event
            reconnection_report = local_inference.describe(
                prompt=f"Describe magnetic reconnection between {agent_i.id} and {agent_j.id}"
            )
            
            # Measure energy release
            energy_before = compute_total_energy([agent_i, agent_j])
            agent_i.magnetic_reconnection(agent_j)
            energy_after = compute_total_energy([agent_i, agent_j])
            
            log_reconnection_event(reconnection_report, energy_before - energy_after)
            pair_counter += 1
```

**Metrics**:
- Latent-B-field correlation coefficient
- Alfven wave propagation speed accuracy
- Reconnection frequency per timestep
- Energy conservation (should improve with DivB cleaning)

**Local Inference Role**:
- Generate magnetic field configurations
- Witness and describe reconnection events
- Track wave propagation
- Validate energy conservation

---

## Phase 4: SWIFT Cosmological Integration

**Goal**: Export EVO states to SWIFT and run cosmological simulations.

**Experiments**:

### Exp 4.1: IC Generation Validation
```python
# Generate EVO population
evos = generate_evo_population(n=1000)

# Local inference curates population
selected_evos = local_inference.select(
    prompt="Select most interesting EVOs for cosmological simulation",
    candidates=evos,
    n=100
)

# Export to SWIFT ICs
system = AgenticMHDSystem(evos=selected_evos)
system.generate_swift_ics("/tmp/evos_cosmology.hdf5")

# Validate with local inference
validation = local_inference.check(
    prompt="Validate HDF5 ICs for SWIFT compatibility"
)
```

### Exp 4.2: Small-Scale SWIFT Test
```python
# Run SWIFT on small subset
result = subprocess.run([
    "mpirun", "-np", "4", "./swift",
    "--self-gravity", "--hydro", "--mhd",
    "/tmp/evos_cosmology.hdf5"
], capture_output=True)

# Local inference analyzes
swift_output = local_inference.analyze(
    prompt=f"Analyze SWIFT output: {result.stdout}"
)

# Compare EVO-predicted vs SWIFT-computed
divergence = compare_trajectories(evo_journeys, swift_particle_data)
```

### Exp 4.3: Parameter Sweep
```python
# Use local inference to suggest parameters
for run in range(10):
    params = local_inference.suggest(
        prompt="Suggest cosmological parameters for next SWIFT run",
        history=previous_results
    )
    
    # Configure SWIFT
    configure_swift(params)
    
    # Execute
    run_swift()
    
    # Evaluate
    result = evaluate_cosmology()
    local_inference.record(params, result)
```

**Metrics**:
- IC generation success rate
- SWIFT completion without crashes
- Trajectory divergence (EVO vs SWIFT)
- Cosmological metric accuracy (power spectrum, halo mass function)

**Local Inference Role**:
- Curate EVO populations
- Validate IC formats
- Analyze SWIFT outputs
- Suggest parameter sweeps

---

## Phase 5: Unified Observations

**Goal**: Integrate all phases into unified analysis framework.

**Experiments**:

### Exp 5.1: Cross-Phase Correlation
```python
# Build correlation matrix across all phases
correlations = {
    "latent_coherence ↔ physical_density": compute_correlation(
        phase1_data.coherence, phase2_data.density
    ),
    "information_content ↔ b_field_strength": compute_correlation(
        phase1_data.info_content, phase3_data.b_magnitude
    ),
    "mhd_divergence ↔ cosmology_accuracy": compute_correlation(
        phase3_data.div_b_error, phase4_data.metric_error
    ),
    "evo_journey_length ↔ halo_mass": compute_correlation(
        phase2_data.journey_length, phase4_data.halo_mass
    ),
}

# Local inference interprets
unified_theory = local_inference.synthesize(
    prompt=f"Synthesize unified theory from correlations: {correlations}"
)
```

### Exp 5.2: Predictive Validation
```python
# Train predictive model using local inference as oracle
train_data = collect_all_phases()
model = local_inference.train_predictor(
    prompt="Train model to predict phase N+1 from phase N",
    data=train_data
)

# Test extrapolation
for phase_sequence in test_sequences:
    predicted = model.predict(phase_sequence[:-1])
    actual = phase_sequence[-1]
    accuracy = evaluate_prediction(predicted, actual)
```

### Exp 5.3: Anomaly Detection
```python
# Use local inference to identify anomalies across phases
for sample in all_phase_data:
    anomaly_score = local_inference.score_anomaly(
        prompt=f"Is this sample anomalous? {sample}"
    )
    if anomaly_score > threshold:
        flag_for_investigation(sample)
```

**Metrics**:
- Cross-phase correlation strengths
- Prediction accuracy on held-out data
- Anomaly detection precision/recall
- Unified theory coherence score

**Local Inference Role**:
- Synthesize unified frameworks
- Train cross-phase predictors
- Detect anomalies
- Generate hypotheses

---

## Experiment Orchestration

### Automated Pipeline

```python
class PhaseConnectionOrchestrator:
    def __init__(self):
        self.inference = LocalInferenceEngine(
            model="DeepSeek-R1-0528-Qwen3-8B-Q4_1",
            concurrency=4,
            optimized=True
        )
        self.results = {}
    
    def run_experiment(self, phase: int, exp_id: str):
        config = load_config(phase, exp_id)
        
        # Local inference generates parameters
        params = self.inference.generate_params(config)
        
        # Execute experiment
        if phase == 0:
            result = self.run_baseline(params)
        elif phase == 1:
            result = self.run_flume_experiment(params)
        elif phase == 2:
            result = self.run_evo_experiment(params)
        elif phase == 3:
            result = self.run_mhd_experiment(params)
        elif phase == 4:
            result = self.run_swift_experiment(params)
        elif phase == 5:
            result = self.run_unified_analysis(params)
        
        # Local inference validates
        validation = self.inference.validate(result, config)
        
        self.results[f"P{phase}_{exp_id}"] = {
            "params": params,
            "result": result,
            "validation": validation
        }
        
        return result
    
    def run_full_suite(self):
        for phase in range(6):
            for exp in self.get_experiments_for_phase(phase):
                print(f"Running Phase {phase}, Experiment {exp}...")
                self.run_experiment(phase, exp)
```

### Resource Requirements

| Phase | Duration | GPU Utilization | Inference Calls |
|-------|----------|-----------------|-------------------|
| 0 | 1 hour | High | 100 |
| 1 | 2 hours | Medium | 500 |
| 2 | 4 hours | Medium | 1000 |
| 3 | 6 hours | High | 2000 |
| 4 | 12 hours | Low (CPU) | 500 |
| 5 | 2 hours | High | 1000 |

**Total**: ~27 hours, ~5100 inference calls

---

## Success Criteria

### Phase Completion
- [ ] Phase 0: Baseline latency < 200ms TTFT
- [ ] Phase 1: HIHO convergence within 1000 steps
- [ ] Phase 2: Measurable coupling coefficient > 0.1
- [ ] Phase 3: Alfven speed prediction within 10%
- [ ] Phase 4: Successful SWIFT completion on 1000 particles
- [ ] Phase 5: Cross-phase correlation with R² > 0.5

### Integration
- [ ] Automated pipeline runs end-to-end
- [ ] Local inference quality > 80% validation rate
- [ ] Reproducible results across 3 runs

---

## Next Steps

1. **Validate Phase 0**: Confirm inference benchmark runs successfully
2. **Curate Experiments**: Select specific parameter ranges
3. **Implement Orchestrator**: Build automated pipeline
4. **Run Phase 1-2**: Validate FLUME-EVO coupling
5. **Scale to Phase 3-4**: MHD and SWIFT integration
6. **Synthesize Phase 5**: Unified analysis

**Ready to begin Phase 0?** Start with baseline inference benchmark.
