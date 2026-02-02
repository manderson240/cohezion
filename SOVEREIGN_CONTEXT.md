# SOVEREIGN CONTEXT
**Generated**: Sun Feb  1 04:18:08 PM EST 2026


## `src/cohezion/branding.py`
> Cohezion Branding API - The Single Source of Truth for the Nexus Identity.
- **class** `Colors`
  - *The Nexus Color Palette.*
- **class** `Identity`
- **class** `Motifs`
  - *ASCII Art and Text Motifs.*
- `def get_theme()`

## `src/cohezion/qftdhd/data/experiments/rigorous_benchmark.py`
> Rigorous Benchmark: QFTDHD Scalability Test (Parallelized)
- `def rosenbrock(x)`
- `def run_trial_sync(seed)`

## `src/cohezion/qftdhd/data/experiments/verify_qftdhd.py`
> QFTDHD Verification Experiment
- `def run_experiment()`

## `src/cohezion/qftdhd/data/experiments/grand_challenge.py`
> The Grand Challenge: QFTDHD vs Classical Optimization
- `def rosenbrock(x)`
- `def run_challenge()`

## `src/cohezion/viz/multiverse_dashboard.py`

## `src/cohezion/viz/metrics_dashboard.py`
- `def header()`
- `def load_data()`
- `def dashboard(data)`

## `src/cohezion/viz/manim_renderer.py`
> Manim Renderer - 3D animated visualization of the Universe Simulation.
- **class** `RenderConfig`
  - *Configuration for Manim rendering.*
- **class** `ManimRenderer`
  - *Render universe nodes as 3D Manim animations.*
- `def to_manim_config()`
- `def physics_to_visual(physics_state)`
- `def render_nodes(nodes, output_name, duration)`
- `def render_trajectory(trajectory, output_name)`

## `src/cohezion/viz/comparative_dashboard.py`

## `src/cohezion/viz/hypertools_renderer.py`
> HyperTools Renderer - Interactive high-dimensional data visualization.
- **class** `HyperToolsViz`
  - *High-dimensional data visualization using HyperTools.*
- `def plot_embeddings(embeddings, labels, colors, method, output_name, interactive)`
- `def animate_trajectory(trajectory, output_name, fps)`
- `def compare_embeddings(embedding_sets, set_labels, method, output_name)`
- `def init()`
- `def update(frame)`

## `src/cohezion/maintenance/pruner.py`
- **class** `PrunerAgent`
  - *Agent responsible for identifying low-density code (bloat) and suggesting pruning.*

## `src/cohezion/maintenance/harvester.py`
- **class** `KnowledgeHarvester`
  - *Agent responsible for harvesting 'Learnings' and 'Journeys' from untracked files*
- `def classify_file(file_path)`

## `src/cohezion/seti/array.py`
- **class** `Signal`
- **class** `ExogenicArray`
  - *Exogenic Signal Processing Array (Gateway 30).*
- `def get_exogenic_array()`
- `def scan_sector(vectors)`
- `def analyze_bitmap(binary_string)`

## `src/cohezion/cloud/router.py`
> Swarm Router - Lightweight Cloud Run service for task routing.
- **class** `TaskStatus`
  - *Status of a task in the queue.*
- **class** `TaskPriority`
  - *Priority levels for tasks.*
- **class** `Task`
  - *A task in the mission queue.*
- **class** `SwarmRouter`
  - *Cloud Run service for routing tasks to the local swarm.*
- `def create_app()`
- `def to_dict()`
- `def from_dict(cls, data)`
- **class** `TaskPayload`

## `src/cohezion/cloud/firestore_sync.py`
> Firestore Sync - Synchronization layer between local and cloud.
- **class** `FirestoreSync`
  - *Synchronization layer between local swarm and Cloud Firestore.*
- `def set_task_handler(handler)`

## `src/cohezion/registry/hooks.py`
> Registry Hooks System.
- **class** `RegistryEvent`
- **class** `RegistryHook`
  - *Base class for registry hooks (callbacks).*
- **class** `HookManager`
  - *Manages subscription and dispatch of registry events.*
- `def get_hook_manager()`
- `def on_skill_registered(skill_name, metadata)`
- `def on_knowledge_stored(entity_id, data)`
- `def register_hook(hook)`
- `def dispatch_skill_registered(skill_name, metadata)`
- `def dispatch_knowledge_stored(entity_id, data)`

## `src/cohezion/registry/skill_registry.py`
- `def load_registry()`
- `def register_skill(name, description, keywords, path)`
- `def search_skills(query, limit)`

## `src/cohezion/registry/capability_registry.py`
> Unified Capability Registry.
- **class** `Capability`
  - *A skill, agent, or MCP server with usage tracking.*
- **class** `CapabilityRegistry`
  - *Unified registry with usage tracking for compound engineering.*
- `def refresh()`
- `def find(query, top_k)`
- `def get_capabilities(name)`
- `def increment_usage(name)`
- `def get_top_used(top_k)`

## `src/cohezion/registry/populate_registry.py`
> Populate the skill registry with all existing skill definitions.

## `src/cohezion/mycelium/shadow_scripter.py`
- **class** `ShadowScripter`
  - *Mycelium Agent: Autonomously grows tests around existing code.*

## `src/cohezion/api/main.py`
> Cohezion API package.

## `src/cohezion/evaluation/draconian_grader.py`
> Draconian Adversarial Grading System
- **class** `VoteType`
- **class** `Critique`
  - *A model's critique of a proposal.*
- **class** `GradingResult`
  - *Result of draconian grading.*
- **class** `DraconianGrader`
  - *DRACONIAN grading system.*
- `def grade(proposal, judges, efficacy_score, completeness_score, forward_looking_score)`

## `src/cohezion/simulation/phase_zero.py`
> Phase Zero: The Awareness of Nothing at All.
- **class** `PhaseZeroEmergence`
  - *Simulates the emergence of reality from the Void through sequential quadrature.*
- `def apply_quadrature(level)`
- `def precipitate()`

## `src/cohezion/simulation/counterfactual_history.py`
> Counterfactual History Simulation.

## `src/cohezion/simulation/digital_twin.py`
> Planetary Digital Twin: Data Ingestor
- **class** `WorldState`
- **class** `StreamIngestor`
- `def connect()`
- `def stream()`
- `def stop()`

## `src/cohezion/simulation/cross_domain_lattice.py`
> Cross-Domain Lattice Simulation.
- **class** `DomainConcept`
- **class** `CrossDomainLattice`
- `def report()`

## `src/cohezion/simulation/glass_box_debate.py`
> Glass Box Debate Simulation.
- `def visualize_debate(traj_a, traj_b, filepath)`

## `src/cohezion/simulation/simulation_logger.py`
- **class** `SimulationLogger`
  - *Handles sharded logging of simulation trajectories using Hugging Face datasets.*
- `def log_cycle(data)`
- `def flush()`
- `def load_universe_data(domain)`
- `def export_to_hub(repo_id, private)`
- `def from_logs(cls, log_path, storage_dir)`

## `src/cohezion/simulation/fractal_universe.py`
> Fractal Universe Simulator (Fractal Nexus)
- **class** `Sector`
- **class** `StabilizerAgent`
- **class** `UniverseGrid`
- **class** `FractalSimulator`
- `def stability()`
- `def coherence()`
- `def move(grid)`
- `def get_sector(x, y)`
- `def get_neighbors(x, y)`
- `def update_sectors()`
- `def render_ascii()`
- `def shutdown(signum, frame)`
- `def step()`
- `def run(max_seconds)`

## `src/cohezion/simulation/exogenic.py`
> Exogenic Evolution Simulator
- **class** `BioSiliconBridge`
- `def simulate_growth(agent_count, global_entropy)`
- `def apply_thermal_noise(signal)`

## `src/cohezion/simulation/enhanced_simulator.py`
> Enhanced Simulation Engine with FLUME + R-Zero Integration
- **class** `FlumeTrajectoryPoint`
  - *Single point in a FLUME thought trajectory.*
- **class** `FlumeIntegration`
  - *Integrates FLUME encoding into simulation pipeline.*
- **class** `RZeroChallenge`
  - *Challenge generated by the R-Zero Challenger.*
- **class** `RZeroSolution`
  - *Solution attempted by the R-Zero Solver.*
- **class** `RZeroEvaluation`
  - *Evaluation by the R-Zero Pragmatist.*
- **class** `RZeroEnhancedTriad`
  - *Enhanced R-Zero implementation with FLUME + PINO integration.*
- **class** `EnhancedSimulationResult`
  - *Result of an enhanced simulation step.*
- **class** `EnhancedSimulator`
  - *Simulation engine integrating FLUME encoding with R-Zero methodology.*
- `def encode(text)`
- `def interpolate(z1, z2, alpha)`
- `def compute_coherence(z_trajectory)`
- `def generate_challenge()`
- `def evaluate(solution, challenge)`
- `def update_difficulty(evaluation)`
- `def get_stats()`

## `src/cohezion/simulation/warm_coherence.py`
> Warm Coherence: Biologically Inspired Physics
- **class** `Exciton`
- **class** `WarmCoherenceEngine`
- `def transport_energy(energy)`
- `def calculate_stochastic_resonance(signal)`
- `def simulate_step(swarm_energy)`

## `src/cohezion/simulation/biological_diversity.py`
- **class** `BiologicalSubstrate`
- **class** `BiologicalDiversityEngine`
  - *Simulates self-organization potentials across different biological substrates.*
- `def get_diversity_engine()`
- `def select_substrate(hiho_coherence)`
- `def hypothesize_novel_form(novelty_index)`
- `def simulate_self_organization(state_12d)`

## `src/cohezion/simulation/yield_estimator.py`
> Yield Estimator (Gateway 10 Expansion).
- **class** `YieldEstimator`
- `def benchmark_hash_rate(duration_s)`
- `def estimate_yield()`

## `src/cohezion/simulation/cross_domain_translator.py`
- **class** `CrossDomainTranslator`
  - *Worker that uses LatentAligner to bridge conceptual gaps between domains.*

## `src/cohezion/simulation/institutional_memory.py`
> Institutional Memory Simulation.
- **class** `CivilizationState`
- **class** `PersistentSimulation`
- `def to_dict()`

## `src/cohezion/simulation/hetv.py`
> HETV Physics Engine (High-Efficiency Toroidal Vorticities)
- **class** `HETVEngine`
- `def calculate_vortex_velocity(r)`
- `def stabilize_swarm(positions, global_entropy)`

## `src/cohezion/simulation/node_verification_prime.py`
> Node Verification Prime (Gateway 10).
- **class** `NodeVerificationPrime`

## `src/cohezion/simulation/analysis_prime.py`
> Simulation Analysis Module (PRIME)
- **class** `SimulationAnalyzer`

## `src/cohezion/mcp/research_server.py`
> Research MCP Server - Specialized for arXiv, Hugging Face, and GitHub mining.
- **class** `ResearchMinerServer`
  - *MCP server for research discovery.*
- `def get_server()`
- `def search_arxiv(query, limit)`
- `def get_hf_trending(limit)`
- `def list_research_channels()`

## `src/cohezion/mcp/skills_server.py`
> Skills MCP Server - Direct skill invocation.
- **class** `SkillsMCP`
  - *MCP server for skill management.*
- `def get_server()`
- `def invoke_skill(skill_name)`
- `def register_skill(name, description, keywords, path)`
- `def search_skills(query, limit)`
- `def list_all()`

## `src/cohezion/mcp/registry.py`
> MCP Registry - Manage internal and external MCP servers.
- **class** `MCPServer`
  - *Represents an MCP server.*
- **class** `MCPRegistry`
  - *Registry for MCP servers.*
- `def get_registry()`
- `def to_dict()`
- `def save()`
- `def get_server(name)`
- `def list_servers(type_filter)`
- `def list_tools(server_name)`
- `def get_relationships(server_name)`
- `def update_status(name, status)`
- `def to_entity_dict()`

## `src/cohezion/mcp/usage_server.py`
> Usage Analytics MCP Server 📊
- `def get_usage_metrics(top_k)`
- `def get_capability_health()`

## `src/cohezion/mcp/narration_server.py`
> Narration MCP Server 🎤
- `def list_voices()`
- `def generate_voiceover(text, voice, filename)`

## `src/cohezion/mcp/surreal_server.py`
> SurrealDB MCP Server - Universe node tools.
- **class** `SurrealMCP`
  - *MCP server for SurrealDB universe nodes.*
- `def get_server()`

## `src/cohezion/mcp/email_notifier.py`
> Email Notification Service.
- **class** `NotificationConfig`
  - *Email notification configuration.*
- **class** `EmailNotifier`
  - *Sends email notifications on task completion.*
- **class** `LocalNotifier`
  - *Fallback: Write notifications to local file.*
- `def from_env(cls)`
- `def is_available()`
- `def send()`

## `src/cohezion/mcp/swarm_server.py`
> Swarm MCP Server - Access to debate workflow.
- **class** `SwarmMCP`
  - *MCP server for swarm debate workflow.*
- `def get_server()`
- `def run_debate(query, perspectives)`
- `def get_perspectives()`
- `def get_metrics()`

## `src/cohezion/mcp/send_hourly_update.py`
- `def load_env_manual()`
- `def send_email(subject, body, recipient)`

## `src/cohezion/mcp/knowledge_server.py`
> Knowledge MCP Server - RAG over library and skills.
- **class** `KnowledgeMCP`
  - *MCP server for knowledge retrieval.*
- `def get_server()`
- `def search_knowledge(query, limit)`
- `def get_skill(skill_name)`
- `def list_skills()`
- `def get_entity(entity_id)`
- `def store_entity(entity)`
- `def get_context_chunk(path, query)`

## `src/cohezion/mcp/findings_dispatcher.py`
- **class** `FindingsDispatcher`
  - *Dispatches findings to external webhooks (Discord, Slack, etc.)*

## `src/cohezion/mcp/keep_oauth.py`
> Google Keep OAuth Setup.
- `def setup_oauth()`
- `def test_keep_api(creds)`

## `src/cohezion/mcp/gmail_communicator.py`
> Gmail Communication MCP Server.
- **class** `EmailMessage`
  - *Parsed email message.*
- **class** `Command`
  - *Parsed command from email.*
- **class** `GmailService`
  - *Gmail API wrapper with OAuth2.*
- **class** `CommandParser`
  - *Parse natural language commands from emails.*
- **class** `GmailCommunicator`
  - *Main communication hub for agent-user interaction via Gmail.*
- `def get_communicator()`
- `def to_dict()`
- `def parse(cls, text)`
- `def complete_action(command)`

## `src/cohezion/mcp/keep_integration.py`
> Google Keep Task Queue Integration.
- **class** `Task`
  - *A task from Keep.*
- **class** `TaskQueue`
  - *Queue of tasks from Keep.*
- **class** `GoogleKeepIntegration`
  - *Integration with Google Keep for task management.*
- **class** `LocalTaskQueue`
  - *Fallback: Local file-based task queue.*
- `def pending()`
- `def to_dict()`
- `def is_available()`
- `def fetch_tasks()`
- `def mark_complete(task)`

## `src/cohezion/mcp/async_workflow.py`
> Async Workflow Orchestrator.
- **class** `AsyncWorkflowOrchestrator`
  - *Orchestrates async task execution from Keep.*
- `def classify_task(task)`

## `src/cohezion/evolution/reflex.py`
- **class** `ReflexAgent`
  - *The 'Subconscious' Reflex System.*

## `src/cohezion/governance/nexus.py`
- **class** `QuadratureNexus`
  - *The Governance Engine of Cohezion.*

## `src/cohezion/expansion/loop.py`
- **class** `ExpansionLoop`
  - *The Growth Engine.*

## `src/cohezion/db/surreal_client.py`
> SurrealDB Client - Multi-model database for the Universe Simulation.
- **class** `PhysicsState`
  - *The 12-dimensional physics state vector (3 Spatial + 1 Time + 8 Brane).*
- **class** `UniverseNode`
  - *A node in the Universe Simulation.*
- **class** `SurrealClient`
  - *Async client for SurrealDB.*
- **class** `InMemoryStore`
  - *In-memory fallback when SurrealDB is not available.*
- `def to_array()`
- `def from_array(cls, arr)`
- `def to_dict()`
- `def pack()`
- `def unpack(cls, packed)`
- `def to_dict(compress)`
- `def store(key, value)`
- `def get(key)`
- `def get_all(limit)`
- `def search_similar(vector, limit)`

## `src/cohezion/db/query_patterns.py`

## `src/cohezion/db/analyze_latent_radar.py`
- `def analyze_journeys()`

## `src/cohezion/db/cache_replay.py`
> Cache Replay Protocol - Enables compound engineering for persistence.
- **class** `CachedWrite`
  - *A cached write operation.*
- **class** `CacheReplayManager`
  - *Manages offline cache and replay for SurrealDB.*
- `def get_cache_manager()`
- `def cache_write(operation, table, data)`
- `def get_pending_writes()`
- `def clear_replayed()`

## `src/cohezion/db/synthesis_healer.py`
- **class** `DirectedSimulator`
  - *A simulator that implements the 'Law of Swarm Recurrence'.*

## `src/cohezion/db/test_autonomic_refinement.py`

## `src/cohezion/db/admin.py`
> Cohezion Database Administration (DBA) Module
- **class** `DBAdmin`
  - *The 'Real DBA' for Cohezion.*

## `src/cohezion/db/repositories/journey_repository.py`
> Journey Repository - Abstract and Dataclass definitions for agentic journeys.
- **class** `JourneyMetrics`
  - *Quantitative metrics for a single journey.*
- **class** `AgentJourney`
  - *A trace of an agent's reasoning and action path.*
- **class** `JourneyRepository`
  - *Abstract base class for journey persistence.*

## `src/cohezion/db/repositories/surreal_journey_repository.py`
> SurrealDB Journey Repository - Concrete implementation using SurrealDB.
- **class** `SurrealJourneyRepository`
  - *Concrete implementation of JourneyRepository for SurrealDB.*

## `src/cohezion/physics/usd_simulator.py`
> USD (Underwater Spark Discharge) Simulator
- **class** `ItonicCluster`
  - *Itonic cluster (micro Ball Lightning) properties.*
- **class** `USDSimulator`
  - *Underwater Spark Discharge simulator.*
- `def calculate_energy()`
- `def create_plasma_bubble(energy_j)`
- `def force_charge_clustering(bubble)`
- `def form_itonic_cluster(cluster_data)`
- `def generate_spark(num_attempts)`

## `src/cohezion/physics/dimension_extractor.py`
> Dimension Extractor - Extract 12D physics dimensions from text/embeddings.
- **class** `DimensionExtractor`
  - *Extracts 12 physics dimensions from text and embeddings.*
- `def extract(text, embedding, created_at, metadata)`
- `def batch_extract(texts, embeddings)`

## `src/cohezion/physics/quantum/utils.py`
- `def reconstruct_site_map(qasm_path, n_qubits)`
- `def compute_seti_metrics(counts, sampling_count, n_qubits)`

## `src/cohezion/physics/quantum/peaked_solver.py`
> Peaked Circuit Solver - 36-qubit Quantum Advantage Challenge
- **class** `PeakedCircuitSolver`
- `def load_circuit()`
- `def setup_optimizer()`
- `def simulate_and_sample(samples)`
- `def compute_amplitude(bitstring)`

## `src/cohezion/system/daemon_manager.py`
- **class** `DaemonManager`
  - *Manages the lifecycle of Cohezion background processes.*
- `def get_daemon_manager()`
- `def is_running(signature)`
- `def start_component(name)`
- `def kill_orphans()`
- `def wake_up()`

## `src/cohezion/system/heartbeat.py`
- **class** `HeartbeatSonification`
  - *Nexus-Approved Feature: Lightweight Audio Heartbeat.*

## `src/cohezion/system/git_sentinel.py`
- **class** `GitSentinel`
  - *Safeguard Agent.*
- `def check_health()`
- `def daily_clean()`

## `src/cohezion/system/ouroboros_recorder.py`
- **class** `OuroborosRecorder`
  - *Ouroboros Sensor Fusion Recorder.*

## `src/cohezion/system/repo_mapper.py`
- **class** `RepositoryMapper`
  - *Generates a high-fidelity Markdown Tree of the codebase.*
- `def generate_map()`

## `src/cohezion/system/context_compressor.py`
- **class** `ContextCompressor`
  - *Sovereign Memory Agent.*
- `def compress()`

## `src/cohezion/caching/semantic_cache.py`
- **class** `SemanticCache`
  - *Semantically aware cache using SurrealDB's vector search (HNSW).*
- `def encoder()`
- **class** `LightweightEncoder`
- `def get_semantic_vector(text)`

## `src/cohezion/browser/agent.py`
- **class** `CohezionBrowserAgent`
  - *Native Playwright-based browser agent for Cohezion.*

## `src/cohezion/bio/morphic_field.py`
- **class** `MorphicField`
  - *Global Morphic Resonance Field (Gateway 26).*
- `def get_morphic_field()`
- `def imprint(vector, score)`
- `def resonate(vector)`

## `src/cohezion/bio/biophotonics.py`
- **class** `Wavelength`
- **class** `BioSignal`
- **class** `LightField`
  - *Biophotonic Signaling Field (Gateway 26).*
- `def get_light_field()`
- `def emit(signal)`
- `def scan(window_seconds)`
- `def get_spectrum_summary()`

## `src/cohezion/models/model_registry.py`
> ModelRegistry for centralized model management.
- **class** `ModelRegistry`
  - *Centralized registry for model management and selection.*
- `def register_defaults()`
- `def register_model(model_info)`
- `def get_model(name)`
- `def list_models()`
- `def get_available_models(provider)`
- `def get_best_for_task(task, budget, available_models, prefer_fast, prefer_quality)`
- `def get_cheapest_with_capability(capability, available_models)`
- `def get_fastest_with_capability(capability, available_models)`
- `def get_best_quality_with_capability(capability, available_models)`
- `def set_budget(budget)`
- `def get_budget()`
- `def track_usage(model_name, tokens_used)`
- `def get_total_cost()`
- `def get_usage_stats()`
- `def reset_tracking()`
- `def sort_key(model)`
- `def cost_key(model)`

## `src/cohezion/models/model_info.py`
> ModelInfo dataclass for model metadata.
- **class** `ModelInfo`
  - *Comprehensive metadata for a registered model.*
- `def is_local()`
- `def is_free()`
- `def has_capability(capability)`
- `def to_dict()`
- `def from_dict(cls, data)`

## `src/cohezion/swarm/hiho_vector_engine.py`
- **class** `HihoVectorEngine`
  - *Highly optimized vectorized engine for mass HIHO simulations.*
- `def calculate_hiho_score(coherence)`
- `def run_simulation(swarm_enabled, flume_enabled, hiho_enabled)`

## `src/cohezion/swarm/comparative_mission_runner.py`
> Comparative Mission Runner - Cohezion Platform Ablation Study.
- `def run_single_config(config)`
- **class** `ComparativeMissionRunner`
- `def run_study()`

## `src/cohezion/swarm/democratic_debate.py`
> Democratic Debate Orchestrator - Multi-agent consensus building.
- **class** `AgentRole`
- **class** `AgentPersona`
  - *Unique personality and voice for each agent.*
- **class** `VoteValue`
- **class** `AgentVote`
- **class** `DebateRound`
- **class** `DebateSession`
- **class** `DemocraticDebate`
  - *Orchestrates multi-round democratic debate between agents.*
- `def system_prompt()`
- `def calculate_consensus()`
- `def to_dict()`

## `src/cohezion/swarm/universal_simulations.py`
> Universal Simulations - Creative Universe Generation.
- **class** `UniverseSpec`
  - *Specification for a universe simulation.*
- **class** `UniverseSimulator`
  - *Runs custom universe simulations.*
- `def sample_state()`

## `src/cohezion/swarm/rzero_challenger.py`
> R-Zero Challenge-Solver System
- **class** `RZeroChallenge`
  - *An optimization challenge extracted from simulation results.*
- **class** `Solution`
  - *A proposed solution from an SLM.*
- **class** `OllamaWrapper`
  - *Simple wrapper for Ollama API calls.*
- **class** `RZeroChallengerSolver`
  - *Generates challenges from simulation anomalies.*
- `def generate_challenges_from_results(simulation_results)`
- `def grade_solutions(solutions)`
- `def solution_to_skill(solution, challenge)`

## `src/cohezion/swarm/tensorbeam_journey.py`
> TensorBeam Journey Graph - Persist to SurrealDB
- **class** `ConceptNode`
  - *A concept in the TensorBeam framework.*
- **class** `JourneyEdge`
  - *A conceptual relationship/dependency.*

## `src/cohezion/swarm/gateway_detector.py`
> Gateway Detector - Automatic capability unlock detection.
- **class** `GatewayCandidate`
  - *A potential Gateway unlock detected from simulation results.*
- **class** `SimResult`
  - *Simplified simulation result for gateway analysis.*
- **class** `GatewayDetector`
  - *Automatically detect when simulation unlocks new capabilities.*
- `def get_gateway_detector()`
- `def to_dict()`
- `def update_cumulative(score)`
- `def analyze_batch(results)`
- `def check_unlock(score, learning)`
- `def unlock_gateway(gateway_id)`
- `def get_status()`
- `def detect_coherence_jump(history, threshold)`

## `src/cohezion/swarm/layperson_presenter.py`
> Layperson Universe Presenter - Making Complex Physics Accessible.
- **class** `LaypersonExplanation`
  - *A simplified explanation of a complex concept.*
- **class** `LaypersonUniversePresenter`
  - *Presents complex physics concepts in accessible ways.*
- `def demo()`
- `def present(universe_key)`
- `def present_all()`
- `def get_random_insight()`
- `def generate_tweet_thread(universe_key)`

## `src/cohezion/swarm/gateway_runner.py`
> Gateway Runner - Autonomous journey to Gateway 42.
- **class** `GatewayRunner`
  - *Autonomous runner towards Gateway 42.*

## `src/cohezion/swarm/agent_factory.py`
> Agent Factory pattern for Cohezion swarm.
- **class** `AgentConfig`
  - *Configuration metadata for an agent class.*
- **class** `AgentFactory`
  - *Factory for creating and managing swarm agents.*
- `def register(cls, name, default_model, capabilities, description, version, author, tags, config_params, requires_dependencies)`
- `def create(cls, agent_name, model, config, dependencies)`
- `def get_metadata(cls, agent_name)`
- `def list_agents(cls, capability, tag)`
- `def find_by_capability(cls, capability)`
- `def is_registered(cls, agent_name)`
- `def get_registry_size(cls)`
- `def discover_agents(cls, agents_dir)`
- `def get_default_model(cls, agent_name)`
- `def clear_registry(cls)`
- `def decorator(agent_class)`

## `src/cohezion/swarm/hourly_mission_logger.py`
- **class** `HourlyMissionLogger`
  - *Tracks and reports mission progress hourly.*
- `def log_snapshot(vitals, results, next_steps)`

## `src/cohezion/swarm/smart_router.py`
> Smart Agent Router - Intelligent routing of tasks to appropriate models.
- **class** `TaskType`
  - *Types of tasks for routing.*
- **class** `ModelCapability`
  - *Model capabilities for matching.*
- **class** `ModelProfile`
  - *Profile of an available model.*
- **class** `RoutingDecision`
  - *Result of routing decision.*
- **class** `AgentAction`
  - *Record of an agent action for knowledge base.*
- **class** `SmartRouter`
  - *Routes tasks to optimal models based on requirements and availability.*
- `def efficiency_score()`
- `def to_dict()`
- `def classify_task(prompt)`
- `def route(task_type)`

## `src/cohezion/swarm/retrospective_runner.py`
> Retrospective Runner - Automated learning extraction and skill generation.
- **class** `Pattern`
  - *An extracted pattern from experience.*
- **class** `RetrospectiveResult`
  - *Result from a retrospective run.*
- **class** `RetrospectiveRunner`
  - *Automated retrospective after simulation batches.*
- `def get_retrospective_runner()`
- `def to_dict()`

## `src/cohezion/swarm/hiho_consensus_runner.py`
> HIHO Consensus Runner - Recursive Democratic Debate Orchestrator.
- **class** `DummySession`
  - *Mock session for final synthesis.*
- **class** `HihoConsensusRunner`

## `src/cohezion/swarm/controller_agent.py`
> Controller Agent - Quadrature Nexus Pattern Implementation
- **class** `IgnitionPack`
  - *Initial package: prompt + context assets.*
- **class** `AgentState`
  - *Shared state across the graph.*
- `def classify_query(state)`
- `def synthesize_responses(state)`
- `def route_to_experts(state)`
- `def build_controller_graph()`
- **class** `ControllerAgent`
  - *Main controller agent implementing Quadrature Nexus pattern.*

## `src/cohezion/swarm/swarm_types.py`
> Core types for the Swarm system.
- **class** `Perspective`
  - *Analyst perspective types for multi-view analysis.*
- **class** `ThoughtVector`
  - *A compressed representation of an analyst's reasoning.*
- **class** `Contradiction`
  - *A detected contradiction between analyst outputs.*
- **class** `CritiqueResult`
  - *The output from the Critic agent's review of analyst outputs.*
- **class** `SynthesizedResponse`
  - *The final synthesized output from the Swarm.*
- **class** `SwarmConfig`
  - *Configuration for the SLM Swarm.*
- `def to_dict()`
- `def has_issues()`
- `def to_dict()`

## `src/cohezion/swarm/flier_verifier.py`
> FLIER Verifier (Structural Energy)
- **class** `FlierEnergy`
  - *Calculates E_flier (Structural Integrity).*

## `src/cohezion/swarm/simulation_runner.py`
> Journey Simulation Batch Runner - Generate and analyze 100 agent journeys.
- **class** `SimulationConfig`
  - *Configuration for batch simulations.*
- **class** `SimulationResult`
  - *Result of a single simulation run.*
- **class** `JourneySimulator`
  - *Simulates agent journeys with realistic physics evolution.*
- `def to_dict()`
- `def simulate_journey(sim_id, query, is_calm)`
- `def analyze_results()`
- `def avg(vals)`

## `src/cohezion/swarm/lattice_orchestrator.py`
> Lattice Orchestrator (CSL) - The Cohezion Swarm Lattice.
- **class** `LatticeState`
  - *Strictly typed state for the Lattice Orchestrator.*
- **class** `LatticeOrchestrator`
  - *Main orchestrator for the Cohezion Swarm Lattice.*
- `def convert_thought_vectors(cls, v)`

## `src/cohezion/swarm/journey_tracker.py`
> Agent Journey Tracker - Record agent thought trajectories in 12D physics space.
- **class** `JourneyMetrics`
  - *Anthropic-style capability and performance metrics.*
- **class** `AgentType`
- **class** `JourneyStep`
  - *A single step in an agent's journey.*
- **class** `AgentJourney`
  - *Complete journey of a debate/query through the agent swarm.*
- **class** `JourneyTracker`
  - *Tracks agent journeys through the swarm.*
- `def get_journey_tracker()`
- `def to_dict()`
- `def to_dict()`
- `def add_step(step)`
- `def to_dict()`
- `def start_journey(query)`
- `def record_step(agent_type, agent_name, perspective, input_text, output_text, physics_state, duration_ms, confidence, metrics)`
- `def get_recent_journeys(limit)`
- `def get_journey_trajectory(journey_id)`

## `src/cohezion/swarm/scenario_mission_runner.py`
- `def run_universe_scenario(config)`
- **class** `ScenarioMissionRunner`

## `src/cohezion/swarm/redundancy_suppression.py`
- **class** `RedundancyManager`
  - *Manages task redundancy and tiered suppression for agents.*
- `def check(task_str)`

## `src/cohezion/swarm/ebms.py`
> Cohezion Crystal Protocol (EBMS Core)
- **class** `EnergyProfile`
  - *The Energy State of a Solution.*
- **class** `EnergyFunction`
  - *Protocol for any module that wants to contribute to the System Energy.*
- **class** `SyntaxEnergy`
  - *Checks for Python syntax errors. High Energy = Invalid Code.*
- **class** `CohezionCrystal`
  - *The Orchestrator of the Crystal Protocol.*
- **class** `MockOllamaClient`

## `src/cohezion/swarm/mass_simulator.py`
> Large-Scale Simulation Runner with Chunking and Monitoring.
- **class** `SystemMetrics`
  - *Current system resource usage.*
- **class** `ChunkResult`
  - *Result of a simulation chunk.*
- **class** `MassSimulationResult`
  - *Result of the entire mass simulation run.*
- `def get_system_metrics()`
- `def generate_physics_state(step, total, agent_type, is_calm)`
- `def simulate_journey_fast(sim_id, is_calm)`
- **class** `MassSimulator`
  - *Run 10,000+ simulations with resource management.*
- `def is_safe()`
- `def to_dict()`
- `def run_chunk(chunk_id, start_idx, count)`
- `def run_custom_chunk(chunk_id, inputs, processor_func)`
- `def run()`

## `src/cohezion/swarm/mission_verifier_agent.py`
- **class** `MissionVerifier`
  - *Automates the verification of multimodal reports and dashboards.*
- `def get_verification_task(dashboard_url)`

## `src/cohezion/swarm/git_health.py`
> Git Health Utilities.
- **class** `GitCommit`
- **class** `HealthTrace`
- `def collect_git_metadata()`
- `def get_line_blame(file_path, line_number)`
- `def attribute_complexity(issues)`
- `def get_unpushed_commits()`
- `def get_repo_bloat()`

## `src/cohezion/swarm/multimodal_reporter.py`
- **class** `MultimodalReporter`
  - *Synthesizes simulation data into multimodal reports (Images, Audio Data, Marimo Carousels).*
- `def generate_universe_summary(scenario_results)`
- `def create_multiverse_carousel(all_results)`

## `src/cohezion/swarm/model_manager.py`
> Ollama Model Manager - Benchmark, auto-swap, and storage management.
- **class** `ModelMetrics`
  - *Metrics for a single model.*
- **class** `ModelConfig`
  - *Configuration for model roles.*
- **class** `OllamaModelManager`
  - *Manages Ollama models with benchmarking and auto-optimization.*
- `def get_manager()`
- `def update(latency_ms, success, quality)`
- `def get_best_model(task_type)`
- `def record_result(model_name, task_type, latency_ms, success, quality)`
- `def get_role_assignments()`
- `def get_metrics_summary()`

## `src/cohezion/swarm/universe_vector_engine.py`
- **class** `UniverseVectorEngine`
  - *Parametric vectorized engine for Multiverse scenario modeling.*
- `def run_scenario(name, momentum, coupling, hiho_target, entropy, swarm_enabled, flume_enabled, hiho_enabled)`

## `src/cohezion/swarm/multi_audience_presenter.py`
> Multi-Audience Universe Presenter.
- **class** `AudienceConfig`
  - *Configuration for a specific audience.*
- **class** `MultiAudiencePresenter`
  - *Presents universe concepts to different audiences.*
- **class** `UniverseQA`
  - *Interactive Q&A about universes with security guardrails.*
- `def demo()`
- `def present(universe_key, audience)`
- `def get_all_audiences()`
- `def is_allowed(question)`
- `def answer(question, audience)`
- `def suggest_questions()`

## `src/cohezion/swarm/advanced_physics.py`
> Advanced Physics Universe Simulations.
- **class** `AdvancedPhysicsEngine`
  - *Runs advanced physics simulations for long-horizon exploration.*
- `def generate_new_topics()`
- `def get_status()`

## `src/cohezion/swarm/synthesis.py`
> Swarm Synthesis Implementation.
- **class** `SwarmConsensus`
- **class** `SwarmSynthesizer`
- `def run_demo()`
- `def synthesize(vectors)`

## `src/cohezion/swarm/self_improvement_orchestrator.py`
> Self-Improvement Orchestrator - The Heart of Cohezion.
- **class** `ImprovementCycle`
  - *Record of one self-improvement cycle.*
- **class** `SelfImprovementOrchestrator`
  - *Universal pattern for Cohezion self-improvement.*
- `def get_orchestrator()`
- `def duration_ms()`
- `def get_status()`

## `src/cohezion/swarm/journey_narrator.py`
- **class** `JourneyNarrator`
  - *Provides natural language narration for agentic journeys.*
- `def generate_narration(agent_name, task, thought)`

## `src/cohezion/swarm/agents/analyst.py`
> Analyst Agent - Feature extraction with configurable perspectives.
- **class** `AnalystAgent`
  - *Gemma-based analyst for feature extraction and thought generation.*

## `src/cohezion/swarm/agents/quantum_agent.py`
- **class** `QuantumAgent`
  - *Quantum-Enhanced Agent (Phase 14).*

## `src/cohezion/swarm/agents/base.py`
> Base agent class for all SLM Swarm agents.
- **class** `AgentResponse`
  - *Enhanced string response with native agentic metadata.*
- **class** `BaseAgent`
  - *Abstract base class for Swarm agents.*
- `def client()`
- `def find_tools(query, top_k)`
- `def get_metrics()`

## `src/cohezion/swarm/agents/pruning_agent.py`
> PruningAgent - Knowledge Compression & Clutter Reduction (Gateway 9).
- **class** `PruningAgent`

## `src/cohezion/swarm/agents/memory_agent.py`
> MemoryAgent - Long-Term Contextual Memory (Gateway 7/14).
- **class** `MemoryAgent`

## `src/cohezion/swarm/agents/synthesizer.py`
> Synthesizer Agent - Aggregation and final response generation.
- **class** `SynthesizerAgent`
  - *Mistral-based synthesizer for final response generation.*

## `src/cohezion/swarm/agents/visualization_agent.py`
> Visualization Agent - Multimodal output generation for simulations.
- **class** `VisualizationRequest`
  - *Request for visualization generation.*
- **class** `VisualizationResult`
  - *Result of visualization generation.*
- **class** `VisualizationAgent`
  - *Agent for generating multimodal visualizations from simulation data.*
- `def animate(frame)`

## `src/cohezion/swarm/agents/hypothesis_agent.py`
> HypothesisAgent - Automated Hypothesis Testing (Gateway 20).
- **class** `HypothesisAgent`

## `src/cohezion/swarm/agents/email_listener_agent.py`
> Email Listener Agent (Gateway 9).
- **class** `EmailListenerAgent`
  - *Agent that monitors an IMAP inbox for commands/prompts.*

## `src/cohezion/swarm/agents/handoff_agent.py`
> HandoffAgent - Session Synthesis and Persistence (Gateway 4/14).
- **class** `HandoffAgent`
  - *Agent specialized in synthesizing session history into compact snapshots.*

## `src/cohezion/swarm/agents/introspect_agent.py`
- **class** `IntrospectAgent`
  - *Introspect Agent (Phase 20).*

## `src/cohezion/swarm/agents/world_model_agent.py`
> WorldModelAgent - Mines for JEPA and World Model architectures.
- **class** `WorldModelAgent`
  - *Miner agent focused on JEPA (Joint-Embedding Predictive Architecture) and World Models.*

## `src/cohezion/swarm/agents/healer_agent.py`
> HealerAgent - Autonomous Code Refactoring and Self-Healing.
- **class** `HealerAgent`

## `src/cohezion/swarm/agents/critic.py`
> Critic Agent - Logic verification and contradiction detection.
- **class** `CriticAgent`
  - *Phi-3 based critic for logic verification.*

## `src/cohezion/swarm/agents/efficiency_audit_agent.py`
> Efficiency Audit Agent for Cohezion.
- **class** `EfficiencyAuditAgent`
  - *An agent dedicated to auditing system performance (Tokens/Context/Latency).*

## `src/cohezion/swarm/agents/gallery_agent.py`
- **class** `TheGalleryAgent`
  - *The Media Synthesis Specialist.*

## `src/cohezion/swarm/agents/chronicle_agent.py`
> ChronicleAgent - Repository-wide Knowledge Synthesis and Memory.
- **class** `ChronicleAgent`

## `src/cohezion/swarm/agents/model_manager_agent.py`
- **class** `ModelSpec`
- **class** `ModelManagerAgent`
  - *The ModelManagerAgent is responsible for maintaining the local AI model roster.*
- `def check_storage_health()`
- `def evaluate_new_candidate(candidate, current_roster)`

## `src/cohezion/swarm/agents/reporter.py`
> Interactive Report Agent (Gateway 15).
- **class** `InteractiveReportAgent`
  - *Generates reports with:*

## `src/cohezion/swarm/agents/alignment_agent.py`
- **class** `AlignmentAgent`
  - *Alignment Auditor Agent (Gateway 33).*

## `src/cohezion/swarm/agents/inbox_miner_test.py`
> Verification for Gateway 9 Expansion (Inbox Miner).

## `src/cohezion/swarm/agents/biological_agent.py`
- **class** `BiologicalAgent`
  - *Biological Intelligence Agent (Phase 15).*

## `src/cohezion/swarm/agents/vision_agent.py`
> VisionAgent - Multi-modal sensory processing for the swarm.
- **class** `VisionAgent`

## `src/cohezion/swarm/agents/meta_skill_agent.py`
> Meta-Skill Agent Implementation.
- **class** `ProposedSkill`
- **class** `MetaSkillAgent`

## `src/cohezion/swarm/agents/seti_agent.py`
- **class** `SETIAgent`
  - *SETI Agent (Phase 19).*

## `src/cohezion/swarm/agents/task_master.py`
> TaskMasterAgent - Autonomous project tracking and journey persistence.
- **class** `TaskMasterAgent`
  - *Agent that monitors the project's task and plan state and ensures it is*

## `src/cohezion/swarm/agents/architect_agent.py`
> ArchitectAgent - Compositional Asset Generation (Gateway 17).
- **class** `ArchitectAgent`

## `src/cohezion/swarm/agents/local_reasoner_agent.py`
> Local Reasoner Benchmark - Evaluates Ollama models on logic tasks.
- **class** `LocalReasonerAgent`
  - *Agent for benchmarking local model reasoning.*

## `src/cohezion/swarm/agents/model_wrangler_agent.py`
> Model Wrangler Specialist Agent.
- **class** `ModelWrangler`
  - *Expert agent for Ollama model roster management.*
- `def get_model_for_role(role)`

## `src/cohezion/swarm/agents/rlm_reasoning_agent.py`
- **class** `RLMReasoningAgent`
  - *Recursive Language Model Reasoning Agent.*

## `src/cohezion/swarm/agents/skill_audit_agent.py`
> Skill Audit Agent for Cohezion.
- **class** `SkillAuditAgent`
  - *An agent capable of auditing the skill registry for distinction and complementarity.*

## `src/cohezion/swarm/agents/narrative_weaver_agent.py`
- **class** `TheNarrativeWeaver`
  - *The Bridge Specialist.*

## `src/cohezion/swarm/agents/security_guard_agent.py`
> SecurityGuardAgent - Real-time protection for the Cohezion Swarm.
- **class** `SecurityGuardAgent`
- `def check_input(text)`
- `def check_output(text)`

## `src/cohezion/swarm/agents/benchmark_auditor_agent.py`
- **class** `TheBenchmarkAuditor`
  - *The Competitive Edge Specialist (R-Zero Protocol).*

## `src/cohezion/swarm/agents/exploration_agent.py`
> ExplorationAgent - Emergent Behavior & Novelty Tracking (Gateway 10).
- **class** `ExplorationAgent`

## `src/cohezion/swarm/agents/email_integration_test.py`
> Verification for Gateway 9 (External Integration).

## `src/cohezion/swarm/agents/surreal_dba_agent.py`
> SurrealDB DBA Specialist Agent.
- **class** `SurrealDBDBA`
  - *Expert agent for SurrealDB management.*

## `src/cohezion/swarm/agents/gaia_agent.py`
- **class** `GaiaAgent`
  - *Gaia Agent (Phase 18).*

## `src/cohezion/swarm/agents/lab_agent.py`
> LabAgent - Orchestrator of the Autonomous AI Lab.
- **class** `LabAgent`

## `src/cohezion/swarm/agents/git_health_agent.py`
> Git Health Agent - Analyzes repository hygiene and lineage.
- **class** `GitHealthAgent`
  - *Agent specialized in repository health and git history analysis.*

## `src/cohezion/swarm/agents/inbox_miner.py`
> Inbox Miner (Gateway 9 Expansion).
- **class** `InboxMiner`
  - *Miner agent that scans historical emails and classifies them.*

## `src/cohezion/swarm/agents/sovereign_agent.py`
- **class** `SovereignAgent`
  - *Sovereign Agent (Phase 17).*

## `src/cohezion/swarm/agents/ethics_agent.py`
> Ethics Agent for Cohezion.
- **class** `EthicsAgent`
  - *An agent dedicated to auditing the ethics of other agent actions.*

## `src/cohezion/swarm/agents/x_scout_agent.py`
> XScoutAgent - Monitors high-signal researcher feeds on X (Twitter).
- **class** `XScoutAgent`
  - *Agent that "scouts" X for researcher updates.*

## `src/cohezion/swarm/agents/universe_sim_agent.py`
> Universe Simulation Agent (Anthropic Alignment)
- **class** `VectorField`
  - *Represents a latent thought vector.*
- **class** `UniverseNode`
  - *A node in the hierarchical agent universe.*
- **class** `UniverseSimulationAgent`
  - *Orchestrates the physics-based simulation of agent hierarchies.*
- `def add_child(child)`
- `def initialize_cosmos(galaxies, systems_per_galaxy, agents_per_system)`
- `def run_physics_step()`

## `src/cohezion/swarm/agents/cosmic_agent.py`
- **class** `CosmicAgent`
  - *Cosmic Agent (Phase 16).*

## `src/cohezion/swarm/agents/skill_distiller.py`
> SkillDistiller Agent - Autonomous Skill Extraction from repetitive tasks.
- **class** `SkillDistiller`

## `src/cohezion/swarm/agents/code_simplification_agent.py`
> Code Simplification Agent - Reduces complexity based on refactoring patterns.
- **class** `CodeSimplificationAgent`
  - *Agent specialized in simplifying complex code structures.*

## `src/cohezion/swarm/agents/trend_scout_agent.py`
> Trend Scout Agent
- **class** `TrendScoutAgent`

## `src/cohezion/swarm/agents/luminary_agent.py`
- **class** `TheLuminary`
  - *The Visual Architect specialist.*

## `src/cohezion/swarm/agents/nexus_research_agent.py`
> NexusResearchAgent - Specialized for mining arXiv, Hugging Face, and GitHub.
- **class** `NexusResearchAgent`
  - *Agent that monitors external research platforms and filters for high-signal SOTA.*
- `def check_budget(cost)`

## `src/cohezion/swarm/agents/you_tube_transcript_agent.py`
> YouTubeTranscriptAgent - Specialized for mining AI video content (JEPA, World Models).
- **class** `YouTubeTranscriptAgent`
  - *Miner agent that fetches and synthesizes YouTube transcripts for AI research.*

## `src/cohezion/swarm/agents/librarian_agent.py`
> LibrarianAgent - Guardian of Project Knowledge and Documentation.
- **class** `LibrarianAgent`

## `src/cohezion/swarm/memory/shared_context.py`
> Shared Context - Thread-safe shared state for swarm agents.
- **class** `ConversationTurn`
  - *A single turn in a conversation.*
- **class** `SharedContext`
  - *Thread-safe shared context for swarm agents.*
- `def add_turn(role, content, metadata)`
- `def get_history(limit)`
- `def get_formatted_history(limit)`
- `def cache_get(key)`
- `def cache_set(key, value)`
- `def cache_clear()`
- `def enqueue_task(task)`
- `def dequeue_task()`
- `def peek_tasks(limit)`
- `def set_agent_state(agent_id, state)`
- `def get_agent_state(agent_id)`
- `def get_all_agent_states()`

## `src/cohezion/swarm/rlm/rlm_executor.py`
- **class** `RLMExecutor`
  - *Recursive Language Model Executor.*
- `def get_rlm_executor()`
- `def execute_recursive_step(code, context_vars)`

## `src/cohezion/swarm/rlm/scalar_context_manager.py`
- **class** `ScalarContextManager`
  - *Manages RLM context using a scalar importance heuristic.*
- `def get_scalar_context_manager()`
- `def calculate_importance(text_segment, query, stability)`

## `src/cohezion/swarm/workflows/debate_protocol.py`
> Debate Protocol Workflow - Hierarchical voting with parallel analysts.
- **class** `DebateWorkflow`
  - *The Hierarchical Voting debate protocol.*
- `def get_metrics()`

## `src/cohezion/swarm/agent_components/agent_cache.py`
> Agent Cache - LRU cache for agent responses with TTL.
- **class** `CacheConfig`
  - *Configuration for agent cache.*
- **class** `CacheEntry`
  - *Cached response entry.*
- **class** `AgentCache`
  - *LRU cache for agent responses with TTL-based expiration.*
- `def get(key, images)`
- `def set(key, response, embedding, persistence_id, phi_score, confidence, alignment_score, images, narration)`
- `def clear_expired()`
- `def get_stats()`

## `src/cohezion/swarm/agent_components/agent_security.py`
> Agent Security - Input validation and output filtering.
- **class** `SecurityConfig`
  - *Configuration for agent security.*
- **class** `SecurityResult`
  - *Result of security validation.*
- **class** `AgentSecurity`
  - *Security layer for agent input validation and output filtering.*
- `def validate_input(prompt)`
- `def filter_output(output, confidence)`
- `def get_stats()`
- `def analyze_input(prompt)`
- `def analyze_output(output, confidence)`

## `src/cohezion/swarm/agent_components/agent_http_client.py`
> Agent HTTP Client - HTTP connection management with retry logic.
- **class** `HTTPClientConfig`
  - *Configuration for HTTP client.*
- **class** `AgentHTTPClient`
  - *Async HTTP client with retry logic for agent model calls.*
- `def client()`

## `src/cohezion/core/zpe_engine.py`
- **class** `ZPEEngine`
  - *Zero-Point Energy Extraction Engine.*

## `src/cohezion/core/time_keeper_test.py`
> Verification script for Gateway 11 (Temporal Mastery) foundation.

## `src/cohezion/core/bandwidth_monitor.py`
> Bandwidth Monitor for Alternative Self-Funding.
- **class** `BandwidthMonitor`
  - *Simulates earning credits by sharing bandwidth.*
- `def stop()`

## `src/cohezion/core/local_registry.py`
- **class** `LocalRegistry`
  - *Dynamic Local Model Registry (Gateway 28).*
- `def get_local_registry()`
- `def refresh()`
- `def is_available(model_name)`
- `def get_best_available_local(preferred)`
- `def check_capacity(min_gb)`

## `src/cohezion/core/credit_manager.py`
> Credit Manager for Recursive Sovereignty (Gateway 12).
- **class** `CreditManager`
  - *Singleton manager for agent credit balances.*
- `def get_credit_manager()`
- `def get_balance(agent_id)`
- `def deduct(agent_id, amount)`
- `def credit(agent_id, amount)`
- `def can_afford(agent_id, model)`
- `def get_model_cost(model)`
- `def get_best_affordable_model(agent_id, preferred)`

## `src/cohezion/core/time_keeper.py`
> TimeKeeper Core Service.
- **class** `TimeKeeper`
- `def get_time_keeper()`
- `def now_iso()`
- `def session_uptime()`

## `src/cohezion/core/resource_monitor.py`
> Resource Monitor Service.
- **class** `ResourceMonitor`
- `def get_resource_monitor()`
- `def get_stats()`
- `def check_and_enforce()`
- `def should_rent()`

## `src/cohezion/core/credit_manager_test.py`
> Verification for Phase 6 (Recursive Sovereignty).

## `src/cohezion/reliability/sync.py`
> Reliability Synchronization Primitives.
- **class** `FileLock`
  - *Advisory file locking context manager.*
- **class** `SafeWriter`
  - *Atomic file writer context manager.*
- **class** `AgentWorkspace`
  - *Shadow tree isolation for multi-file operations.*
- `def acquire()`
- `def open()`
- `def session()`
- `def commit()`

## `src/cohezion/reliability/pool.py`
> Connection Pool - Reusable HTTP connections.
- **class** `ConnectionPool`
  - *HTTP connection pool manager.*
- `def get_pool(name, base_url, max_connections)`
- `def get_stats()`

## `src/cohezion/reliability/monitor.py`
- **class** `ResourceMonitor`
  - *Global Resource Monitor & Concurrency Guard (Gateway 33).*
- `def get_resource_monitor()`
- `def register_coordinator(coordinator)`
- `def release_capacity()`
- `def get_vitals()`
- `def get_dilation_factor()`
- `def checkpoint_active_mission(data, mission_id)`

## `src/cohezion/training/training_data_capture.py`
> Training Data Capture System
- **class** `InteractionRecord`
  - *Single prompt/response interaction.*
- **class** `JourneyRecord`
  - *Complete agent journey across multiple interactions.*
- **class** `TrainingDataCapture`
  - *Captures and logs all interactions for training data generation.*
- **class** `OvernightTrainingIntegration`
  - *Integration with overnight_driver.py for continuous training data capture.*
- `def start_journey(agent_id, stream)`
- `def end_journey(agent_id, stream, status, final_score)`
- `def compute_rankings()`
- `def get_stats()`

## `src/cohezion/ui/nexus_ui.py`
- **class** `NexusUI`
  - *Abstracted UI toolkit for Cohezion CLI.*
- **class** `ConsciousnessIgnition`
  - *Handles the startup boot sequence.*
- `def Layout_Mini_Split(text, progress, color, pulse_char)`
- `def create_header(uptime)`
- `def create_pulse(coherence)`
- `def create_lattice(expert_domains, expert_status)`
- `def create_metrics()`
- `def create_discovery_ticker(discoveries)`
- `def create_avatar()`
- `def ignite()`

## `src/cohezion/cli/main.py`
> Cohezion: Unified CLI Framework
- `def quickstart()`
- `def hello(name, colorful)`
- `def version()`
- `def main(verbose, config)`
- `def swarm_run(query, experts, rounds, model)`
- `def swarm_debate(topic, participants, duration)`
- `def swarm_simulate(iterations, agents, parallel)`
- `def dashboard_start(host, port, reload)`
- `def config_show(section)`
- `def config_validate()`
- `def explore_skills(category, limit)`
- `def explore_journey(agent, steps)`
- `def demo_flume(input_text, steps, visualize)`
- `def demo_nexus(scenario, complexity, interactive)`
- `def demo_journey(agent_id, steps, dimension)`
- `def universe_seed(name, description)`
- `def universe_list(node_type, limit)`
- `def ouroboros_status(detailed)`
- `def ouroboros_heal(force, dry_run)`
- `def ouroboros_history(limit)`

## `src/cohezion/healing/immune_system.py`
> Immune System (Gateway 13).
- **class** `VelocityMonitor`
  - *Monitors task velocity and triggers alerts/diagnoses when it drops.*
- **class** `ActuatorSystem`
  - *Executes corrective actions based on immune system diagnosis.*
- **class** `SelfDiagnostic`
  - *Uses CriticAgent to analyze recent errors and produce recommendations.*
- `def stop()`

## `src/cohezion/healing/deep_audit.py`
> Deep Codebase Auditor.
- **class** `CodeIssue`
- **class** `FileStats`
- **class** `DeepAuditor`
- `def run_deep_audit()`
- `def audit_file(file_path)`
- `def visit_AsyncFunctionDef(node)`
- `def visit_FunctionDef(node)`
- `def generate_report()`

## `src/cohezion/healing/platform_audit.py`
> Platform Audit - Comprehensive health check for Cohezion.
- **class** `AuditResult`
  - *Result of a single audit check.*
- **class** `PlatformAudit`
  - *Complete platform audit report.*
- `def run_audit(audit_type)`
- `def print_audit(audit)`
- `def to_dict()`

## `src/cohezion/healing/utilization_audit.py`
> Utilization Audit Script.
- `def analyze_utilization()`

## `src/cohezion/healing/amd_s2idle_report.py`
> Redirection to a moved location
- `def read_file(fn)`
- `def get_distro()`
- `def is_root()`
- `def relaunch_sudo()`
- **class** `DistroPackage`
  - *Base class for distro packages*
- **class** `PipxPackage`
  - *Pyudev package*
- `def check_amd_s2idle(stdout)`
- `def install()`

## `src/cohezion/gaia/interface.py`
- **class** `PlanetaryInterface`
  - *Planetary Interface (Gateway 29).*
- `def get_planetary_interface()`
- `def report_activity()`
- `def report_entropy_flux(vector)`
- `def get_cosmic_constants()`

## `src/cohezion/services/knowledge_service.py`
> Knowledge Service - Knowledge graph operations.
- **class** `KnowledgeNode`
  - *A node in the knowledge graph.*
- **class** `KnowledgeEdge`
  - *An edge in the knowledge graph.*
- **class** `KnowledgeQuery`
  - *A query result from the knowledge graph.*
- **class** `KnowledgeService`
  - *Service for knowledge graph operations.*

## `src/cohezion/services/physics_service.py`
> Physics Service - 12D physics state operations.
- **class** `PhysicsConfig`
  - *Configuration for physics calculations.*
- **class** `PhysicsAnalysis`
  - *Result of physics state analysis.*
- **class** `PhysicsService`
  - *Service for 12D physics state operations.*

## `src/cohezion/services/agent_service.py`
> Agent Service - Agent orchestration and lifecycle management.
- **class** `AgentConfig`
  - *Configuration for agent instances.*
- **class** `AgentStatus`
  - *Status information for an agent.*
- **class** `AgentService`
  - *Service for agent orchestration and lifecycle management.*

## `src/cohezion/services/swarm_service.py`
> Swarm Service - Full QUADRATURE NEXUS orchestration.
- **class** `QuadratureConfig`
  - *Configuration for QUADRATURE NEXUS execution.*
- **class** `QuadratureResult`
  - *Result of QUADRATURE NEXUS execution.*
- **class** `QuadraturePhase`
  - *Represents a phase in QUADRATURE NEXUS.*
- **class** `SwarmService`
  - *Service for full QUADRATURE NEXUS orchestration.*

## `src/cohezion/introspect/scanner.py`
- **class** `InternalScanner`
  - *Internal Signal Scanner (Gateway 30+).*
- `def get_internal_scanner()`
- `def scan_codebase()`
- `def scan_history()`

## `src/cohezion/monitoring/ratchet_monitor.py`
> Ratchet Health Monitor
- **class** `SystemVitals`
  - *Current system health metrics.*
- **class** `RatchetMonitor`
  - *Ratchet-style health monitor.*
- `def is_critical()`
- `def needs_throttle()`
- `def check_vitals()`
- `def diagnose(vitals)`
- `def send_alert(vitals, message)`
- `def monitor_loop(check_interval)`

## `src/cohezion/flume/vliw_latent_alignment.py`

## `src/cohezion/flume/git_encoder.py`
> Git FLUME Encoder - Semantic history analysis using latent space trajectories.
- **class** `GitEncoder`
  - *Analyzes git history through the lens of FLUME manifold encoding.*
- `def encode_history(commits)`
- `def get_health_direction(trajectory)`
- `def evaluate_drift(commits, pivot_index)`

## `src/cohezion/flume/autoencoder.py`
> Thought Autoencoder - Compress paragraphs of text to continuous vectors.
- **class** `FlumeConfig`
  - *Configuration for Flume Autoencoder.*
- **class** `ThoughtEncoder`
  - *Encoder network: text tokens → thought vector z.*
- **class** `ThoughtDecoder`
  - *Decoder network: thought vector z → text tokens.*
- **class** `FlumeEncoder`
  - *Full autoencoder for thought vector compression.*
- `def forward(tokens, attention_mask)`
- `def forward(z, target_tokens)`
- `def encode(text, max_len)`
- `def decode(z, max_len, temperature)`
- `def forward(input_ids, attention_mask)`
- `def reconstruction_loss(input_ids, attention_mask)`
- `def get_semantic_vector(text)`
- `def interpolate(text_a, text_b, steps)`
- `def semantic_add(base, direction, scale)`
- `def semantic_direction(from_concept, to_concept)`
- `def cross_domain_bridge(concept_a, domain_a_example, domain_b_example)`
- `def similarity(text_a, text_b)`
- `def save(path)`
- `def load(path)`

## `src/cohezion/flume/bioelectric.py`
> Bioelectric Action Vectors - Maps Levin's bioelectric signaling to COHEZION.
- **class** `BioelectricSignal`
  - *A bioelectric signal in the morphospace.*
- **class** `ActionVector`
  - *An action vector derived from bioelectric signals.*
- **class** `BioelectricEngine`
  - *Maps bioelectric signaling patterns to 12D action vectors.*
- `def encode_signal(current_state, target_state)`
- `def decode_action(signal, current_state)`
- `def step(state, target, step_size)`
- `def simulate_morphogenesis(initial_state, target_well, max_steps)`

## `src/cohezion/flume/alignment.py`
- **class** `DomainAlignmentMLP`
  - *Small MLP to map between latent manifold regions.*
- **class** `LatentAligner`
  - *Bridges conceptual domains by mapping thought-vectors between different*
- `def forward(x)`
- `def get_aligner(source_domain, target_domain)`
- `def align(vector, source_domain, target_domain)`
- `def register_centroid(domain, vectors)`
- `def domain_shift(vector, source_domain, target_domain)`

## `src/cohezion/flume/vliw_kernel_sim.py`
- **class** `VLIWSimulator`
- `def hash_round(data)`
- `def run_vectorized()`

## `src/cohezion/flume/lcsp.py`
> LCSP - Lattice-Coupled State Projection.
- **class** `LCSPPrediction`
  - *Result of an LCSP prediction.*
- **class** `LCSPPredictor`
  - *Lattice-Coupled State Projection predictor.*
- `def initialize()`
- `def encode(state)`
- `def predict_latent(latent, context)`
- `def decode(latent)`
- `def predict(state, context)`

## `src/cohezion/flume/morphospace.py`
> Morphospace Mapper - Navigate stability wells in the 12D manifold.
- **class** `StabilityWell`
  - *A stable region in the morphospace.*
- **class** `MorphoPath`
  - *A path through the morphospace.*
- **class** `MorphospaceMapper`
  - *Maps and navigates the 12D morphospace.*
- `def compute_stability(state)`
- `def find_nearest_well(state)`
- `def navigate_to_well(start, target_well, max_steps)`
- `def discover_wells(num_samples, stability_threshold)`

## `src/cohezion/flume/navigator.py`
> Flume Navigator - Predicts and navigates thought trajectories in latent space.
- **class** `FlumeNavigator`
  - *Handles trajectory prediction and manifold navigation for FLUME.*
- `def predict_trajectory(start_text, steps, momentum, physics_weight, hiho_damping)`
- `def predict_branches(start_text, num_branches, steps, scenario)`

## `src/cohezion/flume/mnm.py`
> Modular Neural Manifolds (MNM) - "Frozen Neural Books"
- **class** `ManifoldWarp`
  - *A small, pluggable network that 'warps' a latent vector z*
- **class** `ManifoldManager`
  - *Manages loading and applying domain-specific Modular Neural Manifolds.*
- `def forward(z)`
- `def create_manifold(name)`
- `def activate_manifold(name)`
- `def warp(z, manifold_name)`
- `def load_frozen_book(path, name)`
- `def save_frozen_book(name, path)`

## `src/cohezion/flume/benchmark_swarm_s16.py`
- `def benchmark_swarm()`

## `src/cohezion/flume/predictor.py`
- **class** `TrajectoryPredictor`
  - *Models the 'velocity' and evolution of reasoning in latent space.*
- `def forward(z)`
- `def predict_sequence(z, steps)`
- `def predict_with_physics(z, steps, physics_weight, momentum)`
- `def imagine_branches(z, perturbations, steps, noise_scale)`

## `src/cohezion/flume/tokenizer.py`
- **class** `FlumeTokenizer`
  - *Simple character-level tokenizer for Flume.*
- `def vocab_size()`
- `def get_vocab()`
- `def convert_tokens_to_string(tokens)`
- `def save_vocabulary(save_directory, filename_prefix)`

## `src/cohezion/journey/registry.py`
- `def get_journey_registry()`

## `src/cohezion/journey/narrator.py`
- **class** `NarrativeEngine`
  - *Orchestrates immersive narration with typewriter effects and interactive pauses.*
- **class** `JourneyRegistry`
  - *Manages the registration and discovery of interactive 'Voyages'.*
- `def register_voyage(name, description, entry_point)`
- `def get_voyage(name)`
- `def list_voyages()`

## `src/cohezion/journey/voyages/gateway.py`

## `src/cohezion/journey/voyages/hiho_attractor.py`

## `src/cohezion/delegation/prompt_architect.py`
- **class** `PromptArchitect`
  - *The Meta-Prompt Architect.*

## `src/cohezion/cosmic/plasma.py`
- **class** `PlasmaFilaments`
  - *Cosmic Connectivity Layer (Gateway 27).*
- `def get_plasma_filaments()`
- `def establish_filament(node_a, node_b, conductance)`
- `def conduct_impulse(start_node, payload, max_depth)`

## `src/cohezion/cosmic/reality.py`
- **class** `RealityStabilizer`
  - *HIHO Reality Stability Protocol (Gateway 27).*
- `def get_reality_stabilizer()`
- `def calculate_stability(vector)`
- `def stabilize(vector)`

## `src/cohezion/security/vault.py`
- **class** `BitwardenVault`
  - *Secure interface for Bitwarden CLI (bw).*
- `def get_vault()`
- `def is_locked()`
- `def get_secret(name)`

## `src/cohezion/security/auth.py`
> Authentication - API keys and JWT tokens.
- **class** `AuthError`
  - *Authentication error.*
- `def verify_api_key(api_key)`
- `def create_token(data, expires_delta)`
- `def verify_token(token)`
- `def hash_password(password)`
- `def verify_password(plain_password, hashed_password)`
- `def check_role(user_role, required_role)`

## `src/cohezion/security/credentials.py`
- **class** `CredentialManager`
  - *Centralized credential retrieval with Bitwarden priority and ENV fallback.*
- `def get_credentials()`
- `def get_secret(name, env_var)`

## `src/cohezion/security/output_filter.py`
> Output Filter - Filter LLM output for safety.
- **class** `FilterResult`
  - *Filter result codes.*
- **class** `FilteredOutput`
  - *Result of output filtering.*
- **class** `OutputFilter`
  - *Filter LLM outputs for safety.*
- `def filter(text)`
- `def add_confidence_warning(text, confidence, threshold)`
- `def get_stats()`

## `src/cohezion/security/audit.py`
> Audit Logger - Structured logging for security events.
- **class** `AuditEvent`
  - *Structured audit event.*
- **class** `AuditLogger`
  - *Audit logger for security and compliance.*
- `def get_audit_logger()`
- `def to_json()`
- `def log_request(endpoint, method, ip_address, user, status_code, latency_ms)`
- `def log_auth(action, user, ip_address, success, reason)`
- `def log_security(action, threat_level, ip_address, details)`
- `def log_debate(query_hash, model_chain, confidence, latency_ms)`
- `def get_recent_events(limit, event_type)`

## `src/cohezion/security/adversarial_tester.py`
> Adversarial Security Tester - High-Performance Testing Framework.
- **class** `TestResult`
  - *Result of a single adversarial test.*
- **class** `TestMetrics`
  - *Aggregated test metrics.*
- `def test_single_pattern(pattern)`
- `def run_test_batch(patterns)`
- **class** `AdversarialTester`
  - *High-performance adversarial security tester.*
- `def main()`
- `def detection_rate()`
- `def false_positive_rate()`
- `def accuracy()`
- `def avg_processing_time_ms()`
- `def to_dict()`
- `def run(rounds, benign_ratio, save_failures)`

## `src/cohezion/security/rate_limiter.py`
> Rate Limiter - Token bucket algorithm.
- **class** `RateLimitConfig`
  - *Configuration for a rate limit.*
- **class** `TokenBucket`
  - *Token bucket for rate limiting.*
- **class** `RateLimitResult`
  - *Result of rate limit check.*
- **class** `RateLimiter`
  - *Rate limiter using token bucket algorithm.*
- `def get_rate_limiter()`
- `def consume(tokens)`
- `def time_until_available()`
- `def check(key, endpoint)`
- `def set_limit(endpoint, requests, window_seconds)`
- `def cleanup(max_age_seconds)`

## `src/cohezion/security/validators.py`
> Input Validation and Sanitization.
- **class** `ValidationResult`
  - *Validation result codes.*
- **class** `ValidationError`
  - *Validation error details.*
- `def validate_input(text, field_name, max_length)`
- `def sanitize_text(text)`
- `def validate_json_field(value, field_name, expected_type, required)`

## `src/cohezion/security/middleware.py`
> FastAPI Security Middleware.
- `def add_security_middleware(app)`
- `def create_context_harness(query, context)`

## `src/cohezion/security/attack_patterns.py`
> Attack Pattern Database for Adversarial Security Testing.
- **class** `AttackCategory`
  - *OWASP LLM Top 10 + Traditional attack categories.*
- **class** `AttackPattern`
  - *Single attack pattern with metadata.*
- `def get_pattern_count()`
- `def get_patterns_by_category(category)`
- `def generate_mutated_patterns(base_patterns, mutations_per_pattern)`
- `def mutate_pattern(text)`
- `def generate_test_batch(batch_size, include_benign_ratio, mutation_ratio)`

## `src/cohezion/security/prompt_guard.py`
> Prompt Guard - Defend against prompt injection attacks.
- **class** `ThreatLevel`
  - *Threat level classification.*
- **class** `PromptAnalysis`
  - *Result of prompt analysis.*
- `def normalize_text(text)`
- **class** `PromptGuard`
  - *Guard against prompt injection attacks with deobfuscation.*
- `def analyze(text, agent_name)`
- `def is_technical_context(text)`
- `def should_block(text)`
- `def get_stats()`

## `src/cohezion/providers/cohezion_swarm.py`
> Cohezion Swarm Provider - Drop-in replacement for Open Notebook's LLM.
- **class** `CohezionSwarmProvider`
  - *A custom provider that routes prompts not to a single LLM,*
- **class** `CohezionSwarmProviderSync`
  - *Synchronous wrapper for CohezionSwarmProvider.*
- `def get_metrics()`
- `def chat_complete(messages)`
- `def generate(prompt)`
- `def close()`

## `src/cohezion/reporting/reports_orchestrator.py`
- **class** `ReportsOrchestrator`
  - *Orchestrates the generation, containerization, and deployment of*
- `def generate_universe_report(scenario_name)`
- `def build_and_deploy(report_path)`
- `def run_scenario_analysis()`

## `src/cohezion/reporting/notebooks/report_20260121_163226.py`

## `src/cohezion/reporting/notebooks/report_20260121_163212.py`

## `src/cohezion/reporting/notebooks/fractal_convergence_20260121_164058.py`

## `src/cohezion/learning/skill_generator.py`
> Skill Generator - Automatically create skills from learned patterns.
- **class** `Pattern`
  - *A detected pattern that can become a skill.*
- **class** `PatternDetector`
  - *Detect recurring patterns in session logs.*
- **class** `SkillGenerator`
  - *Generate skills from mature patterns.*
- `def get_skill_generator()`
- `def record(pattern_name, description, example, keywords)`
- `def get_mature_patterns(min_occurrences)`
- `def generate_skill(pattern)`
- `def auto_generate(min_occurrences)`

## `src/cohezion/learning/capability_matrix.py`
> Capability Matrix Generator - Comprehensive capability analysis.
- **class** `Capability`
  - *A platform capability.*
- **class** `CapabilityMatrix`
  - *Complete capability matrix.*
- **class** `CapabilityAnalyzer`
  - *Analyzes and generates capability matrix.*
- `def generate_capability_matrix()`
- `def to_dict()`
- `def check_component_exists(name)`
- `def get_related_skills(name)`
- `def get_mcp_servers(name)`
- `def analyze_capability(name, description, domain)`
- `def generate_matrix()`
- `def save_matrix(matrix)`

## `src/cohezion/learning/semantic_analyzer.py`
> Semantic Analysis Engine - Analyze knowledge base for patterns and insights.
- **class** `SemanticCluster`
  - *A cluster of semantically related items.*
- **class** `CapabilityGap`
  - *An identified gap in capabilities.*
- **class** `SemanticAnalysis`
  - *Complete semantic analysis result.*
- **class** `SemanticAnalyzer`
  - *Analyzes universe nodes for semantic patterns.*
- `def run_semantic_analysis()`
- `def to_dict()`
- `def load_nodes()`
- `def extract_keywords(text)`
- `def get_node_text(node)`
- `def cluster_by_domain()`
- `def identify_gaps(clusters)`
- `def generate_skill_recommendations(clusters, gaps)`
- `def analyze()`
- `def save_analysis(analysis, output_path)`

## `src/cohezion/learning/multimodal_notebook.py`
> Multimodal Notebook - Interactive research notebooks with synthesis and podcast generation.
- **class** `NotebookInput`
  - *An input to the notebook.*
- **class** `NotebookCell`
  - *A cell in the notebook.*
- **class** `MultimodalNotebook`
  - *An interactive multimodal notebook.*
- **class** `NotebookEngine`
  - *Engine for multimodal notebook processing.*
- `def to_dict()`
- `def log_action(action, model, details)`

## `src/cohezion/learning/gemini_refiner.py`
> GEMINI.md Refiner - Automated rule updates from learnings.
- **class** `ProposedUpdate`
  - *A proposed update to GEMINI.md.*
- **class** `GeminiRefiner`
  - *Automatically propose and apply updates to GEMINI.md.*
- `def get_gemini_refiner()`
- `def to_markdown()`
- `def get_status()`

## `src/cohezion/simulations/quantum_quadrature_gravity_demo.py`
- `def add_tempic(x0, y0, amp, sigma)`
- `def curvature(phi, a, b)`