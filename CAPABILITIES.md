# CAPABILITIES (generated — do not hand-edit; see scripts/audits/capability_index.py)
_generated 2026-07-17T09:46:51; grep this BEFORE building anything new_

pkg actioner (2 files)
  actioner/engine.py: triage, load_actioned_ids, WorkQueueAPI, default_chat_fn, action_item, run_batch
pkg agent (6 files)
  agent/error_loop.py: ErrorClass, error_signature, ErrorClassifier, ReDispatchLedger, reflect
  agent/reflective_driver.py: ReflectiveDriver
  agent/reflective_orchestrator.py: run_with_reflection
  agent/skill_adaptor.py: mask_volatile, FaultAttribution, SkillUpdate, attribute_fault, propose_targeted_update, AcceptanceCheck, adapt_skill
  agent/unified_harness.py: ToolCall, ExecutionTrace, ToolRegistry, UnifiedAgent, autocontext_monitor
pkg agentjet (8 files)
  agentjet/context_optimizer.py: ModelContextProfile, OllamaContextManager, ContextOptimizer
  agentjet/embeddings.py: EmbeddingResult, EmbeddingContext, EmbeddingModel, FlumeVAEEmbeddingModel, GeminiEmbeddingModel, EmbeddingDistiller, EmbeddingOrchestrator
  agentjet/judger.py: PhiScoreJudger
  agentjet/task_reader.py: JourneyTaskReader
  agentjet/trainer.py: TrainingResult, AgentJetTrainer
  agentjet/unsloth_bridge.py: UnslothBridge
  agentjet/workflow.py: CohezionWorkflow
pkg agents (37 files)
  agents/adk_swarm/agi_specialists/metacognition_agent.py: MetacognitionAgent
  agents/adk_swarm/aimo_specialists/agent.py: AlgebraistAgent
  agents/adk_swarm/aimo_specialists/number_theorist.py: NumberTheoristAgent
  agents/adk_swarm/aimo_specialists/orchestrator.py: AIMOOrchestrator
  agents/analyst.py: AnalystAgent
  agents/arc_specialists/manifold_agent.py: ARCManifoldAgent
  agents/architect_agent.py: ArchitectAgent
  agents/base.py: AgentResponse, BaseAgent
  agents/critic.py: CriticAgent
  agents/ecoresilience_agent.py: SimulationMonitor, EcoResilienceAgent
  agents/evo_agent.py: EVOAgent
  agents/factory.py: AgentFactory
  agents/fleet_adapter.py: call_local_first, run_task_sync, get_default_execute_fn
  agents/generated/skill_0_agent.py: Skill0Agent
  agents/generated/skill_1_agent.py: Skill1Agent
  agents/lab_agent.py: LabAgent
  agents/prompt_injection_guard.py: wrap_untrusted
  agents/security_guard_agent.py: SecurityGuardAgent
  agents/specialists/_base.py: AgentCard, PlatformSpecialist, register, get_specialist, list_specialists, describe_all
  agents/specialists/claude_specialist.py: ClaudeSpecialist
  agents/specialists/ecoresilience_agent.py: ResilienceState, EcoResilienceAgent
  agents/specialists/gemini_specialist.py: GeminiSpecialist
  agents/specialists/mcp_specialist.py: MCPSpecialist
  agents/specialists/ollama_specialist.py: OllamaSpecialist
  agents/specialists/platform_coordinator.py: PlatformCoordinator
  agents/specialists/surreal_dba.py: SurrealDBA
  agents/specialists/vault_keeper.py: VaultKeeper
  agents/synthesizer.py: SynthesizerAgent
  agents/template_pipeline.py: GenerationResult, SyncResult, StaleAgent, TemplatePipeline
  agents/version_tracker.py: VersionTracker
pkg api (57 files)
  api/__init__.py: rate_limit_middleware, root, health, list_servers, list_tools, search_knowledge, list_skills, get_skill, run_debate, get_perspectives, get_metrics, list_notebooks, get_notebook, list_simulations, get_simulation, list_journeys, get_journey, get_journey_trajectory, create_demo_journey, visualize_journey, plot_journey, FlumeTrainRequest, FlumeTrainResponse, FlumeStatusResponse, TemplateParseRequest, TemplateParseResponse, FlumeEncodeRequest, FlumeEncodeResponse, FlumeDecodeRequest, FlumeDecodeResponse, FlumeInterpolateRequest, FlumeInterpolateResponse, FlumeLatentSpaceRequest, FlumeLatentSpaceResponse, RLTrainRequest, RLTrainResponse, RLPolicyResponse, train_flume, flume_status, flume_encode, flume_decode, flume_interpolate, flume_latent_space, parse_template, train_rl, get_rl_policy, RlStepRequest, RlStepResponse, RlEpisodeResponse, RlPolicyInfoResponse, rl_step, rl_episode, rl_policy_info, compare_calm_llm, SkillExecuteRequest, PlanStepOut, SkillExecuteResponse, CapabilityQueryRequest, CapabilityQueryResponse, execute_skill, find_capable_agent, list_prime_skills, AgentMetrics, AgentMetricsResponse, TrainingMetricsResponse, PipelineStageStatus, PipelineStatusResponse, SystemMetricsResponse, KnowledgeQueryRequest, KnowledgeQueryResponse, metrics_agents, metrics_training, metrics_pipeline, metrics_system, knowledge_query, TokenMetricsResponse, metrics_tokens, set_token_client, SwarmExecuteRequest, SwarmTaskResult, SwarmExecuteResponse, swarm_execute, CompoundMetricsResponse, metrics_compound, CompoundExecuteRequest, CompoundStepOut, CompoundExecuteResponse, compound_execute, CompoundFeedbackRequest, CompoundFeedbackResponse, compound_feedback, CompoundHealthResponse, compound_health, CompoundHistoryResponse, compound_history, TrainResponse, agentjet_train, agentjet_status, agentjet_models, verify_a2a_token, get_agent_card, list_agents, A2AMessageModel, A2ASendTaskRequest, send_a2a_task, get_a2a_task, cancel_a2a_task
  api/_helpers.py: compute_coherence, get_vae, get_rl_policy
  api/agui_events.py: AGUIEventType, AGUIEvent, RunStartedEvent, RunFinishedEvent, TextMessageEvent, ToolCallEvent, StateSnapshotEvent, StateDeltaEvent, CustomEvent, narration_event, phase_transition_event, universe_tick_event
  api/fail_hook.py: async_failure
  api/journey_status.py: JourneyStatusService, get_journey_status, list_active_journeys, stream_journey_status, start_journey, pause_journey, resume_journey
  api/journeys.py: load_journey, load_all_journeys, list_journeys, get_journey, analyze_journeys, journey_thermodynamics, journey_topology, journey_anomaly, journey_archetype
  api/observability_endpoints.py: get_analytics, get_unified_metrics, get_cache_analytics, get_token_efficiency, get_guardrail_analytics, get_resource_analytics, get_health_score, get_metric_trend, get_full_dashboard, reset_metrics
  api/research_endpoints.py: ResearchConfigRequest, MultiAgentConfigRequest, ResearchResponse, ResearchResultResponse, start_research, start_multi_agent_research, get_research_status, get_research_results, stop_research, get_experiment_log, get_research_dashboard
  api/routes/a2a.py: verify_a2a_token, A2AMessageModel, A2ASendTaskRequest, get_agent_card, send_a2a_task, get_a2a_task, cancel_a2a_task
  api/routes/agentjet.py: TrainRequest, TrainResponse, agentjet_train, agentjet_status, agentjet_models
  api/routes/agui.py: compute_cosmogony, cosmogony_stream, stream_cosmogony, get_a2ui_catalog
  api/routes/compound.py: CompoundExecuteRequest, CompoundStepOut, CompoundExecuteResponse, CompoundFeedbackRequest, CompoundFeedbackResponse, CompoundHealthResponse, CompoundHistoryResponse, compound_execute, compound_feedback, compound_health, compound_history
  api/routes/eigent.py: WorkforceRequest, WorkforceResponse, run_long_horizon_task, create_workforce, get_workforce_status
  api/routes/fleet.py: get_fleet_status, register_service, trigger_health_check, get_fleet_events
  api/routes/flume.py: FlumeTrainRequest, FlumeTrainResponse, FlumeStatusResponse, FlumeEncodeRequest, FlumeEncodeResponse, FlumeDecodeRequest, FlumeDecodeResponse, FlumeInterpolateRequest, FlumeInterpolateResponse, FlumeLatentSpaceRequest, FlumeLatentSpaceResponse, train_flume, flume_status, flume_encode, flume_decode, flume_interpolate, flume_latent_space
  api/routes/flume_inline.py: FlumeTrainRequest, FlumeTrainResponse, FlumeStatusResponse, FlumeEncodeRequest, FlumeEncodeResponse, FlumeDecodeRequest, FlumeDecodeResponse, FlumeInterpolateRequest, FlumeInterpolateResponse, FlumeLatentSpaceRequest, FlumeLatentSpaceResponse, train_flume, flume_status, flume_encode, flume_decode, flume_interpolate, flume_latent_space
  api/routes/journey_nexus.py: viz_frame, stream_viz, evo_snapshot, stream_evo, quadrature_vote, narrate, OmniChatRequest, omni_chat
  api/routes/journeys_legacy.py: list_journeys, get_journey, get_journey_trajectory, create_demo_journey, visualize_journey, plot_journey, compare_calm_llm
  api/routes/knowledge.py: SearchRequest, KnowledgeQueryRequest, KnowledgeQueryResponse, search_knowledge, list_skills, get_skill, knowledge_query
  api/routes/mcp.py: list_servers, list_tools
  api/routes/metrics.py: AgentMetrics, AgentMetricsResponse, TrainingMetricsResponse, PipelineStageStatus, PipelineStatusResponse, SystemMetricsResponse, TokenMetricsResponse, CompoundMetricsResponse, metrics_agents, metrics_training, metrics_pipeline, metrics_system, metrics_tokens, set_token_client, metrics_compound
  api/routes/notebooks.py: list_notebooks, get_notebook, list_simulations, get_simulation
  api/routes/rl.py: RLTrainRequest, RLTrainResponse, RLPolicyResponse, RlStepRequest, RlStepResponse, RlEpisodeResponse, RlPolicyInfoResponse, train_rl, get_rl_policy, rl_step, rl_episode, rl_policy_info
  api/routes/skills.py: SkillExecuteRequest, PlanStepOut, SkillExecuteResponse, CapabilityQueryRequest, CapabilityQueryResponse, execute_skill, find_capable_agent, list_prime_skills
  api/routes/swarm.py: DebateRequest, DebateResponse, SwarmExecuteRequest, SwarmTaskResult, SwarmExecuteResponse, run_debate, get_perspectives, get_metrics, swarm_execute
  api/routes/templates.py: TemplateParseRequest, TemplateParseResponse, parse_template
  api/routes/training.py: TrainingRun, TrainingHistoryResponse, get_training_history, get_best_run, get_algorithm_reward_matrix
  api/security.py: rate_limit, requires_auth, get_current_user, verify_a2a_token
  api/services/anima.py: AnimaStatusResponse, NarrationResponse, AskRequest, AskResponse, SpeakRequest, SpeakResponse, AnimaService, get_anima_service, get_anima_status, narrate, ask_anima, speak
  api/services/architecture.py: GraphNode, GraphEdge, ArchitectureGraph, get_architecture_graph
  api/services/brand.py: HIHOPalette, BrandColors, BrandIdentity, BrandThemeResponse, get_brand_theme
  api/services/flume.py: FlumeTrainRequest, FlumeTrainResponse, FlumeStatusResponse, FlumeEncodeRequest, FlumeEncodeResponse, FlumeDecodeRequest, FlumeDecodeResponse, FlumeInterpolateRequest, FlumeInterpolateResponse, get_vae, compute_coherence, train_flume_service, get_flume_status, flume_encode_service, flume_decode_service, flume_interpolate_service
  api/services/forge.py: HardwareTelemetry, BenchmarkRequest, BenchmarkResponse, get_telemetry, run_benchmark, get_local_leaderboard
  api/services/genesis.py: BlochVectorResponse, SpinorStateResponse, SpinorFromValuesRequest, SpinorRotateRequest, get_hiho_spinor, spinor_from_values, rotate_spinor, sweep_bloch_sphere, check_su2_algebra, CoolRequest, CosmogonyStateResponse, CosmogonySetTemperatureRequest, get_cosmogony_state, cool_universe, set_universe_temperature, reset_cosmogony, get_free_energy_landscape, get_cosmogony_12d_state, get_fiber_bundle_state, get_gauge_state, LagrangianTrajectoryRequest, simulate_lagrangian_trajectory, get_manifold_summary, NarrateRequest, get_narration_stages, narrate_stage, narrate_concept, narrate_custom
  api/services/graphify.py: GraphEntity, GraphRelation, GraphifyResult, GraphifyService
  api/services/journey_corpus_seeder.py: seed_stub_corpus
  api/services/journey_loader.py: load_journey
  api/services/journey_nexus.py: EVOEvent, QuadratureOutcome, OmniChatOutcome, NarrateResult, JourneyNexus
  api/services/modules.py: HamiltonianResponse, ManifoldLagrangeResponse, PhononResponse, TriuneResponse, EmergenceResponse, MorphospaceResponse, LCSPResponse, RewardsResponse, CoherenceResponse, EVOLifecycleResponse, BioelectricBridgeResponse, TensorBeamData, HIHOBridgeData, PersistenceData, LagrangeRequest, StateRequest, simulate_hamiltonian, compute_lagrange_points, evolve_phonons, get_triune_coherence, detect_emergence, analyze_morphospace, predict_lcsp, compute_rewards, get_tensor_beam_data, get_hiho_bridge_data, get_persistence_diagram, get_system_coherence, simulate_evo_lifecycle, bioelectric_step
  api/services/modules_api.py: HamiltonianResponse, ManifoldLagrangeResponse, PhononResponse, TriuneResponse, EmergenceResponse, MorphospaceResponse, LCSPResponse, RewardsResponse, CoherenceResponse, EVOLifecycleResponse, BioelectricBridgeResponse, TensorBeamData, HIHOBridgeData, PersistenceData, LagrangeRequest, StateRequest, simulate_hamiltonian, compute_lagrange_points, evolve_phonons, get_triune_coherence, detect_emergence, analyze_morphospace, predict_lcsp, compute_rewards, get_tensor_beam_data, get_hiho_bridge_data, get_persistence_diagram, get_system_coherence, simulate_evo_lifecycle, bioelectric_step
  api/services/mycelium_api.py: NetworkStatusResponse, SporeResponse, SporesQueryResponse, SkillResponse, SkillsResponse, PiTurnLog, PiTurnAck, log_pi_turn, get_mycelium_network, query_spores, get_mycelium_skills
  api/services/ouroboros_api.py: HealthResponse, HealingHistoryResponse, RulesResponse, get_ouroboros_health, get_healing_history, get_ouroboros_rules
  api/services/physics_extended.py: BioelectricResponse, NaturalCapitalResponse, CosmogonyChainResponse, HamiltonianSimulateResponse, TriuneStateResponse, PhononStateResponse, StabilityWellResponse, MorphospaceWellsResponse, LCSPPredictResponse, EmergenceDetectResponse, get_bioelectric_state, get_natural_capital, get_cosmogony_full_chain, get_hamiltonian_simulate, get_triune_state, get_phonon_state, get_morphospace_wells, get_lcsp_predict, get_emergence_detect, BECStatusResponse, MercuryLatticeResponse, ColibreStatusResponse, MHDStatusResponse, BismuthResponse, ToroidalResponse, TensorMetricResponse, get_bec_status, get_mercury_status, get_colibre_status, get_mhd_status, get_bismuth_status, get_toroidal_status, get_tensor_metric_status, BECStatusResponse, MercuryLatticeResponse, ColibreStatusResponse, MHDStatusResponse, BismuthResponse, ToroidalResponse, TensorMetricResponse, get_bec_status, get_mercury_status, get_colibre_status, get_mhd_status, get_bismuth_status, get_toroidal_status, get_tensor_metric_status, BECStatusResponse, MercuryLatticeResponse, ColibreStatusResponse, MHDStatusResponse, BismuthResponse, ToroidalResponse, TensorMetricResponse, get_bec_status, get_mercury_status, get_colibre_status, get_mhd_status, get_bismuth_status, get_toroidal_status, get_tensor_metric_status
  api/services/rl.py: RLTrainRequest, RLTrainResponse, RLPolicyResponse, RlStepRequest, RlStepResponse, RlEpisodeResponse, RlPolicyInfoResponse, get_rl_policy_singleton, train_rl_service, get_rl_policy_service, rl_step_service, rl_episode_service, rl_policy_info_service
  api/services/skills.py: TemplateParseRequest, TemplateParseResponse, parse_template_service
  api/services/universe.py: UniverseStateResponse, EvoHealthEntry, HIHOStatusReport, CAAnalysis, TopologyPairEntry, TopologyData, SynthesisReport, PerturbRequest, UniverseStateService, get_universe_service, get_universe_state, tick_universe, get_synthesis_report, perturb_universe, get_universe_history, get_history_summary, stream_universe
  api/services/world_model.py: TrainRequest, PredictRequest, SimulateRequest, SurpriseRequest, get_status, train_model, predict_next, simulate_trajectory, compute_surprise
  api/services/worldviews.py: list_traditions, get_tradition_detail, list_convergences, get_step_comparison, get_vault_graph_data, get_vault_tradition_subgraph, get_vault_clusters
  api/sse_queue_bounds.py: BoundedAsyncQueue, create_bounded_queue, safe_queue_put
  api/streaming.py: StreamingInferenceRequest, SessionListResponse, stream_inference, resume_session, cancel_session, list_active_sessions, get_session_status, close_session_endpoint
  api/telemetry.py: ConnectionManager, telemetry_endpoint, broadcast_state
  api/work_queue_router.py: WorkItemCreate, WorkItemPatch, list_items, create_item, patch_item, delete_item, kanban_ui
pkg arc (14 files)
  arc/codec.py: ARCCodec, encode_task, decode_prediction, grids_equal
  arc/data_loader.py: list_tasks, load_task, load_all
  arc/evaluate_local.py: load_data, grids_equal, score_submission, print_scorecard
  arc/grid_pipeline.py: encode_grid, decode_grid, decode_from_latent, validate_grid, batch_encode, batch_decode, grid_hash, grid_summary, verify_roundtrip, verify_pipeline_sanity
  arc/pattern_extractor.py: CompoundRule, PatternExtractor
  arc/solver.py: SolverState, ucb1_score, derive_color_ops, beam_search, solve_task, evaluate_on_subset, update_ksearch
  arc/submission.py: PredictionProvenance, SubmissionBuilder, verify_submission
  arc/tracks/arc_agi_2.py: ARCAGI2Result, ARCAGI2Pipeline
  arc/tracks/arc_agi_3.py: InteractiveAttempt, ARCAGI3Result, ARCAGI3Pipeline
  arc/tracks/orchestrator.py: TrackRun, MultiTrackOrchestrator
  arc/tracks/paper_track.py: PaperSection, PaperTrackResult, PaperTrackPipeline
  arc/transforms.py: rotate_90, rotate_180, rotate_270, flip_horizontal, flip_vertical, transpose, gravity_fall, scale_up_2, scale_down_2, crop_to_content, dilate, erode, outline, extract_largest_component, flood_fill_expand, remove_background, detect_lines, count_objects, pattern_repeat_row_col, tile_3x3, tile_grid, repeat_rows, repeat_cols, kronecker_mask_tile, find_largest_object, object_bbox, fill_interior, remove_small_objects, color_map_by_object_size, replace_8_to_7, replace_1_to_2, replace_3_to_4, replace_2_to_7, replace_3_to_8, replace_5_to_7, replace_1_to_6, replace_8_to_1, replace_0_to_bg, recolor_enclosed, color_replace, color_swap, color_filter_keep, color_map_learned, color_majority, color_background, recolor_interior, make_color_swap, make_color_remap, apply_chain, get_timing_report, grid_symmetry_reflect, object_center_of_mass
pkg audio (6 files)
  audio/bioacoustic_encoder.py: BioacousticEncoder, BirdCLEFDataProduct
  audio/moshi_client.py: MoshiClient
  audio/narrator.py: CosmoNarrator, get_narrator
  audio/neural_audio.py: AudioStreamStatus, AudioChunk, AudioStreamState, NeuralAudioStream
  audio/protoclr.py: ProtoCLR, DomainInvarianceHarness
pkg benchmarks (9 files)
  benchmarks/agentic_benchmark.py: AgenticTask, TaskResult, AgenticBenchmark
  benchmarks/agentic_metrics.py: AgenticResults, AgenticMetrics
  benchmarks/benchmark_suite.py: IntrinsicResults, ComparativeResults, PredictiveResults, HumanEvalPackage, BenchmarkReport, CohezionBenchmark
  benchmarks/coding_benchmark.py: CodeTask, CodeResult, SWEBenchRunner, CohezionCodeBenchmark
  benchmarks/cyber_benchmark.py: CTFChallenge, CTFResult, CyberBenchmark
  benchmarks/datamesh_query.py: DatameshBenchmarkResult, benchmark_datamesh_queries, main
  benchmarks/mock_evaluation.py: EvaluationResult, MockBenchmarkEvaluator, main
  benchmarks/orchestrator.py: BenchmarkSuiteResults, UnifiedBenchmarkOrchestrator
pkg cache (7 files)
  cache/cache_warmer.py: CacheWarmer
  cache/lemonade_encoder.py: LemonadeEncoder, get_lemonade_encoder, reset_lemonade_encoder
  cache/redis_cache.py: RedisSemanticCache
  cache/semantic_cache.py: CacheEntry, SemanticCache
  cache/sentence_encoder.py: SentenceTransformerEncoder, get_encoder
  cache/text_encoder.py: SemanticTextEncoder, get_text_encoder, reset_encoder
pkg cli (3 files)
  cli/main.py: quickstart, hello, version, main, get_swarm_service, swarm_run, swarm_debate, swarm_simulate, swarm_review, dashboard_start, config_show, config_validate, explore_skills, explore_journey, demo_flume, demo_nexus, demo_journey, universe_seed, universe_list, ouroboros_status, ouroboros_heal, ouroboros_history
pkg cockpit (2 files)
  cockpit/daemon_state.py: read_task_queue, read_graph_counts, read_work_queue, read_gap_analysis, read_lemonade_health, tail_daemon_log, run_feeder, add_manual_task, ask_local_advisor
pkg competition (69 files)
  competition/arc_agi_3/action_aware_agent.py: ActionAwareAgent, run_action_aware_agent
  competition/arc_agi_3/experiential_agent.py: Experience, WorldModel, grid_signature, agent_position, compute_reward, ExperientialAgent, run_experiential_learning_spike
  competition/arc_agi_3/experiential_feedback.py: load_cross_project_learnings, analyze_state_abstraction_failure, generate_ouroboros_report, update_cohezion_skills, update_mycelium_map, update_dynamic_levers, run_feedback_loop
  competition/arc_agi_3/goal_aware_explorer.py: find_regions, find_player, find_target_regions, GoalAwareExplorer, run_goal_aware_explorer
  competition/arc_agi_3/object_clicker.py: find_click_targets, run_object_clicker
  competition/arc_agi_3/phi4_agent.py: grid_to_ascii, Phi4Agent, run_phi4_agent
  competition/arc_agi_3/systematic_explorer.py: grid_diff, find_player_pos, SystematicExplorer, run_systematic_explorer
  competition/arc_agi_3/vmodel_gate.py: VModelGateConfig, BaselineResult, VModelGate, main
  competition/arc_prize_paper_track/ablation_study.py: build_ops_subset, run_ablation
  competition/arc_prize_paper_track/gate_precision.py: structural_alignment_score, gate_score, measure_gate_precision
  competition/arc_prize_paper_track/gate_precision_v2.py: structural_alignment_score, collecting_search
  competition/arc_prize_paper_track/generate_figure1.py: draw_compound_loop
  competition/arc_prize_paper_track/score_draft.py: score_draft
  competition/arc_prize_paper_track/skill_refinement_test.py: task_signature, run_with_fixed_strategies, run_with_skill_refinement
  competition/arc_solver.py: deepcopy_grid, identity, flip_horizontal, flip_vertical, transpose, rotate_90, rotate_180, rotate_270, find_objects, bounding_box, crop_to_object, remove_background, count_colors, grid_to_colors, replace_color, swap_colors, keep_only, invert_colors, pad_to_object, fill_holes, border, interior, upsample, downsample, mirror_horizontal, mirror_vertical, diagonal_symmetry, move_objects_up, order_objects_by_size, gravity_down, gravity_up, gravity_left, gravity_right, infer_color_map, color_map_wrapper, deduplicate_rows, deduplicate_cols, hconcat, vconcat, extend_lines_h, extend_lines_v, compress_repeating, tile_grid, get_all_ops, apply_program, grids_equal, search_program, solve_task
  competition/evaluate_solver.py: evaluate
  competition/experience_solver.py: try_program_on_train, build_prediction, solve_with_experience, run_evaluation
  competition/experience_vault.py: TaskSignature, extract_signature, sig_distance, ExperienceEntry, ExperienceVault
  competition/gemma_hackathon/app.py: run_agent
  competition/gemma_hackathon/crisis_compound_demo.py: CrisisReport, ResponseAction, ScenarioOutcome, Scenario, query_gemma, CrisisCompoundAgent, run_demo
  competition/gemma_hackathon/dashboard.py: EpisodeMetrics, render_episode_metrics, render_training_progress
  competition/gemma_hackathon/kaggle_submission.py: CrisisReport, ResponseAction, ScenarioOutcome, query_ollama, CrisisCompoundAgent, main
  competition/gemma_hackathon/kernel.py: CrisisReport, ResponseAction, ScenarioOutcome, simulate_reasoning, CrisisCompoundAgent, main
  competition/gemma_hackathon/training_loop.py: EpisodeResult, simulate_episode, run_training_loop
  competition/kaggle_submission_arc.py: solve_task, main
  competition/llm_fallback.py: llm_solve
  competition/nemotron_solver/kaggle_notebook.py: parse_examples, classify_problem, extract_test_input, solve_gravity, solve_unit_conversion, int_to_roman, solve_numeral, solve_bit_manip, solve_encryption, solve_equations, solve
  competition/nemotron_solver/kaggle_pure_symbolic.py: parse_examples, classify_problem, extract_test_input, solve_gravity, solve_unit_conversion, int_to_roman, solve_numeral, solve_bit_manip, solve_encryption, solve_equations, solve
  competition/nemotron_solver/solve.py: solve_with_model, parse_examples, classify_problem, extract_test_input, solve_gravity, solve_unit_conversion, int_to_roman, solve_numeral, solve_bit_manip, solve_equations, solve_encryption, solve, evaluate
  competition/nemotron_solver/submit.py: generate_submission
  competition/nemotron_solver/test_model.py: test_problems
  competition/nemotron_solver/train_local_submit.py: prepare_training_data, load_base_model, setup_lora, train
  competition/nemotron_solver/train_lora_kaggle.py: parse_examples, classify_problem, compare_answers, int_to_roman, solve_gravity, solve_unit_conversion, solve_numeral, solve_bit_manip, solve_encryption, solve_equations, extract_test_input, solve, trace_numeral, trace_gravity, trace_unit_conversion, trace_bit_manip, trace_encryption, trace_equations, build_training_data, tokenize_with_mask, main
  competition/neurogolf/coord_conv.py: CoordConvARCSolver, pad_grid, grids_equal, train_on_task, predict
  competition/neurogolf/eval.py: pad_grid, grids_equal, train_on_task, evaluate_task
  competition/neurogolf/generalize_test.py: TinyConvARCV3, pad_grid, grids_equal, train_on_task, predict
  competition/neurogolf/hybrid_ensemble.py: TinyConvARCV3, pad_grid, grids_equal, train_on_task, predict_conv, predict_dsl, predict_fallback
  competition/neurogolf/hybrid_selector.py: GridEncoder, ProgramSelector, pad_grid, grids_equal
  competition/neurogolf/kaggle_submission.py: TinyConvARCV3, pad_grid, train_on_task, predict
  competition/neurogolf/meta_train.py: TinyConvARCV3, pad_grid, grids_equal
  competition/neurogolf/sweep_hidden.py: TinyConvARCV2, pad_grid, train_on_task, evaluate
  competition/neurogolf/test_time_sweep.py: TinyConvARCV3, pad_grid, grids_equal, train_and_predict
  competition/neurogolf/tiny_conv_arc.py: TinyConvARCSolver, test_forward
  competition/neurogolf/tiny_conv_v2.py: TinyConvARCV2, pad_grid, train_on_task, evaluate
  competition/neurogolf/tiny_conv_v3.py: TinyConvARCV3, pad_grid, train_on_task, evaluate
  competition/neurogolf/tiny_transformer.py: TinyTransformerARCSolver, pad_grid, grids_equal, train_on_task, predict
  competition/neurogolf/validate_100.py: TinyConvARCV2, pad_grid, train_on_task, evaluate
  competition/orchestrator/agents/arc_solver_agent.py: ARCSolverAgent
  competition/orchestrator/agents/base_agent.py: BaseAgent
  competition/orchestrator/agents/gemma_hackathon_agent.py: GemmaHackathonAgent
  competition/orchestrator/agents/neurogolf_agent.py: NeuroGolfAgent
  competition/orchestrator/agents/paper_track_agent.py: PaperTrackAgent
  competition/orchestrator/agents/sei_accelathon_agent.py: SeiAccelathonAgent
  competition/orchestrator/benchmark_context_scaling.py: main
  competition/orchestrator/benchmark_lemonade.py: main
  competition/orchestrator/benchmark_local_model.py: benchmark_model, run_benchmark, main
  competition/orchestrator/main.py: CompetitionOrchestrator
  competition/orchestrator/model_dispatcher.py: GenerationResult, ModelDispatcher
  competition/orchestrator/resource_guard.py: MemorySnapshot, ResourceGuard
  competition/orchestrator/review_paper.py: read_draft, review_paper
  competition/orchestrator/test_gemma_readiness.py: main
  competition/portfolio_manager.py: expected_value, alignment_gate, main
  competition/sei_accelathon/assessment.py: assess_sei_prize_ev, assess_existing_mcp_readiness
  competition/sei_accelathon/sei_compound_server.py: SeiOperation, SeiCompoundSession, demonstrate_compound_session
pkg compound (198 files)
  compound/__init__.py: make_executor
  compound/adversarial.py: AdversarialFinding, RalphLoppsReviewer, MultiperspectiveReviewBoard, BlueHatReviewer, GreenHatReviewer, YellowHatReviewer
  compound/agi_reasoning.py: ReasoningModel, AGINode, AGIEvaluator
  compound/aimo_reasoning.py: ReasoningModel, ReasoningNode, ProcessRewardModel, AIMOScaler
  compound/analytics/engine.py: AnalysisConfig, ExecutionAnalyzer, SimpleAnalyzer
  compound/analytics/metrics.py: MetricsSnapshot, MetricsCollector, SimpleMetrics
  compound/aoep_scorecard.py: AOEPScore, AOEPScorecard
  compound/autodqa.py: DQAResult, AutoDQA
  compound/autoharness.py: AutoHarnessSynthesizer
  compound/autonomous_loop/coordinator.py: LoopConfig, LoopTask, SprintResult, RunReport, LoopCoordinator
  compound/autonomous_loop/executor.py: ImprovementExecutor
  compound/autonomous_loop/local_executor.py: warmup_tiers, get_tier_health, LoopTickSweeper, LocalImprovementExecutor
  compound/autonomous_loop/quality_tracker.py: MarkovQualityTracker
  compound/autonomous_loop/rzero_challenger.py: TaskAttempt, EpisodeResult, ChallengerAgent, SolverAgent, RZeroChallengerExecutor
  compound/autoresearch.py: ExecutionMetrics, ImprovementOpportunity, AutoresearchEngine, VaultLearningCapture, AsyncMetricsSkillRefiner, ExperientialLearningLoop
  compound/batch_executor.py: CompoundTask, BatchCompoundResult, BatchableExecutor, BatchExecutorFactory
  compound/batch_sizer.py: BatchExecutionMetrics, BatchSizePredictor, get_batch_size_predictor
  compound/behavioral_eval.py: BehaviorProperty, BehaviorTestResult, BehavioralEvalReport, BehavioralEvaluator
  compound/cache_persistence.py: CachePersistence, WarmCacheLoader
  compound/capability_matrix.py: CapabilityEntry, CapabilityGap, FinetuneCandidate, CapabilityMatrix
  compound/chronos.py: classify_deferrable, ChronosJob, ChronosRegistry, get_chronos, ChronosAdvisor, install_chronos_advisor, ControlResult, ChronosController
  compound/clr_quality_gate.py: CLRQualityGate
  compound/coherence_v3.py: clamp01, logprob_to_quality, coherence_v1, base_quality, verbal_score, reasoning_depth, CoherenceV3Result, compute_coherence_v3, compute_coherence, spine_liveness_ok, workspace_occupancy, default_igpu_grader, default_igpu_entailment
  compound/cohezion_state.py: get_full_state, format_state_for_context
  compound/compat.py: CompoundExecutor, ExecutionResult, CompoundCycleResult, CompoundCycleReport
  compound/compound_engine.py: CompoundEngine
  compound/compound_feeder.py: feed_compound_tasks
  compound/compound_health_oracle.py: HealthAssessment, CompoundHealthOracle
  compound/compound_persist.py: persist_cycle
  compound/compound_score_tracker.py: CompoundScoreWindow
  compound/config.py: CompoundConfig
  compound/consortium_instigator.py: Severity, AttackCategory, AttackVector, AttackRunResult, ConsortiumInstigator
  compound/context_integration.py: ContextLoadError, ContextCoherenceError, ContextManager, CompoundContextMixin
  compound/context_policy.py: TaskProfile, ContextBudget, ContextSignals, ContextPolicy
  compound/copernicus_bridge.py: CopernicusState, CopernicusBridge
  compound/core/batch_processor.py: BatchResult, BatchProcessor, SimpleBatch
  compound/core/executor.py: ExecutionConfig, CompoundExecutor, execute_simple
  compound/cosmic_fire_protocol.py: CosmicFireEvent, CosmicFireProtocol
  compound/cron_manager.py: CronJob, CronManager, schedule_standard_jobs
  compound/daemon/workflow_initializer.py: CompoundEngineeringWorkflowInitializer, get_workflow_initializer
  compound/degradation_detector.py: AlertSeverity, DegradationAlert, SkillDriftDetector, MetricBaseline, DegradationDetector
  compound/degradation_health.py: HealthObservabilityMixin
  compound/design_review_report.py: GateLevel, FindingSeverity, Finding, DesignReviewReport, DRRGenerator
  compound/difficulty_estimator.py: DifficultyEstimator
  compound/distillation_engine.py: RegimeAxiom, DistillationEngine
  compound/distillation_pipeline.py: run_distillation
  compound/dual_loop_optimizer.py: DualLoopOptimizer
  compound/dynamic_compound_system.py: DynamicExecutionResult, DynamicCompoundSystem, create_dynamic_system, quick_execute
  compound/dynamic_system_integration.py: CircuitBreakerRouterAdapter, ProactivePoolAdapter, AdaptiveCostAdapter, EventLoggingAdapter, VaultPatternAdapter, DynamicSystemCoordinator, LemonadeAdapter, create_integrated_dynamic_system
  compound/eco_symphony.py: CompoundEcoSymphony, EcoResilienceCompoundEngine
  compound/error_classifier.py: classify_error
  compound/evo_pipeline.py: encode_journey_as_evo, persist_evo_to_surreal, persist_evo_to_obsidian, capture_evo
  compound/evolution_training_bridge.py: EvolutionTrainingConfig, EvolutionTrajectory, TraceToTrajectoryConverter, LatentNoveltyScorer, TrainingSignals, EvolutionTrainingSignalGenerator, EvolutionTrainingExporter, EvolutionRoundResult, EvolutionTrainingPipeline, ModelEvaluationResult, FitnessEvaluator
  compound/evopolicygym_adapter.py: EvoPolicyFeedback, SkillRefinerEvoPolicyAgent, EvoPolicyGymBenchmark, run_benchmark
  compound/exec_sandbox_audit.py: ExecSite, unsandboxed_exec_paths
  compound/execute_fn_aligned.py: execute_fn_aligned
  compound/executor.py: ExecutionResult, CompoundExecutor
  compound/executor_factory.py: ExecutorFactory, make_executor
  compound/executor_helpers/guardrail_runner.py: run_async_guardrail
  compound/executor_helpers/refinement_reader.py: load_refined_guidance
  compound/executor_helpers/template_matcher.py: try_template_match
  compound/executor_helpers/vault_integration.py: fetch_experience_guidance
  compound/executor_integration.py: ExecutorIntegrationMixin
  compound/exp_persistence/accumulator.py: PersistenceAccumulator, get_accumulator
  compound/exp_persistence/journey.py: JourneyPersistence, get_journey_persistence
  compound/exp_persistence/vault.py: ExecutionContext, VaultLogger, get_vault_logger
  compound/experiment_analytics.py: load_experiment_records, compute_experiment_stats, find_retirement_candidates, compute_hiho_balance, get_analytics_report, compute_experiment_velocity
  compound/experiment_correlator.py: compute_temporal_correlation, find_strong_correlations
  compound/experiment_recommender.py: recommend_next_experiments, get_session_recommendation_summary
  compound/experiment_scheduler.py: ExperimentScheduler
  compound/failure_attributor.py: FailureAttribution, FailureAttributor
  compound/feedback_loop.py: RetryStrategy, RetryAttempt, FeedbackLoopResult, CompoundFeedbackLoop, CompoundFeedbackLoopFactory
  compound/fleet_health_specialist.py: FleetHealthSnapshot, FleetHealthSpecialist
  compound/friction_metric.py: FrictionReading, FrictionMetric
  compound/gaia_loop.py: GoalResult, GaiaLoop
  compound/geometric_correspondence.py: CorrespondenceMatch, geometric_correspondence, correspondence_is_discriminating, correspondences_from_backlog, compound_context_for
  compound/global_metrics_aggregator.py: InstanceMetrics, TimeWindowMetrics, SkillMetrics, GlobalMetricsAggregator, get_global_aggregator, reset_global_aggregator
  compound/greek_parameters.py: GreekParameters
  compound/group_evolution.py: ArchivePersister, TaskSuccessVector, NoveltyScorer, SelectionStrategy, AgentCandidate, PerformanceNoveltySelector, ExperienceTraceType, ExperienceTrace, GroupExperiencePool, EvolutionDirective, ArchiveEntry, GroupEvolutionEngine
  compound/group_evolution_persistence.py: SurrealArchivePersister
  compound/guidance_enhancer.py: EnhancedGuidance, GuidanceEnhancer
  compound/hardware_monitor.py: HardwareMetrics, HardwareMonitor, get_hardware_monitor
  compound/harness.py: HarnessSynthesizer
  compound/harness_benefit.py: HarnessBenefitRecord, HarnessBenefitTracker
  compound/harness_tuning_specialist.py: HarnessTuningSpecialist
  compound/health.py: CompoundHealthReport, SkillHistoryResponse
  compound/health_monitor.py: test_autoresearch_available, test_error_classifier_available, test_session_metrics_available, get_health_report, test_loop_visualizer_available, test_compound_engine_available, test_experiment_scheduler_available, test_experiment_recommender_available, get_health_report
  compound/hiho_lm_gate.py: check_quality, ppl_score, check_sycophancy, check_sycophancy_v5, reset
  compound/holographic_projection.py: text_to_latent, encode_step_sequence, holographic_project, step_to_axiomatic
  compound/inflection_detector.py: Severity, AnomalyDetection, InflectionDetector, InflectionDetectorFactory
  compound/intake_specialist.py: IntakeGreeting, IntakeSpecialist
  compound/intent_classifier.py: IntentClassifier
  compound/invest/bridge.py: InvestState, InVESTBridge
  compound/jepa_gate.py: PreExecutionVerdict, JepaGate
  compound/journey_analyzer.py: ArchetypeType, ClusteringResult, AnomalyReport, PatternLibrary, ArchetypeModel, ThermoAnalysis, TopoAnalysis, JourneyReport, JourneyAnalyzer
  compound/journey_spatial.py: AllocentricMap, journey_allocentric_map
  compound/journey_to_training.py: ValidationResult, JourneyToTrainingBridge
  compound/journey_tracker.py: OperationType, classify_state_category, TrajectoryPoint, Journey, JourneyTracker, JourneyTrackerFactory
  compound/lemonade_recipes.py: RecipeOptions, BaseRecipe, UserVariant
  compound/lemonade_world_model.py: FlumeWorldModel, build_live_jepa_gate
  compound/local_inference.py: get_session_token_record, get_recommended_concurrency, lemonade_available, make_local_execute_fn
  compound/long_horizon_task.py: get_context_usage_percent, TaskStepResult, LongHorizonTask
  compound/loop_daemon.py: LoopDaemon
  compound/loop_telemetry.py: LoopTelemetry, loop_telemetry, StallReport, detect_loop_stall, LoopProgressDelta, loop_progress_delta, RegressionReport, detect_loop_regression
  compound/loop_visualizer.py: render_hiho_bar, render_experiment_table, render_session_summary
  compound/mcp_tool_audit.py: ToolDescriptionFinding, tool_description_audit
  compound/metrics.py: ExecutionRecord, RefinementRecord, CycleRecord, CompoundMetricsCollector, get_collector, reset_collector
  compound/metrics_persistence.py: MetricsPersistence
  compound/model_quality_classifier.py: FailureMode, RecommendedAction, ExecutionRecord, QualityForecast, ActionRecommendation, QualityPredictor, ModelQualityClassifier
  compound/models.py: ExecutionStatus, IntentType, ExecutionMetrics, ExecutionResult, Task, ExecutionContext, AnalysisReport, BatchConfig, ThermodynamicState, ConstraintType, ExecutionConstraint, SuccessCriterion, DriftSignal, ConstraintViolation, CriterionFailure, ExecutionAlignment, HumanRequest, SessionCheckpoint, CompoundCycleResult, CompoundCycleReport
  compound/moe_skill_router.py: MoESkillRouter
  compound/multi_agent_compound_bridge.py: CompoundAgentResult, MultiAgentCompoundBridge, execute_with_compound_agents, CompoundMultiAgentExecutor
  compound/oom_guard.py: ComputeTier, MemorySnapshot, get_available_ram_gb, audit_heavy_models, OOMRisk, check_oom_risk, safe_model_for_task, safe_load, prefetch_for_next_task, run_startup_audit, BackendEntry, get_live_topology, tier_for_model, get_active_uma_gb, models_on_tier, topology_summary
  compound/optimized_session_manager.py: SessionState, SessionConfig, lazy_import_mcp_client, OptimizedSessionRuntime, InferenceSession, CompoundSessionManager, create_optimized_session
  compound/output_validator.py: validate_structured_output, execute_with_output_validation
  compound/persistence/vault.py: PersistenceConfig, SessionPersister, VaultPersister, SimplePersistence
  compound/persistence.py: CompoundPersistence
  compound/plasma_theosophy_synthesizer.py: PlasmaAnomalyData, PlasmaTheosophySynthesizer
  compound/post_execution.py: PostExecutionOrchestrator
  compound/proactive_reactive_engine.py: SystemEvent, CircuitBreaker, WorkloadPattern, ProactiveAction, ProactiveReactiveEngine, reactive_on, create_proactive_reactive_system
  compound/problem_discovery.py: ProblemTemplate, Problem, discover_problems, default_templates
  compound/prompt_optimizer.py: PromptOptimizer
  compound/prompt_version_registry.py: PromptVersionRegistry, evaluate_regression, generate_fixture_candidates
  compound/qa_gate.py: RiskScore, GateRecord, evaluate
  compound/r0_sigma.py: UncertaintyBand, R0Challenge, R0ChallengeResult, synthesize_challenges
  compound/recursive_challenger.py: get_test_count, ImprovementOpportunity, RecursiveChallenger
  compound/request_alignment_analyzer.py: RequestAlignmentAnalyzer, RequestAlignmentAnalyzerFactory
  compound/request_cache.py: RequestCache
  compound/research_feed_parser.py: FeedRecord, parse_research_feed, CrossrefReport, feed_backlog_crossref, feed_dedup_hits
  compound/resilience_loop.py: ResilienceExecutionResult, EcoResilienceCompoundLoop, get_resilience_loop
  compound/retrospection_summary.py: CycleMetrics, RetrospectionSummary, FailureSignature, mine_failure_signatures, StrategyTracker, CycleRetrospectionEngine
  compound/retrospection_validator.py: ValidationResult, RetrospectionValidator
  compound/routing_feedback_loop.py: RoutingDecisionType, RoutingDecision, RoutingMetrics, RoutingOptimizationFeedback, get_routing_feedback
  compound/rubric_middleware.py: RubricVerdict, RubricMiddleware
  compound/safe_exec.py: safe_exec_globals
  compound/scope_frontier.py: ScopeProposal, propose_scope_frontier, unswept_packages_from_ledger, propose_scope_frontier_from_state, frontier_is_human_gated, gated_reasons_from_ledger, gated_targets_from_ledger, frontier_is_human_gated_from_state, HumanGateDecision, human_gate_report, human_gate_report_from_state
  compound/self_evolving_refiner.py: FailureAnalysis, SelfEvolvingRefiner
  compound/self_improvement_orchestrator.py: SelfImprovementOrchestrator
  compound/session_broadcast.py: BroadcastPlan, build_broadcast, broadcast
  compound/session_manager.py: SessionState, SessionConfig, InferenceSession, VaultCheckpointManager, create_session, get_session, list_sessions, close_session, AlignmentResult, SessionSummary, CompoundSessionManager
  compound/session_metrics_aggregator.py: ExperimentRecord, SessionMetricsAggregator
  compound/simplicity_audit.py: nesting_outliers, complexity_outliers, long_parameter_lists, long_functions, stealth_bare_excepts, passthrough_functions, NeedlessPassthrough, needless_passthroughs
  compound/skill_adoption.py: skill_adoption_report, low_adoption_report, least_adopted
  compound/skill_consensus_voter.py: VotingStrategy, AgentVote, ConsensusResult, SkillConsensusVoter
  compound/skill_evolution_diff.py: SkillVersion, SkillDiff, SkillEvolutionTracker
  compound/skill_health_tracker.py: SkillHealthRecord, SkillHealthTracker
  compound/skill_mutation_queue.py: SkillMutation, SkillMutationQueue
  compound/skill_quality_data_pipeline.py: SkillQualityDataPipeline
  compound/skill_quality_orchestrator.py: ImprovementHypothesis, ImprovementResult, SkillQualityOrchestrator
  compound/skill_quality_scorer.py: DimensionScore, SkillQualityReport, SkillQualityScorer
  compound/skill_refinement_validator.py: RefinementMetrics, SkillRefinementValidator
  compound/skill_refiner.py: ExecutionMetrics, LearningSignal, SkillRefinementInput, EnvironmentResponsePredictor, ShadowCanaryValidator, SkillRefiner, SkillRefinerFactory
  compound/skill_selector.py: SkillScore, SkillSelector
  compound/skills/selector.py: SkillMatch, SkillSelector, SelectorFeedbackRefiner, SimpleSkills
  compound/stability_guard.py: StabilityCheckResult, HIHOStabilityGuard
  compound/symbolic_executor.py: SymbolicExecutor
  compound/tape_logger.py: TapeEntry, TapeLogger
  compound/task_queue.py: TaskPriority, QueuedTask, QueueMetrics, TaskQueue
  compound/tdd_adversarial/adversarial_review.py: ReviewPerspective, ReviewFinding, PerspectiveState, ReviewSession, AdversarialReviewSystem, get_adversarial_review_system
  compound/tdd_adversarial/adversarial_reviewer.py: AdversarialCritique, AdversarialRedTeamAgent
  compound/tdd_adversarial/coordinator.py: TDDAdversarialState, TDDAdversarialCoordinator, get_tdd_adversarial_coordinator
  compound/tdd_adversarial/tdd_integration.py: TestStatus, TestType, TestResult, TDDState, TDDIntegration, get_tdd_integration
  compound/tdd_adversarial/test_integration.py: test_tdd_integration, test_adversarial_review, test_coordinator, test_workflow_initializer, main
  compound/tdp_budget_tracker.py: PowerProfile, PowerSample, TDPEnvelope, TDPConfig, TDPBudgetTracker, get_tdp_budget_tracker
  compound/team_executor.py: AgentTask, AgentTaskResult, TeamExecutionResult, TeamExecutor, TeamExecutorFactory
  compound/telegram_hub.py: TelegramOOMGuard, TelegramHub
  compound/telegram_notify.py: notify, notify_tier_escalation, notify_task_complete, notify_lemonade_offline, notify_compound_error
  compound/telemetry.py: StepMetrics, PipelineMetrics, CompoundTelemetry, get_telemetry
  compound/test_basic_import.py: test_imports
  compound/thermal_autoresearch_executor.py: DomainConfig, EightHourConfig, ThermalAutoresearchExecutor, run_8hour_autoresearch_journey
  compound/thermal_checkpoint_manager.py: ThermalState, Checkpoint, ThermalConfig, ThermalCheckpointManager, get_thermal_checkpoint_manager
  compound/thermal_history_persistence.py: ThermalTimeSeriesCollector, load_jsonl_history, get_thermal_time_series_collector
  compound/thermal_predictor.py: ThermalMetrics, ThermalTrendAnalyzer, get_thermal_trend_analyzer
  compound/thermal_trend_predictor.py: ThermalTimeSeries, ThermalTrendPredictor, get_thermal_trend_predictor
  compound/thermodynamic_metrics.py: ThermodynamicState, PhaseTransition, ThermodynamicMetrics
  compound/token_efficient_executor.py: TokenEfficientCompoundExecutor
  compound/token_ledger.py: LedgerRow, LedgerSummary, TokenLedger
  compound/topological_persistence.py: PersistencePair, PersistenceDiagram, TopologicalPersistence, trajectory_persistence_summary
  compound/trace_exporter.py: OtelSpan, execution_trace_to_otel_spans
  compound/trajectory_search.py: TrajectorySearchResult, TrajectorySearchEngine
  compound/triune_reviewer.py: ReviewPerspective, TriuneReviewResult, TriuneReviewer
  compound/triune_self.py: DoerProtocol, ThinkerProtocol, KnowerProtocol, CallableDoer, NullKnower, PerciwalCycleResult, TriuneSelf
  compound/universal/init.py: is_cohezion_environment, initialize_cohezion_environment
  compound/universe_bridge.py: UniverseBridge
  compound/vault_search_executor.py: SearchQuery, SearchResult, VaultSearchExecutor, create_vault_search_executor
  compound/vector_pruning.py: SemanticVector, PruningReport, VectorPruningEngine
  compound/vmodel_harness.py: SkillVModelRecord, VModelCoverageReport, VModelHarness, run_coverage, main
  compound/workflow_manager.py: OnboardingResult, GapReport, ReassessmentReport, FinetuneResult, WorkflowManager
pkg concurrency (5 files)
  concurrency/file_lock.py: FileLockError, FileLock, ConfigManager, LockedFileOperation, safe_file_access
  concurrency/ollama_gate.py: OllamaGate, get_gate, reset_gate
  concurrency/safe_singleton.py: safe_singleton
  concurrency/shared_resources.py: SkillRegistry, CapabilityUsageTracker
pkg config (16 files)
  config/config_archival.py: ConfigArchiver, SizeEnforcer
  config/config_events.py: ConfigEvent
  config/config_monitoring.py: ConfigMonitor, VaultSubscriptionClientProxy
  config/config_state.py: SectionRef, FileMetadata, ChangeSet, ConfigConflict, ValidationReport, ConfigSchema, ConfigState
  config/config_sync_engine.py: ConfigSyncEngine
  config/config_sync_logger.py: SyncLogEntry, ConfigSyncLogger
  config/config_templates.py: TemplateType, TemplateContext, ConfigTemplateEngine
  config/config_validation.py: ConfigValidator, ReconciliationValidator
  config/configuration_orchestrator.py: get_config_orchestrator, reset_config_orchestrator, ConfigurationOrchestrator
  config/conflict_policy.py: ConflictResolutionStrategy, ConflictPolicy, ConflictResolutionPolicy
  config/event_wiring.py: CommitBatcher, EventSubscriber, SyncEventSubscriber
  config/git_utils.py: GitUtils
  config/semver_validator.py: BumpType, SemVer, ValidationResult, SemverValidator
  config/unified.py: UniverseTrackConfig, EmailConfig, CloudGraderConfig, SystemConfig, get_config, reload_config
pkg core (53 files)
  core/cache_manager.py: CacheManager
  core/compound/engine.py: CompoundLogicEngine
  core/compound/retrospection.py: LearningPattern, SkillRefinement, RetrospectionEngine
  core/compound/skill_refiner.py: RefinementResult, SkillRefiner
  core/config.py: ModelConfig, TokenBudget, CacheConfig, BatchConfig, InferenceConfig, CohezionConfig
  core/config_templates.py: ConfigTemplateManager
  core/connection_pool.py: SurrealClientProtocol, PoolConfig, PooledConnection, ConnectionPool, get_connection_pool, reset_connection_pool
  core/context_engineering.py: ContextEngineeringInfrastructure
  core/credit_manager.py: CreditManager, get_credit_manager
  core/event_bus.py: EventType, Event, EventHandlerProtocol, EventBus, EventFilter, SamplingFilter, RoutingFilter, get_event_bus, reset_event_bus, EventHandlerGroup
  core/heterogeneous_sharding.py: NodeStatus, ComputeNode, Shard, ShardingReport, HeterogeneousShardingProtocol
  core/instruction_expander.py: PlanStep, ExecutablePlan, InstructionExpander
  core/journey_persistence_manager.py: WriteDestination, TrajectoryNode, PersistenceResult, JourneyPersistenceManager
  core/journey_worker.py: JourneyWorker, get_journey_worker
  core/local_registry.py: LocalRegistry, get_local_registry
  core/manifold_sharding.py: PulseMode, ManifoldShard, HolographicCoherenceReport, DistributedManifold
  core/mcp_client.py: MCPConfig, MCPClientError, MCPConnectionError, MCPAuthenticationError, MCPToolError, MCPClient, create_mcp_client, get_mcp_client
  core/mcp_retry.py: retry_async, retry_sync
  core/persistence/admin.py: DBAdmin
  core/persistence/query_patterns.py: query_patterns
  core/persistence/redis_aggregator.py: RedisAggregator, get_redis
  core/persistence/repositories/base.py: RepositoryMetrics, BatchOperationResult, BaseRepository
  core/persistence/repositories/journey_repository.py: JourneyMetrics, JourneyStep, AgentJourney, JourneyRepository
  core/persistence/repositories/pattern_repository.py: CodePattern, CodeAntiPattern, PatternRepository
  core/persistence/repositories/skill_repository.py: Skill, SkillRepository
  core/persistence/repositories/surreal_journey_repository.py: SurrealJourneyRepository
  core/persistence/repositories/surreal_proactive_repository.py: SuggestionAcceptance, PatternEffectiveness, SurrealProactiveRepository
  core/persistence/repositories/surreal_skill_repository.py: SurrealSkillRepository
  core/persistence/repositories/surreal_universe_repository.py: SurrealUniverseRepository
  core/persistence/repositories/universe_repository.py: UniverseRepositoryFilter, UniverseRepository
  core/persistence/repositories.py: UniverseNode, AgentJourney, DBClientProtocol, NodeRepository, SurrealNodeRepository, JourneyRepository, SurrealJourneyRepository, RepositoryFactory, get_repository_factory
  core/persistence/surreal_client.py: InsecureSurrealCredentialsError, PhysicsState, UniverseNode, SurrealClient, InMemoryStore, main, get_surreal_client
  core/plan_executor.py: TokenClient, StepResult, ExecutionResult, PlanExecutor
  core/resource_monitor.py: ResourceMonitor, get_resource_monitor
  core/routing/manifold_bridge.py: ManifoldBridge
  core/routing/router.py: LocalExpertRouter
  core/silicon_guard.py: HardwarePressure, SiliconGuard, get_silicon_guard
  core/substrate_governor.py: PressureLevel, DilationState, GovernorEvent, SubstrateGovernor
  core/substrate_loom.py: LoomMode, SHMSnapshot, SubstrateLoom
  core/symmetry_hardware_bridge.py: SymmetryHardwareBridge, get_symmetry_bridge
  core/task_manager.py: TaskStatus, TaskInfo, TaskManager, TaskGroup, get_task_manager, reset_task_manager
  core/telemetry_bus.py: TelemetryBus, get_telemetry_bus
  core/template_engine.py: SkillSpec, TemplateEngine
  core/time_keeper.py: TimeKeeper, get_time_keeper
  core/timeit.py: TimeitStats, timeit, get_stats
  core/vault_subscription.py: VaultEvent, VaultSubscriptionClient
  core/zero_copy_validator.py: TypeMismatchError, ChecksumValidationError, SHMBuffer, ValidationReport, ZeroCopyValidator
  core/zvol_swap.py: SwapEventType, KVCacheEntry, SwapEvent, ZVOLSwapPipeline
pkg cost_optimization (5 files)
  cost_optimization/budget_enforcer.py: BudgetPolicy, BudgetState, CostAlertManager, BudgetCircuitBreaker, BudgetEnforcer, get_current_enforcer, set_current_enforcer, reset_current_enforcer
  cost_optimization/cost_dashboard.py: CostBreakdown, SpendRate, BudgetStatus, TrendPoint, CostDashboard, get_cost_dashboard, reset_cost_dashboard
  cost_optimization/cost_tracker.py: CostRecord, SessionCostTracker, get_current_tracker, set_current_tracker, reset_current_tracker
  cost_optimization/forecast_engine.py: Forecast, ForecastSummary, AnomalyScore, ForecastEngine, get_forecast_engine, reset_forecast_engine
pkg data_mesh (14 files)
  data_mesh/audio_telemetry.py: TaxonomyLevel, BirdSpeciesNode, AudioSegmentMetadata, SpectrogramConfig, AudioTelemetryEvent
  data_mesh/corpus_quality_consumer.py: CorpusQualityConsumer, make_corpus_quality_consumer
  data_mesh/data_product.py: DataProductStatus, DataQualityTier, DataProductSchema, DataProduct, get_cohezion_data_products
  data_mesh/event_bridge.py: DataMeshEventBridge, make_event_bridge
  data_mesh/event_consumer.py: EventConsumer
  data_mesh/gaia_domain_agent.py: GaiaDataAgent
  data_mesh/inference_products.py: build_inference_products, get_inference_registry, get_product_for_capability, register_with_event_bus, emit_quality_alert
  data_mesh/journey_telemetry.py: HardwareTier, SwarmExpert, QuadratureFabrics, RZeroMetrics, FlumeJourneyEvent
  data_mesh/kanban_bridge.py: persist_item, backfill_items
  data_mesh/lemonade_multimodal.py: LemonadeMultimodalClient, make_multimodal_client
  data_mesh/research_products.py: classify_actionability, ResearchFinding, parse_brief, card_finding, ingest_brief, ingest_all_briefs
  data_mesh/scripts/data_mesh_guard.py: check_slas
  data_mesh/universe_telemetry.py: UniverseStateEvent
pkg datamesh (7 files)
  datamesh/bidirectional_linkage.py: LinkDirection, LinkStatus, BidirectionalLink, LinkChangeEvent, BidirectionalLinkageManager
  datamesh/federation.py: DomainEndpoint, FederationLayer
  datamesh/ingestion.py: IngestionConfig, IngestionMetrics, DatameshIngestion, IdempotentWriter
  datamesh/knowledge_graph_layer.py: RelationType, KnowledgeEdge, KnowledgeNode, KnowledgeGraphLayer
  datamesh/query.py: DatameshFilter, DatameshResult, DatameshQuery
  datamesh/schema.py: RecordType, RelationType, Physics12D, Embedding256D, DataLineage, UnifiedRecord, WikiRecordBuilder, FlumeRecordBuilder, OuroborosRecordBuilder
pkg deployment (2 files)
  deployment/feature_flags.py: RolloutStage, FeatureFlag, FeatureFlagConfig, FeatureFlagContext, FeatureFlagManager, get_feature_flag_manager, is_feature_enabled
pkg dogfooding (3 files)
  dogfooding/daily_cycle.py: DailyDogfoodingCycle, main
  dogfooding/production_hardening.py: CIIntegration, PerformanceMonitor, DisasterRecovery, ProductionHardening, main
pkg environments (9 files)
  environments/arc_env.py: MockARCGame, ARCEnvironment
  environments/auto_generator.py: EnvironmentSpec, GeneratedEnvironment, EnvironmentGenerator, GeneratedCodeValidator
  environments/forest_integrity_env.py: ForestIntegrityEnv
  environments/manifold_env.py: ManifoldEnv
  environments/seagrass_percolation_env.py: SeagrassPercolationEnv
  environments/swarm_env.py: SwarmEnv
  environments/tidal_perturbation_env.py: TidalPerturbationEnv
  environments/universe_agent_env.py: UniverseAgentEnv
pkg eval (7 files)
  eval/capability_scorecard.py: StatisticalComparison, CapabilityScorecard
  eval/cognitive_profile.py: TextProbe, MemoryProbe, LearningProbe, Capabilities, Axis, build_default_capabilities, oracle_capabilities, run_profile
  eval/huggingface_export.py: HuggingFaceExporter
  eval/pipeline.py: EpisodeStatus, EpisodeResult, RalphLoopConfig, PipelineProgress, RalphLoop, EvalPipeline
  eval/stats.py: pass_at_k, bootstrap_ci, MeanCI, mean_ci, ContaminationResult, contamination_probe
  eval/universe_evaluator.py: EpisodeMetrics, PolicyEvaluation, PolicyComparison, UniverseEvaluator, random_policy, greedy_hiho_policy, zero_policy
pkg evaluation (2 files)
  evaluation/self_eval.py: EvaluationResult, SelfEvaluationEngine
pkg evo (1 files)
pkg evolution (4 files)
  evolution/reflection_optimizer.py: OptimizationResult, ReflectionOptimizer
  evolution/skill_optimizer.py: SkillOptimizer
  evolution/variable.py: Variable, from_prime_section
pkg flume (60 files)
  flume/alignment.py: DomainAlignmentMLP, LatentAligner
  flume/autoencoder.py: FlumeConfig, ThoughtEncoder, ThoughtDecoder, FlumeEncoder
  flume/benchmark_swarm_s16.py: benchmark_swarm
  flume/bioelectric.py: BioelectricSignal, ActionVector, BioelectricEngine
  flume/bridge.py: HFEmbeddingBridge
  flume/coe_evaluator.py: CoEMode, ChainOfEmbeddingEvaluator, get_coe_evaluator, coe_quality_from_texts, coe_quality_from_embeddings
  flume/coherence_guard.py: TurboQuantHarness, apply_dummy_int8_quantization
  flume/compression.py: FlumeCompressionPipeline, PolarQuantEncoder, QJLProjector
  flume/data_pipeline.py: SyntheticTaskGenerator, ContrastivePairMiner, TrainingDataPipeline
  flume/dataset.py: FlumeTrajectoryDataset, SyntheticFlumeDataset, RealSkillStateDataset
  flume/diversity.py: gvendi_diversity_filter, ConceptDirection, LatentDirectionProbe
  flume/domain_encoder.py: EncodedTrajectoryPoint, DomainEncoder, MathProblemEncoder, KernelOptimizationEncoder, InteractiveGameEncoder, GenericEncoder, register_encoder, get_encoder
  flume/embedding_provider.py: EmbeddingProvider, OllamaEmbeddingProvider, HashFallbackProvider, CachedEmbeddingProvider, create_embedding_provider, AsyncOllamaEmbeddingProvider
  flume/evaluate_vae.py: reconstruction_cosine_similarity, paraphrase_precision_at_1, kl_health_check, similarity_preservation_spearman, VAEEvaluator
  flume/experience_collector.py: ExperienceCollector
  flume/experience_dataset.py: ExperienceDataset
  flume/experience_encoder.py: ExperienceEncoder
  flume/experience_pipeline.py: ExperienceTrainingPipeline
  flume/flume_two_track.py: FlumeTwoTrack, run_twotrack_smoke_test
  flume/geometric_bridge.py: GeometricLatentBridge
  flume/git_encoder.py: GitEncoder
  flume/grid_encoder.py: ARCGridEncoder, FlumeGridHarness
  flume/journey_encoder.py: JourneyEncoderConfig, JourneyToFlumeEncoder, compute_journey_vae_loss, save_checkpoint, load_checkpoint
  flume/journey_finetune_pipeline.py: JourneyToFinetuneConverter, OllamaFinetuner, main
  flume/kernels/turbo_kv.py: ProdQuantized, ValueQuantized, TurboKVKernel
  flume/latent_channel.py: LatentMessage, SharedLatentMemory, get_shared_latent_memory
  flume/latent_engine.py: LatentState, CoconutResult, coconut_reason, coe_self_eval, soft_cot_prefix, RecurrentDepthResult, recurrent_depth, LatentEngine, LatentReasoningResult
  flume/latent_gravity.py: LatentGravityNavigator
  flume/latent_health.py: LatentBasisMonitor
  flume/lcsp.py: LCSPPrediction, LCSPPredictor
  flume/local_finetune_pipeline.py: LocalFinetuner, quick_finetune
  flume/manifolds/translator.py: ManifoldProjection, ManifoldTranslator
  flume/mnm.py: ManifoldWarp, ManifoldManager
  flume/morphospace.py: StabilityWell, MorphoPath, MorphospaceMapper
  flume/mps_compressor.py: MPSCompressor
  flume/navigation.py: lerp, slerp, similarity_score
  flume/navigator.py: FlumeNavigator, main
  flume/optuna_tuner.py: FlumeTuneConfig, assert_safe, sample_config, StudyResult, run_flume_study
  flume/overlap.py: calculate_geometric_overlap
  flume/predictor.py: TrajectoryPredictor
  flume/skill_state_encoder.py: SkillStateEncoder
  flume/sparse_analysis.py: SparseLatentAnalysis
  flume/spectral_encoder.py: SpectralEncoder
  flume/stealthskater_corpus.py: embed_corpus, cosine_sim, run_exp_bbbb, append_to_autoresearch, persist_to_surrealdb, run_phase8, run_phase8_sync
  flume/tda_detector.py: TDADetector
  flume/temporal_encoder.py: TemporalEncoder, TemporalDecoder, TemporalVAELoader
  flume/tokenizer.py: FlumeTokenizer
  flume/train.py: FlumeTrainConfig, JourneyDataset, train_flume_on_journeys
  flume/train_vae.py: kl_annealing_beta, count_active_units, VAETrainer
  flume/training.py: TrainConfig, FlumeVAETrainer
  flume/trajectory_capture.py: TrajectoryRecorder, capture_trajectory
  flume/trajectory_dataset.py: TrajectorySequenceDataset, collate_sequences
  flume/turbo_quant.py: TurboQuantCPU, measure_coherence_loss
  flume/vacuum_encoder.py: get_vacuum_encoder, encode_journey_text, load_vacuum_atlas, classify_journey_phase
  flume/vacuum_topology.py: VacuumLabel, VacuumTopologyClassifier, classify_point
  flume/vae.py: FlumeVAEConfig, ThoughtVector, FlumeVAE, flume_vae_loss, build_optimal_vae
  flume/vae_encoder.py: SimpleEncoder, FlumeVAEEncoder, get_encoder, reset_encoder
  flume/vliw_kernel_sim.py: VLIWSimulator
  flume/vliw_latent_alignment.py: align_vliw_to_12d
pkg flux (10 files)
  flux/aggregator.py: FluxAggregator
  flux/provider.py: FluxProvider
  flux/providers/cache_flux.py: CacheFlux
  flux/providers/history_flux.py: HistoryFlux
  flux/providers/surreal_flux.py: SurrealFlux
  flux/providers/tool_flux.py: ToolFlux
  flux/providers/vault_flux.py: VaultFlux
  flux/types.py: FluxSource, FluxBlock, FluxContext
pkg gateway (5 files)
  gateway/demo_gateway.py: DemoMetrics, DemoGateway
  gateway/mcp_http_server.py: sse_endpoint, health, tools, main
  gateway/mcp_server.py: GatewayManager, get_gateway_manager, list_tools, call_tool, main
  gateway/ngrok_adapter.py: NgrokMetrics, NgrokAIGateway
pkg governance (17 files)
  governance/autonomy_engine.py: AutonomyTier, AgentAutonomyState, AutonomyEngine, get_autonomy_engine
  governance/cerebellum_drift.py: cerebellum_drift
  governance/concierge.py: SessionBriefing, RoutingSuggestion, RoutingRecord, ConciergeAgent
  governance/fleet_monitor.py: ServiceStatus, FleetMonitor, get_fleet_monitor
  governance/flume_bridge.py: encode_prompt, flume_route_similarity, agent_state_to_patch_center, encode_data_product_description, data_product_similarity
  governance/guardian.py: Guardian, GuardianRegistry, slugify, get_guardian_cli
  governance/knowledge_bridge.py: Learning, persist_to_vault, persist_to_surrealdb, deposit_neuron_record, build_skill_neuron, deposit_skill_neuron, build_cerebellum_neuron, deposit_cerebellum_neuron, deposit_cerebellum_if_novel, recall_neurons, routing_memory_context, update_key_learnings_with_link, persist_learning
  governance/neuron_quality.py: memory_coverage, DepositQualityReport, deposit_quality_report, memory_gaps, DepositQualityDelta, deposit_quality_delta
  governance/quadrature_nexus.py: QuadratureState, QuadratureNexus
  governance/scripts/async_guard_v2.py: AsyncGuard
  governance/scripts/bmad_guard.py: check_symlinks, check_catalog_schema, check_phase_locks, check_artifact_frontmatter, check_manifest_sync, main
  governance/scripts/guardian_cli.py: main
  governance/scripts/local_resource_manager_guard.py: LocalResourceManagerGuard
  governance/scripts/meta_guard.py: MetaGuard
  governance/scripts/root_health_guard.py: check_root_health
  governance/scripts/submission_governance_guard.py: SubmissionGovernanceGuard
pkg graph (6 files)
  graph/builder.py: WorkflowBuilder
  graph/engine.py: WorkflowEngine
  graph/nodes.py: WorkflowNode, AgentNode, ToolNode, LogicSwitchNode, CustomNode
  graph/persistence.py: WorkflowPersistence
  graph/types.py: NodeStatus, NodeSpec, EdgeSpec, WorkflowSpec, NodeResult, WorkflowResult
pkg healing (8 files)
  healing/__init__.py: HealthStatus, DiagnosisResult, DriftDetector, Diagnostician, Corrector, SelfHealingSystem, get_healing_system
  healing/amd_s2idle_report.py: read_file, get_distro, is_root, relaunch_sudo, DistroPackage, PipxPackage, check_amd_s2idle
  healing/deep_audit.py: CodeIssue, FileStats, DeepAuditor, run_deep_audit
  healing/drift_analyzer.py: DriftAnalyzer
  healing/immune_system.py: SelfDiagnostic, VelocityMonitor, ActuatorSystem
  healing/platform_audit.py: AuditResult, PlatformAudit, run_audit, print_audit
  healing/scripts/trajectory_guard.py: guard_trajectories
  healing/utilization_audit.py: analyze_utilization
pkg hookify (4 files)
  hookify/adversarial_review.py: ReviewPerspective, AdversarialReviewResult, AdversarialReviewHarness, ConsensusVoter
  hookify/validator.py: Rule, ValidationResult, HookifyValidator
  hookify/vault_writer.py: HookifyVaultWriter
pkg inference (85 files)
  inference/activation_router.py: PrefillActivationRouter
  inference/anti_sycophancy.py: SycophancyRisk, AntiSycophancyGuard, BlindEvaluator, NegativeResultReporter, MultiMetricTradeoffAnalyzer, SycophancyResistantExperimentRunner, create_sycophancy_resistant_runner
  inference/autoharness.py: AutoHarnessHypothesis, ThompsonSamplingSearch, CodeAsActionVerifier, HarnessAsPolicy, AutoHarnessEngine
  inference/autoharness_ce.py: TokenBudget, OroborousOptimizer, MyceliumKnowledgeGraph, FlumeDataPipeline, CompoundEngineeringAutoHarness, create_compound_autoharness
  inference/batch_adapter.py: BatchOrchestrator, run_batch_local
  inference/capability_profile.py: CardParseError, CapabilityProfile, CardParser
  inference/challenger_solver.py: SolverState, run
  inference/clasp_tier.py: CLaSpStats, get_clasp_stats, CLaSpTier, build_clasp_igpu_tier
  inference/confidence_calibration.py: PlattCalibrator, set_default_calibrator, calibrated_classify
  inference/context_engineering.py: ModelCapability, ModelCard, ModelCardRegistry, ContextEngineer, QualityMonitor, AutoHarness, get_context_engineer, create_autoharness
  inference/default_profiles.py: get_profile
  inference/direct_tier.py: DirectLemonadeTier, build_direct_npu_tier, build_direct_igpu_tier, build_direct_cpu_tier, FleetNodeResult, FleetResult, ParallelFleetOrchestrator, multi_node_batch, quarter_on_a_string_tier
  inference/distributed_swarm.py: NodeKind, AggregationStrategy, NodeMetrics, SwarmResult, SwarmExperienceTrace, AdaptiveRouter, ExperienceCollector, NodeCircuitBreaker, SiliconSwarm, get_swarm, swarm_dispatch, swarm_parallel, swarm_deliberate
  inference/entropy_compressor.py: StepEntropyCompressor
  inference/escalation_gate.py: SlidingWindowQuantileTracker, IsotonicCalibrator, composite_gate
  inference/evaluation_harness.py: ExperimentMetrics, EvaluationHarness, evaluate_quality_simple, estimate_cost
  inference/fleet.py: RouteResult, route, extend_claude, extend_claude_aligned
  inference/fleet_roles.py: RoleSpec, FleetRoster
  inference/fleet_routing_specialist.py: RoutingDecision, FleetRoutingSpecialist
  inference/fractal_metrics.py: FractalRegime, classify_fd, higuchi_fd, feynman_path_weight, feynman_amplitude_rank, hiho_fixed_point_deviation, quality_series_report, gwtc5_calibration_sequence, bunimovich_calibration_sequence, RollingRegimeTracker
  inference/frontier_oracle.py: FrontierDecision, is_frontier_task, fable_spend_usd, decide_frontier, frontier_complete, frontier_complete_sync
  inference/gaia_adapter.py: GaiaAgentTier, rank_models_by_amd_optimization, amd_optimized_hierarchy, build_gaia_native_tier, build_gaia_mcp_tier, build_gaia_llm_tier
  inference/gauntlet.py: BenchTask, BenchResult, run_gauntlet, get_champion
  inference/gemini_cli_tier.py: GeminiCliTier, GeminiADKTier
  inference/hardware_telemetry.py: ComputeBackend, HardwareSnapshot, UtilizationProfile, HardwareTelemetry, MultiBackendTelemetry, HardwareAwareAutoharness, create_hardware_telemetry
  inference/harnesses.py: Harness, HarnessSlot, HarnessPool, get_pool, dispatch_through_harness
  inference/headless_claude_tier.py: HeadlessClaudeTier, build_claude_tier
  inference/health.py: LaneStatus, LaneHealth, FleetHealth, check_fleet, format_fleet_summary, integrate_omnibus_gateways
  inference/hybrid_router.py: hybrid_route_decision
  inference/idle_eviction.py: eligible, observe_idle_minutes, sweep, main
  inference/image_tier.py: ImageRequest, ImageResult, DirectLemonadeImageTier
  inference/kv_budget.py: kv_cache_bytes, preflight
  inference/langchain_tier.py: LangChainTierResult, LangChainTier, build_rag_chain
  inference/lemonade_embed_bridge.py: LemonadeEmbedBridge
  inference/lemonade_health.py: CtxHazard, OrphanProcess, TypeHeadroom, RecipeProbe, LemonadeHealth, is_lemonade_alive, probe_lemonade
  inference/lemonade_recipes.py: CapabilityProfile, SystemPromptBank, OutputBudgets, EmpiricalMetrics, ModelRecipe, get_recipe, best_model_for_task, get_inference_params, register_recipe, probe_live_models, discover_from_live_models
  inference/load_safety.py: available_ram_gb, effective_size_gb, check_load_safe
  inference/local_coverage.py: LocalCoverageReport, local_coverage_report, coverage_gaps
  inference/local_fleet.py: FleetRole, FleetModel, LocalResearchFleet, get_fleet
  inference/lynx_gate.py: EscalationProbe, LYNXGate
  inference/model_card_defaults.py: get_sampling_defaults, apply_model_card_defaults
  inference/model_card_harness.py: InferenceParams, ModelCardHarness
  inference/model_size_measurer.py: measure_gguf_sizes
  inference/npu_gauntlet.py: flm_roster, procedural_suite, npu_occupant, load_npu, server_version, telemetry, pick_temp_arm, surreal_push, run_round, leaderboard, publish, frontier_review, run_gauntlet_forever, main
  inference/omni_model.py: OmniModel, get_omni
  inference/oom_guard.py: check_ram, scan_and_harden, pre_load_gate, verify_all_bounded
  inference/orchestrator.py: QualityGate, TierAttempt, OrchestrationResult, Runnable, TieredOrchestrator, default_hierarchy
  inference/orchestrator_autoharness.py: TaskPriority, ComputeNodeState, ComputeNode, Task, RoutingDecision, MultiNodeOrchestrator, StrixHaloOrchestrator, create_strix_halo_orchestrator
  inference/p0_resilience_mixins.py: TimeoutMixin, HealthChecker, Checkpoint, CheckpointManager, AsyncExecutorMixin, ThreadSafeAggregator, retry_with_backoff, atomic_write_json
  inference/quality_eval.py: QualityVerdict, evaluate, ttft_budget_ms
  inference/ram_scheduler.py: model_footprint, RamStatus, RamScheduler, get_scheduler
  inference/recipe_guard.py: RecipeMisalignment, LintViolation, RecipeGuard
  inference/registry.py: Lane, Task, WeightQuant, KVQuant, ModelEntry, FleetRegistry, LivenessDrift, LivenessAudit, get_registry
  inference/resource_aware_router.py: RouteDecision, resource_aware_route, route_now
  inference/route_by_capability.py: route_by_capability
  inference/sandbox.py: sanitized_env, sandbox_tempdir, apply_resource_limits, SandboxedSubprocess
  inference/security_spec.py: check_credential_leak, redact_credentials, check_prompt_injection, sanitize_for_surreal, verify_all
  inference/seed_evaluator.py: eval_quality, select_best_seed, get_seed_analysis
  inference/smart_orchestrator.py: SmartResult, SmartOrchestrator, build_smart_orchestrator
  inference/specialist_coverage.py: SpecialistCoverage, SpecialistCoverageReport, specialist_coverage_report, SpecialistCoverageDelta, specialist_coverage_delta
  inference/specialist_registry.py: SpecialistSpec, get_specialist, list_task_types
  inference/structured_npu.py: npu_structured_json
  inference/stt_tier.py: Segment, STTRequest, STTResult, build_stt_tier, DirectLemonadeSTTTier
  inference/system_resource_agent.py: ResourceRecommendation, SystemResourceAgent
  inference/task_classifier.py: Harness, select_harness, band_for_node, RouteDecision, classify, classify_with_harness, classify_with_vacuum_hint
  inference/token_budget.py: TokenUsageRecord
  inference/transition_controller.py: TransitionController, first_passage, time_in_states, detect_stuck_loops
  inference/tri_compute_orchestrator.py: ComputeTask, ExperimentPhase, NPUInferenceEngine, iGPUSimulationEngine, CPUOrchestrationEngine, TriComputeOrchestrator, demo_tri_compute
  inference/triune_orchestrator.py: build_triune_orchestrator, build_triune_omni_orchestrator, build_reasoning_orchestrator, build_parallel_fleet_orchestrator
  inference/tts_tier.py: TTSRequest, TTSResult, build_tts_tier, DirectLemonadeTTSTier
  inference/turboquant/capture.py: RingBuffer, KVCaptureEngine
  inference/turboquant/codebook.py: beta_pdf, compute_lloyd_max_codebook, get_codebook, get_codebook_tensors
  inference/turboquant/kv_cache.py: ValueQuantized, unpack_values, quantize_values, dequantize_values, TurboQuantKVCache
  inference/turboquant/quantizer.py: MSEQuantized, ProdQuantized, TurboQuantMSE, TurboQuantProd
  inference/turboquant/rotation.py: generate_rotation_matrix, generate_qjl_matrix, rotate_forward, rotate_backward
  inference/turboquant/score.py: compute_hybrid_attention
  inference/turboquant/store.py: FlatCache, CompressedKVStore
  inference/turboquant/triton_kernels.py: turboquant_mse_score, turboquant_qjl_score, turboquant_attention_score, turboquant_fused_decode
  inference/turboquant/vllm_attn_backend.py: set_mode, get_mode, install_turboquant_hooks, enable_no_alloc, free_kv_cache
  inference/turboquant_reference.py: HadamardRotation, PolarQuant, TurboQuantReference
  inference/turboquant_streaming.py: KVCacheStats, StreamingKVCompressor
  inference/unified_orchestrator.py: NodeKind, DispatchSource, NodeMetrics, UnifiedResult, ExperienceTrace, QualityScorer, ActionVerifier, DefaultQualityScorer, classify_complexity, AdaptiveRouter, ExperienceCollector, UnifiedOrchestrator, get_orchestrator, create_default_orchestrator, unified_dispatch, unified_batch
  inference/usage_log.py: record_usage, read_usage_log
pkg integrations (29 files)
  integrations/agentverse/api_llm_executor.py: APIResult, APILLMExecutor, HybridExecutor, main
  integrations/agentverse/autonomous_loop.py: SkillBenchmark, RefinementResult, AutonomousCompoundLoop
  integrations/agentverse/benchmark_runner.py: BenchmarkResult, AgentVerseBenchmarkRunner
  integrations/agentverse/bridge.py: CoherenceViolation, AgentVerseBridge
  integrations/agentverse/cli.py: MockExecutorResult, MockExecutor, CLIConfig, load_tasks_from_file, create_mcp_client, run_compound_loop, format_result_text, format_result_json, cli, run, list_tasks, history, autonomous
  integrations/agentverse/cohezion_agent.py: CohezionAgentAdapter
  integrations/agentverse/cohezion_environment.py: CohezionEnvironment, CohezionSimulationEnvironment, CohezionTaskSolvingEnvironment
  integrations/agentverse/compound_loop.py: LoopConfig, IterationResult, LoopResult, CompoundBenchmarkLoop
  integrations/agentverse/llm_executor.py: LLMExecutionResult, CircuitBreaker, LLMExecutor
  integrations/agentverse/rocm_executor.py: ROCmResult, ROCmExecutor, create_rocm_executor, main
  integrations/competition_rate_limiter.py: CompetitionRateLimiter, check_rate_limit
  integrations/flume_wiki_bridge.py: FlumeWikiBridge, FlumeOuroborosBridge
  integrations/hermes_mcp_bridge.py: run_mcp_stdio
  integrations/kaggle_api.py: KaggleAPI
  integrations/kaggle_curation.py: KaggleCurator
  integrations/kaggle_eval.py: KaggleEvaluator
  integrations/kaggle_submission.py: KaggleSubmissionOrchestrator
  integrations/kaggle_submission_improved.py: KaggleSubmissionOrchestrator
  integrations/kaggle_training.py: KaggleTrainingManager
  integrations/kaggle_training_improved.py: KaggleTrainingManager
  integrations/obsidian_wiki.py: WikiPage, ObsidianWiki
  integrations/robinhood_analysis.py: Position, PortfolioSnapshot, PortfolioGoal, PortfolioGoalTracker, PortfolioAnalyzer, MultiModelConsensusGate, TradingMonitorLoop
  integrations/robinhood_bridge.py: TradeAction, TradeIntent, IntentAnalysis, OrderProposal, RobinhoodBridge
  integrations/telegram_bot.py: QueryComplexity, ModelSelection, safe_html, TelegramCommunicationHub
  integrations/ulogme_bridge.py: ActivityEntry, FocusSession, UlogmeBridge
  integrations/wiki_mirix_bridge.py: MemoryMapping, WikiMirixBridge
pkg knowledge (2 files)
  knowledge/llm_wiki.py: WikiEntry, LLMWiki
pkg knowledge_graph (14 files)
  knowledge_graph/bidirectional_linker.py: LinkType, BidirectionalLink, KnowledgeGraph, get_knowledge_graph, link_doc_to_doc, link_doc_to_code, link_skill_to_code, link_decision_to_code, link_pattern_to_code, main
  knowledge_graph/cli.py: main
  knowledge_graph/graphrag_engine.py: RetrievalResult, GraphRAGResponse, GraphRAGEngine
  knowledge_graph/query_engine.py: KnowledgeGraphQueryEngine
  knowledge_graph/scripts/kg_guard.py: find_related_learnings, run_kg_guard
  knowledge_graph/scripts/omega_distiller.py: load_processed, save_processed, generate_policy_stub, distill
  knowledge_graph/universe_artifact_migration.py: ArtifactMetadata, TrainingRunMetadata, MigrationSnapshot, UniverseArtifactMigration, main
  knowledge_graph/universe_genealogy_migration.py: UniverseEpoch, UniversePattern, CoherenceMeasurement, UniverseGenealogySurvey, main
pkg learning (10 files)
  learning/__init__.py: Pattern, PatternDetector, SkillGenerator, get_skill_generator
  learning/deep_research.py: SearchQuery, DeepResearchPipeline
  learning/mycelium_network.py: KnowledgeSpore, MyceliumNetwork
  learning/mycelium_registry.py: JournalEntry, SynthesizedSkill, AuditReport, MyceliumRegistry
  learning/ouroboros.py: ExecutionExhaust, OuroborosEngine, OuroborosAttribution
  learning/ouroboros_trigger.py: TriggerState, TrainingEvent, OuroborosTrigger
  learning/recorder.py: LearningRecorder, get_learning_recorder, reset_learning_recorder
  learning/shadow_scripter.py: TestGenStatus, GeneratedTest, ShadowScripter
  learning/skill_acquisition.py: SkillRegistryRequest, DynamicSkillAcquisition
  learning/vault_neuron_reader.py: VaultNeuronWriter
pkg mass_sim (12 files)
  mass_sim/agent_factory.py: AgentFactory
  mass_sim/analysis.py: SimulationAnalyzer
  mass_sim/artifacts.py: ArtifactGenerator
  mass_sim/batch_runner.py: BatchSimulationRunner
  mass_sim/config.py: ScaleTier, UniverseSpec, CheckpointData, UniverseResult, SimulationReport, SimulationConfig
  mass_sim/exporter.py: CheckpointExporter
  mass_sim/flume_physics_py.py: FlumePhysicsPy
  mass_sim/orchestrator.py: MassSimOrchestrator
  mass_sim/persistence.py: SimulationPersistence
  mass_sim/system_monitor.py: SystemVitals, get_vitals, MemoryGuard
  mass_sim/universe_factory.py: UniverseFactory
pkg mcp (101 files)
  mcp/agentskills_bridge.py: agentskills_execute
  mcp/audit.py: AuditResult, MCPAuditor, run_audit
  mcp/bmad_app.py: get_bmad_data_path, get_redis_url, get_engine, get_session_manager
  mcp/bmad_server.py: bmad_pm_prompt, bmad_dev_prompt, bmad_architect_prompt, bmad_qa_prompt, bmad_game_designer_prompt, bmad_game_dev_prompt, get_workflow_resource, get_agent_resource, list_modules_resource, main
  mcp/bmad_tools.py: bmad_help, bmad_load_skill, bmad_bmm_create_prd, bmad_bmm_create_story, bmad_bmm_sprint_planning, bmad_bmm_dev_story, bmad_bmm_code_review, bmad_gds_create_game_brief, bmad_gds_game_architecture
  mcp/bmad_tools_ext.py: bmad_cis_brainstorming, bmad_tea_test_design, bmad_bmb_create_agent, bmad_party_mode, bmad_list_workflows, bmad_list_agents, bmad_index_docs, bmad_status
  mcp/coherence_server.py: get_mcp, get_tracker, get_detector, list_tools, call_tool, main
  mcp/compound_server.py: compound_start_session, compound_check_alignment, compound_end_session, cache_get_metrics, cache_optimize, ralph_lopps_review, multiperspective_review, autoresearch_analyze, learning_capture, learning_process_execution, skill_refinement_apply, get_context_policy, update_context_policy, cohezion_batch_port_skills, cohezion_inspect_codebase, cohezion_skill_matrix, check_redis_health, main
  mcp/compound_session.py: MCPServerState, MCPInfrastructureState, CompoundMCPSessionManager, get_compound_mcp_manager, start_compound_mcp_infrastructure, stop_compound_mcp_infrastructure
  mcp/compound_unified.py: ServerState, UnifiedSessionCheckpoint, UnifiedCompoundManager, get_unified_manager
  mcp/compound_utils.py: mcp_tool, ok, err, McpClientResolver
  mcp/env_data_mcp.py: fetch_noaa_data, fetch_copernicus_data
  mcp/fleet.py: run_server_sync, main
  mcp/hookify_server.py: HookifyMCPBridge, create_hookify_mcp_server
  mcp/kaggle_server_mcp.py: kaggle_kernel_status, kaggle_kernel_push, kaggle_kernel_logs, kaggle_competition_submit, kaggle_competition_leaderboard, kaggle_competition_submissions, kaggle_quota, kaggle_config_view, kaggle_benchmark_tasks_list, kaggle_benchmark_tasks_status, kaggle_benchmark_tasks_run, kaggle_benchmark_models, kaggle_benchmark_tasks_download, kaggle_benchmark_tasks_logs
  mcp/knowledge_server.py: KnowledgeMCP, get_server, health, tool_search_knowledge, tool_get_skill, tool_list_skills, tool_get_context_chunk, create_app, main
  mcp/knowledge_server_mcp.py: search_knowledge, get_skill, list_skills
  mcp/lemonade_server_mcp.py: lemonade_list_models, lemonade_load_model, lemonade_chat, lemonade_analyze_image, lemonade_generate_image, lemonade_text_to_speech, lemonade_transcribe_audio, lemonade_server_status, main
  mcp/loop_mcp.py: queue_list, queue_file, queue_patch, proposals_query, proposals_append, event_publish, loop_stats, loop_health, main
  mcp/manager/auth.py: generate_ephemeral_token, get_current_token, validate_token, clear_token
  mcp/manager/defaults.py: init_default_servers
  mcp/manager/models.py: MCPServerConfig, PortAllocator
  mcp/manager/routes.py: index, health, start_server_handler, stop_server_handler, restart_server_handler, server_health_handler, main
  mcp/manager/server_manager.py: MCPServerManager, get_manager
  mcp/manager.py: MCPServer, ServerHealth, MCPConfig, MCPManager, SimpleMCP
  mcp/marimo_walkthroughs_mcp.py: compound_loop_metrics, flume_latent_summary, thermodynamic_gravity, lemonade_walkthrough_chat
  mcp/registry.py: MCPServer, MCPRegistry, get_registry
  mcp/research_server.py: ResearchMinerServer, get_server, health, tool_search_arxiv, tool_search_arxiv_advanced, tool_search_arxiv_by_author, tool_get_hf_trending, tool_get_hf_trending_models, tool_semantic_scholar_paper, tool_papers_with_code_link, tool_list_research_channels, tool_list_arxiv_categories, tool_list_hf_tasks, create_app, main
  mcp/research_server_mcp.py: search_arxiv, get_hf_trending, list_research_channels
  mcp/scripts/mcp_guard.py: check_latency_violations, check_harness_exists, extract_tools_from_file, sync_registry, sync_platform_settings
  mcp/servers/bmad/_shared.py: BMADEngine, get_engine
  mcp/servers/bmad/engine.py: BMADEngine
  mcp/servers/bmad/proactive_monitor.py: ProactiveSuggestion, PatternMatch, ProactiveMonitor, main
  mcp/servers/bmad/routes_bmb.py: tool_bmad_bmb_create_agent, tool_bmad_party_mode, tool_bmad_bmb_create_workflow, tool_bmad_bmb_create_module, tool_bmad_bmb_customize_agent, tool_bmad_bmb_import_workflow, tool_bmad_bmb_extend_tool
  mcp/servers/bmad/routes_bmm.py: tool_bmad_help, tool_bmad_bmm_create_prd, tool_bmad_bmm_create_story, tool_bmad_bmm_sprint_planning, tool_bmad_bmm_dev_story, tool_bmad_bmm_code_review, tool_bmad_list_workflows, tool_bmad_list_agents, tool_bmad_index_docs, tool_bmad_status, tool_bmad_doc_retrieve
  mcp/servers/bmad/routes_bmm_ops.py: tool_bmad_bmm_validate_prd, tool_bmad_bmm_create_architecture, tool_bmad_bmm_retrospective, tool_bmad_bmm_release_planning, tool_bmad_bmm_estimate_effort, tool_bmad_bmm_deployment_strategy, tool_bmad_bmm_monitoring_strategy, tool_bmad_bmm_incident_response, tool_bmad_bmm_security_review, tool_bmad_bmm_performance_optimization
  mcp/servers/bmad/routes_cis.py: tool_bmad_cis_brainstorming, tool_bmad_cis_design_thinking, tool_bmad_cis_six_thinking_hats, tool_bmad_cis_scamper, tool_bmad_cis_worst_possible_idea, tool_bmad_cis_mind_mapping
  mcp/servers/bmad/routes_gds.py: tool_bmad_gds_create_game_brief, tool_bmad_gds_game_architecture, tool_bmad_gds_playtest_session, tool_bmad_gds_level_design, tool_bmad_gds_ui_ux, tool_bmad_gds_monetization, tool_bmad_gds_narrative_design, tool_bmad_gds_balance_economy, tool_bmad_gds_audio_design, tool_bmad_gds_multiplayer_architecture, tool_bmad_gds_procedural_generation, tool_bmad_gds_analytics
  mcp/servers/bmad/routes_general.py: tool_bmad_search, tool_bmad_recommend, tool_bmad_analyze_project, tool_bmad_quick_start, tool_bmad_export_session, tool_bmad_import_session
  mcp/servers/bmad/routes_proactive.py: proactive_scan, proactive_execute, proactive_summary, proactive_enable_pattern, proactive_list_patterns, scan_route, execute_route, summary_route, enable_pattern_route, list_patterns_route, proactive_record_feedback, proactive_pattern_effectiveness, proactive_cleanup, record_feedback_route, pattern_effectiveness_route, cleanup_route
  mcp/servers/bmad/routes_tea.py: tool_bmad_tea_test_design, tool_bmad_tea_test_automation, tool_bmad_tea_load_testing, tool_bmad_tea_security_testing, tool_bmad_tea_accessibility_testing, tool_bmad_tea_api_testing
  mcp/servers/bmad/server.py: health, index, get_workflow_resource, get_agent_resource, list_modules_resource, create_app, main
  mcp/servers/doc/indexer.py: DocChunk, TokenCounter, SmartChunker, OllamaEmbedder, SimpleSurrealStore, DocumentIndexer, DocRetrieverSession, create_indexer, index_bmad_docs
  mcp/servers/doc/server.py: get_indexer, health, index, tool_resolve_library, tool_query_docs, tool_index_library, tool_get_stats, create_app, main
  mcp/servers/git/server.py: GitContext, health, index, tool_git_status, tool_git_diff, tool_git_log, tool_git_branches, tool_git_info, create_app, main
  mcp/servers/github/server.py: get_github_token, GitHubService, get_service, github_search_repos, github_get_repo, github_create_issue, github_create_issue_comment, github_list_issues, github_get_user
  mcp/servers/huggingface/server.py: get_hf_api_token, HuggingFaceService, get_service, hf_search_models, hf_get_model_info, hf_search_datasets, hf_search_spaces, hf_inference, hf_get_readme
  mcp/servers/journey/server.py: health, index, tool_journey_start, tool_journey_list, create_app, main
  mcp/servers/memory/server.py: get_surreal_url, Entity, Relation, MemoryGraph, get_graph, health, index, tool_create_entity, tool_get_entity, tool_add_observation, tool_create_relation, tool_search, tool_get_related, tool_export, create_app, main
  mcp/servers/plasma/models.py: Particle, ExoticVacuumObject
  mcp/servers/plasma/server.py: health, index, tool_find_slp, tool_park_context, tool_create_simulation, tool_add_particle, tool_step, tool_get_exotic, tool_get_hiho, tool_get_field, tool_400_year, main
  mcp/servers/plasma/simulation.py: PlasmaSimulation, get_simulation
  mcp/servers/report/server.py: Report, MarimoReportGenerator, get_generator, health, index, tool_generate, tool_serve, tool_export, tool_list, main
  mcp/servers/rewards/server.py: get_reward_status, get_leaderboard
  mcp/servers/safe_input.py: sanitize_path, sanitize_log
  mcp/servers/security/scanner.py: Vulnerability, SecurityChecklist, build_severity_report
  mcp/servers/security/server.py: SecurityScanner, get_scanner, health, index, tool_scan_file, tool_scan_project, tool_get_checklist, tool_generate_report, create_app, main
  mcp/servers/sequential/server.py: Thought, ThinkingSession, get_session, health, index, tool_think, tool_revise, tool_branch, tool_get_sequence, tool_get_session, create_app, main
  mcp/servers/simulate/server.py: health, index, tool_run_simulation, create_app, main
  mcp/servers/skills/cache.py: SkillsCache
  mcp/servers/skills/client.py: Skill, SkillsShClient
  mcp/servers/skills/server.py: get_client, get_cache, health, index, tool_skills_search, tool_skills_get, tool_skills_install, tool_skills_execute, tool_skills_list, tool_skills_categories, tool_skills_sync, tool_skills_cache_info, create_app, main
  mcp/servers/stitch/client.py: StitchDesign, DarkPattern, StitchMCPClient
  mcp/servers/template/server.py: WeatherService, get_service, health, index, tool_get_weather, tool_get_forecast, tool_search_cities, resource_city, create_app, main
  mcp/servers/traceability/server.py: traceability_run_engine, traceability_run_health, traceability_trigger_party, traceability_get_dashboard, traceability_get_findings, traceability_auto_commit, get_health_resource, get_findings_resource, main
  mcp/servers/vault/__init__.py: run_server, main, run_stdio_server
  mcp/shared/auth.py: get_api_key, api_key_middleware
  mcp/shared/client.py: MCPClient
  mcp/shared/logging.py: VaultLogHandler, VaultLogger, get_logger
  mcp/shared/server.py: run_server
  mcp/shared/session.py: get_redis_url, SessionManager, get_session_manager
  mcp/skills_server.py: SkillsMCP, get_server
  mcp/skills_server_mcp.py: invoke_skill, register_skill, search_skills, list_all_skills
  mcp/surreal_server.py: SurrealMCP, get_server
  mcp/surreal_server_mcp.py: query_nodes, store_node, search_similar, store_learning, query_learnings, sync_key_learnings
  mcp/swarm_server.py: SwarmMCP, get_server, health, tool_run_debate, tool_get_perspectives, create_app, main
  mcp/swarm_server_mcp.py: run_debate, get_perspectives, get_swarm_metrics
  mcp/webmcp_bridge.py: WebMCPBridge
  mcp/wiki_mcp.py: WikiMCP
pkg memory (7 files)
  memory/consolidator.py: ConsolidatedFact, MemoryConsolidator
  memory/mem0_adapter.py: mem0_available, Mem0Config, disable_telemetry, build_local_mem0
  memory/service.py: CohezionMemory
  memory/surreal_graph.py: SurrealMemoryGraph
  memory/surreal_vector_store.py: OutputData, SurrealVectorStore, register_surreal_provider
  memory/trust_hierarchy.py: TrustTier, TrustedFact, GroundTruthHierarchy
pkg model (5 files)
  model/cohezion_lm.py: CohezionLMConfig, build_cohezion_lm
  model/hiho_attention.py: hiho_kernel, hiho_kernel_numpy, is_torch_available
  model/train.py: train, main
  model/training_data.py: TrainingExample, TrainingDataset, load_autoresearch_data, load_stealthskater_corpus, build_training_dataset, build_balanced_training_dataset
pkg models (6 files)
  models/birdclef_baseline.py: BirdClassificationHead, BirdCLEFBaseline
  models/model_registry.py: ModelRegistry
  models/perch_v2_adapter.py: PerchV2Adapter
  models/rho_selector.py: HarnessCandidate, RHOSelection, select_harness_update, select_harness_update_from_log, generate_harness_candidates, rho_proposal_record, rho_selection_margin
  models/routing_log.py: record_routing_decision, read_routing_decisions, TuningProposal, propose_tuning, propose_tuning_from_log, SpecialistProposal, propose_specialists, build_inference_neuron, deposit_inference_neuron
pkg mycelium (5 files)
  mycelium/loop.py: CoverageLoop
  mycelium/observer.py: ChangeObserver
  mycelium/registry.py: MyceliumCluster, MyceliumRegistry
  mycelium/scripter.py: ShadowScripter
pkg observability (5 files)
  observability/claude_usage.py: UsageRecord, WindowUsage, summarize_usage, usage_guard, load_usage_records
  observability/gpu_monitor.py: GPUMetrics, ThermalProfilingResult, GPUMonitor
  observability/metrics_analytics.py: MetricsTrend, PerformanceReport, MetricsAnalytics
  observability/unified_metrics.py: InferenceMetrics, UnifiedMetricsCollector, get_metrics_collector
pkg optimization (2 files)
  optimization/r_zero.py: RZeroMetrics, LocalModelOptimizer
pkg ouroboros (8 files)
  ouroboros/card_alignment_monitor.py: AlignmentVerdict, CardAlignmentMonitor
  ouroboros/detector.py: AnomalyDetector
  ouroboros/failure_analyzer.py: FailureAnalysis, OuroborosFailureAnalyzer
  ouroboros/healer.py: HealerAgent
  ouroboros/monitor.py: OuroborosMonitor
  ouroboros/recorder.py: OuroborosRecorder
  ouroboros/wiki_integration.py: OuroborosWikiBridge, OuroborosWikiEngine
pkg patterns (2 files)
  patterns/hermetic_design_patterns.py: DesignIntention, IntentionalClass, MentalismPattern, FractalPattern, FractalComponent, CorrespondencePattern, VibrationState, VibrationalFunction, VibrationPattern, Polarity, PolarFeature, PolarityPattern, BreathPhase, BreathCycle, RhythmPattern, CausalChain, CauseEffectPattern, GenderPrinciple, GenderBalancedDesign, GenderPattern, HermeticDesign, HermeticDesignSystem
pkg persistence (4 files)
  persistence/genesis_persistence.py: persist_journey_transition, persist_universe_snapshot, persist_prompt_artifact, get_journey_transitions, get_transition_count
  persistence/obsidian_mcp.py: ObsidianMemoryMCP
  persistence/surreal_logger.py: SurrealTrajectoryLogger
pkg physics (42 files)
  physics/anomaly_gate.py: InvariantKind, InvariantSpec, AnomalyVerdict, AnomalyGate, SkepticVerdict, LocalSkeptic, adjudicate
  physics/anomaly_quarantine.py: QuarantineRecord, AnomalyQuarantine
  physics/bec_bridge.py: BECState, MercuryLattice
  physics/bioelectric_model.py: CognitiveLightCone, PercolationResult, BioelectricNetwork
  physics/cellular_automata.py: WolframClass, CARule, CAState, ComplexityMetrics, CAEngine, CosmogonyStep, CosmogonyCA, LemonadeCAAdvisor, ca_rl_step, TotalisticRule2D, CAGrid2D, EVOPattern, ComplexityMetrics2D, EVOEmergence
  physics/colibre_bridge.py: ColibreState, AgentAsEVO, load_swift_snapshot
  physics/conservation_filter.py: Verdict, ConservationResult, ConservationFilter
  physics/cosmogony.py: SymmetryGroup, PhaseTransitionEvent, CosmogonyState, ZeroAlgebra, SymmetryBreaking, get_cosmogony, CosmicScaleHierarchy
  physics/dielectric.py: DielectricField
  physics/dimension_extractor.py: DimensionExtractor
  physics/evo_model.py: WitnessMark, ExoticVacuumObject
  physics/fiber_bundle.py: FiberBundleState, FiberBundle
  physics/flier_routing.py: QubitNode, FLIERRouter
  physics/gauge_theory.py: FieldStrength, GaugeConnection, FourFabricGauge
  physics/hamiltonian.py: PotentialType, HamiltonianDynamics
  physics/information_geometry.py: FisherInformationMetric, compute_vae_fisher_metric
  physics/invariant_checker.py: ObligationStatus, ObligationResult, InvariantReport, InvariantChecker
  physics/ionic_cluster.py: IonicClusterState
  physics/lagrangian.py: Potential, LagrangianDynamics, hiho_potential, harmonic_potential
  physics/lenr.py: LENRHamiltonian
  physics/manifold_utils.py: SemanticLagrangeFinder
  physics/mereon_data.py: get_m144p_vertices, get_m120p_vertices
  physics/mereon_projector.py: ProjectionResult, MereonProjector
  physics/mhd_mereon.py: MHDState, MHDMereonOperator, simulate_mereon_mhd_flow
  physics/mhd_plasma.py: MHDEquilibrium, BismuthDiamagnet
  physics/natural_capital.py: EcosystemServiceMetrics, SeventhGenerationProjection, NaturalCapitalValuation
  physics/observer_patch.py: ObserverPatch, overlap_fraction, verify_observer_consistency, ConsistencyResult, evo_observer_consistency, stack_delays, signal_at_observer, FrequencyDispersedDelay, RetardedField, compute_retarded_delay
  physics/ouroboros_bridge.py: HealingPhase, PhysicsAnomaly, HealingEvent, OuroborosBridge
  physics/quantum/peaked_solver.py: PeakedCircuitSolver
  physics/quantum/utils.py: reconstruct_site_map, compute_seti_metrics
  physics/rewards_bridge.py: CoherenceRatchet, RewardsBridge
  physics/riemannian_glide.py: RiemannianGlideTrajectory
  physics/riemannian_metric.py: RiemannianMetric, euclidean_metric, hiho_metric, fabric_block_metric
  physics/sarfatti_bridge.py: SarfattiBackAction, QuarkGluonPlasma
  physics/spinor.py: SpinorState, commutator, verify_su2_algebra
  physics/tensor_metric_engineering.py: TensorMetricEngineering
  physics/thermodynamic_gravity.py: OttoWorkLeg, ThermodynamicGravity, donnan_potential_to_work_leg
  physics/toroidal_moment.py: FractalToroidalMoment
  physics/usd_simulator.py: ItonicCluster, USDSimulator
  physics/vliw_bridge.py: ExecutionMode, KernelBenchmark, VLIWBridgeState, VLIWBridge
pkg pipeline (5 files)
  pipeline/hyperparameter_debate.py: HyperparameterDebate
  pipeline/incremental_trainer.py: IncrementalResult, IncrementalVAETrainer, IncrementalRLTrainer
  pipeline/trained_navigator.py: TrainedNavigator
  pipeline/weight_bridge.py: WeightBridge
pkg pipelines (1 files)
pkg platform (17 files)
  platform/agent_evaluation.py: ViolationSeverity, ConstitutionalPrinciple, SafetyViolation, CharterComplianceScore, AgentExecutionContext, AgentEvaluationResult, AnthropicAlignedEvaluator, get_agent_evaluator, reset_agent_evaluator
  platform/agnostic_integrations.py: IDEIntegrationAdapter, AntigravityIDEAdapter, ClaudeCodeAdapter, ZedCodeAdapter, AgnosticExecutionBroker
  platform/coherence_tracker.py: CoherenceMetrics, CoherenceTracker, get_coherence_tracker, reset_coherence_tracker
  platform/daily_health_digest.py: HealthStatus, RepositoryMetrics, TestMetrics, DependencyMetrics, CICDMetrics, HealthCheckResult, HealthDigest, DailyHealthDigest, get_daily_health_digest, reset_daily_health_digest
  platform/edl_router.py: ExpertStream, StreamRecommendation, EDLConsensus, ExpertDomainRouter, get_edl_router, reset_edl_router
  platform/journey_logger.py: Journey, JourneyLogger, get_journey_logger, reset_journey_logger
  platform/mcp_server.py: ObsidianVaultMCP
  platform/memory_pressure.py: PressureLevel, MemoryPressureEvent, classify_pressure, MemoryPressureMonitor, get_pressure_monitor
  platform/observable_action.py: ActionProposal, ObservableActionProposer, get_observable_proposer, reset_observable_proposer
  platform/oom_evictor.py: LoadedModel, Eviction, OOMEvictor, PressureDriver, install_oom_evictor
  platform/resource_manager.py: ResourceUnavailableError, OOMRiskError, oom_safe_to_load, PlatformMemoryState, TrainingLock, ResourceClient, ResourceDaemon
  platform/session_tracker.py: ModelUsageEvent, SessionRecord, SessionTracker
  platform/skill_analytics_charter.py: CharterSkillInsights, CharterAlignedSkillAnalytics, get_skill_analytics, reset_skill_analytics
  platform/skill_scorer_charter.py: CharterSkillScore, CharterAlignedSkillScorer, get_skill_scorer, reset_skill_scorer
  platform/skill_tracker_charter.py: SkillUsageEvent, CharterAlignedSkillTracker, get_skill_tracker, reset_skill_tracker
  platform/tier_optimizer.py: TierRecommendation, TierChange, TierOptimizer
pkg policies (1 files)
pkg precipitation (5 files)
  precipitation/bus.py: PrecipitationBus, get_bus, set_bus, emit, aemit
  precipitation/events.py: PrecipitationKind, zero_twelve_d, compute_fabric_breakdown, PrecipitationEvent
  precipitation/orchestrator.py: OrchestratorConfig, GenerationRecord, PrecipitationOrchestrator
  precipitation/sinks.py: VaultSink, SurrealSink, GitLedgerSink, register_default_sinks
pkg protocols (6 files)
  protocols/a2a_server.py: TaskState, A2AMessage, A2ATask, AgentCard, A2AServer, A2AClient
  protocols/agent_protocols/handoffs.py: AgentHandoff, HandoffManager
  protocols/sovereignty/filter.py: SovereigntyConfig, SovereigntyFilter
  protocols/stitch/composer.py: StitchSkillDefinition, StitchSkillComposer
  protocols/ucp_capability_handler.py: UCPCapability, UCPInvocationResult, UCPCapabilityHandler
pkg real_envs (2 files)
pkg recursive_trace (4 files)
  recursive_trace/core.py: TraceTask, RecursiveTraceResult, TraceMemory, LatentStateTracker, RecursiveTraceLoop
  recursive_trace/coupling_analysis.py: coupling_delta, permutation_pvalue, analyze_domain
  recursive_trace/resolution_log.py: record_resolution, log_quality_gate_resolution, read_resolutions
pkg registry (11 files)
  registry/autonomous_registration.py: RegisteredSkill, RegistrationConflict, AutonomousSkillRegistry
  registry/capability_registry.py: Capability, CapabilityRegistry
  registry/compound_version_registry.py: VersionEntry, CompoundVersionRegistry
  registry/dependency_scanner.py: Severity, CVEAlert, DeprecationWarning, ScanReport, DependencySecurityScanner
  registry/hooks.py: RegistryEvent, RegistryHook, HookManager, get_hook_manager
  registry/ouroboros_version_healer.py: HealingOutcome, ConflictResolutionProposal, HealingEvent, OuroborosVersionHealer
  registry/skill_registry.py: load_registry, register_skill, search_skills, auto_sync
  registry/version_telemetry.py: DriftStatus, DependencyDrift, VersionConflict, VersionHealthPanel, VersionTelemetry
  registry/version_traceability_gate.py: VersionContract, ReleaseImpactReport, EpicCompletionGate, VersionTraceabilityGate
pkg reliability (17 files)
  reliability/__init__.py: CircuitState, CircuitStats, CircuitBreaker, get_circuit
  reliability/batch_manager.py: BatchManager
  reliability/blackwell_handshake.py: BlackwellHandshake
  reliability/circuit_breaker.py: CircuitState, Circuit, CircuitOpenError, get_circuit
  reliability/context_harness.py: ContextHarness
  reliability/heartbeat.py: update_heartbeat, get_heartbeats
  reliability/memory_manager.py: MemoryManager
  reliability/monitor.py: ResourceMonitor, get_resource_monitor
  reliability/offload_manager.py: OffloadManager
  reliability/pool.py: ConnectionPool, get_pool, close_all_pools
  reliability/quantum_performance_monitor.py: MetricType, AlertLevel, ActionType, PerformanceMetric, AlertCondition, AutoSwapDecision, QuantumPerformanceMonitor
  reliability/residency_awareness.py: ResidencyAnchorBase, get_residency_anchors
  reliability/resolver.py: HallucinationResolver
  reliability/resource_guard.py: SystemVitals, ResourceGuard
  reliability/semantic_cache.py: SemanticCache
  reliability/sync.py: FileLock, SafeWriter, AgentWorkspace
  reliability/viscoelastic.py: ViscoelasticController
pkg reporting (2 files)
  reporting/nightly.py: NightlyReporter
pkg research (23 files)
  research/__init__.py: get_version
  research/adaptive_refinement.py: SkillMetrics, SkillRefinement, AdaptiveSkillRefiner, integrate_with_research, SkillRefinementPlugin
  research/agent.py: ResearchSession, ResearchAgent
  research/autocontext.py: monitor, compress, budget, archive
  research/autoresearch.py: ResearchResult, AutoResearcher
  research/autoresearch_driver.py: ExperimentOutcome, AutoresearchDriver
  research/checkpoint.py: ResearchCheckpoint, CheckpointPersistence, WarmCheckpointLoader
  research/config.py: ResearchConfig, ExperimentResult
  research/consensus.py: ConsensusVote, ConsensusResult, PartyModeConsensus
  research/cost_optimization.py: CostBudget, ExperimentCost, CostTracker, CostAwareRouter, create_cost_tracker, integrate_with_research_agent, estimate_experiment_cost, get_cheapest_model, calculate_session_budget
  research/flume_integration.py: HyperparameterConfig, FLUMEResearchOptimizer, LatentSpaceExplorer, create_flume_optimizer, integrate_with_research_agent
  research/multi_agent.py: MultiAgentResearchConfig, MultiAgentResult, ResearchSwarm, SimpleMultiAgent
  research/orborous.py: Orborous
  research/research_squad.py: OptimizationResult, DegradationSignal, ResearchSquad, integrate_with_compound_system
  research/resource_guarded_autoresearch.py: ResourceLimits, AgentResourceUsage, ResourceGuard, ResearchSubAgent, MultiAgentAutoresearch, create_resource_guarded_autoresearch
  research/scripts/autoresearch_daemon.py: run_autoresearch
  research/scripts/benchmark_research.py: benchmark_session
  research/scripts/benchmark_research_agent.py: run_benchmark
  research/scripts/benchmark_wiki.py: WikiBenchmark, main
  research/scripts/comprehensive_discovery_with_learnings.py: log_learning, discover_all_models_comprehensive, infer_capabilities_from_name
  research/security.py: CodeChange, ValidationResult, ResearchSecurityGuardrails, SimpleSecurity
  research/security_api.py: RateLimitEntry, RateLimiter, get_client_id, rate_limit, APIKeyManager, verify_api_key, require_scope, sanitize_input, validate_session_id, HealthChecker, AuditLogger
  research/training.py: TrainingExecutor, SimpleTrainingRunner
pkg researcher (7 files)
  researcher/daily_researcher.py: LockTimeout, FleetLock, PreflightFleetCheck, DryRunReport, ModelScoutLane, HarnessPaperLane, DatameshSynthesisLane, VerifyEvolveLane, DailyResearcher
  researcher/lanes/datamesh_synthesis.py: SynthesisNote, DatameshSynthesisLane
  researcher/lanes/harness_paper.py: HarnessPaperLane
  researcher/lanes/model_scout.py: ModelScoutLane
  researcher/lanes/verify_evolve.py: VerifyEvolveLane
pkg resilience (3 files)
  resilience/manager.py: AutonomicManager, get_rah_manager
  resilience/strategies.py: HealingStrategy, ModelSwapStrategy, ContextReductionStrategy, SystemRestartStrategy
pkg rewards (4 files)
  rewards/calculator.py: RewardCalculator
  rewards/ratchet.py: RatchetMechanism
  rewards/system.py: RewardSystem
pkg rl (11 files)
  rl/causal_interpreter.py: InterventionResult, ActivationPatcher, CausalInterventionTester, InterpretabilityReport
  rl/distributed_trainer.py: DistributedConfig, ScalingMetrics, DistributedPPOTrainer, DistributedLauncher, ScalingBenchmark
  rl/environment.py: FlumeNavEnv
  rl/evo.py: EthericVariantOscillator, EVOTracker, load_evo_trajectory, evo_to_jsonl
  rl/grpo_trainer.py: GRPOConfig, GRPOMetrics, GRPOTrainer, AsyncGRPOTrainer, create_grpo_trainer
  rl/lora_trainer.py: LoRAConfig, LoRALayer, LoRAModel, LoRALinearWrapper, SFTTrainer, RLHFTrainer
  rl/ppo_trainer.py: TRIUNEPolicy, ValueNetwork, PPOConfig, PPOTrainer, EpisodeResult, train
  rl/reward_shaping.py: CoherenceReward, DiversityBonus, StabilityPenalty, HamiltonianReward, CompositeReward
  rl/task_generator.py: TaskSpec, TaskGenerator, clamp
  rl/trainer.py: PolicyNetwork, TrainingConfig, EpisodeResult, train
pkg sandbox (7 files)
  sandbox/executor.py: ResourceLimitType, ExecutorEventType, ResourceLimits, ResourceMetrics, AuditEntry, SandboxRequest, SandboxResult, SandboxExecutor, get_executor
  sandbox/hooks.py: HookStage, HookAction, HookMetadata, Hook, HookResult, ExecutionContext, HookDiscovery, HookExecutor, HookRegistry, HookIntegration, get_hook_integration
  sandbox/isolation.py: IsolationMode, IsolationStatus, ChangeType, MountPoint, Change, NetworkNamespace, IsolationConfig, IsolationContext, CleanupResult, FilesystemIsolation, ProcessIsolation, NetworkIsolation, CleanupRegistry, IsolationManager, get_isolation_manager
  sandbox/rollback.py: ChangeType, AuditEventType, SnapshotBackendType, Change, AuditEntry, Snapshot, Checkpoint, TransactionConfig, TransactionResult, RollbackResult, AuditLog, SnapshotBackend, GitSnapshotBackend, BtrfsSnapshotBackend, JsonlSnapshotBackend, HybridSnapshotBackend, Transaction, TransactionManager, get_transaction_manager
  sandbox/safety.py: RiskLevel, ViolationSeverity, Violation, SafetyPolicy, SafetyCheckResult, Monitor, PreFlightChecker, RiskAssessor, ConstraintEnforcer, SafetyHarness
  sandbox/shadow_worktree.py: ShadowWorktree
pkg sandboxing (2 files)
  sandboxing/executor.py: ResourceLimits, SandboxResult, SandboxBackend, DockerSandbox, FirecrackerSandbox, SandboxManager
pkg scripts (10 files)
  scripts/analyze_telemetry.py: ExecutionPattern, load_telemetry_files, extract_pattern, analyze_patterns, export_analysis, main
  scripts/async_guard.py: AsyncGuard, scan_file, main
  scripts/auto_refine_skills.py: classify_skill, trigger_refinement, export_canonical, main
  scripts/coherence_inspector.py: main
  scripts/detect_hermes_change.py: setup_logging, get_hermes_version, get_config_mtime, get_model_info, get_providers, compute_change_hash, load_state, save_state, check_for_changes, apply_tuned_settings, apply_routing_policy, run_hermes_doctor, auto_apply_mode, check_only_mode, state_report, main
  scripts/dogfooding_monitor.py: capture_metrics, monitor_loop
  scripts/experiment_e70_tdd_adversarial.py: TestStatus, TDDTestCase, TDDTestSuite, AdversarialPersona, BlindHunter, EdgeCaseHunter, AcceptanceAuditor, SecurityPredator, PerformanceVulture, AdversarialReviewOrchestrator, CapabilityStack, TDDAdversarialExperiment, experiment_e70_tdd_adversarial
  scripts/skill_validator.py: ValidationResult, SkillValidator, main
  scripts/telemetry_dashboard.py: load_metrics, print_dashboard, main
pkg security (36 files)
  security/adversarial_tester.py: TestResult, TestMetrics, test_single_pattern, run_test_batch, AdversarialTester, main
  security/agent_auth.py: AgentCredential, AgentAuthManager
  security/api_key_auth.py: APIKeyValidator, get_validator, reset_validator
  security/apikey_auth_middleware.py: APIKeyAuthMiddleware
  security/attack_patterns.py: AttackCategory, AttackPattern, get_pattern_count, get_patterns_by_category, generate_mutated_patterns, mutate_pattern, generate_test_batch
  security/audit.py: AuditEvent, AuditLogger, get_audit_logger
  security/audit_log.py: AuditAction, AuditLogEntry, AuditLogger
  security/auth.py: AuthError, verify_api_key, create_token, verify_token, hash_password, verify_password, check_role
  security/cert_generator.py: CertificateGenerator
  security/consent_manager.py: ConsentScope, ConsentToken, ConsentManager
  security/constitutional_enforcer.py: ViolationType, Violation, ConstitutionalEnforcer, ConstitutionalGuardrail
  security/constitutional_shield.py: AuditVerdict, AuditRecord, ConstitutionalShield
  security/credentials.py: CredentialManager, get_credentials
  security/ethical_framework.py: EthicalPrinciple, RiskLevel, EthicalAssessment, EthicalFramework
  security/eval_awareness_defense.py: CanaryToken, EvalAwarenessResult, EvalAwarenessDefense
  security/file_lock_context.py: FileLockError, FileLock, locked_file_operation, atomic_file_write, atomic_file_read, atomic_file_modify
  security/guardrail_adapters.py: NoOpGuard, ConstitutionalGuard, PromptInjectionGuard, ResourceGuard, RateLimitGuard, OutputFilterGuard
  security/guardrail_factory.py: create_default_pipeline, create_minimal_pipeline, create_strict_pipeline
  security/guardrail_pipeline.py: GuardrailAction, GuardrailResult, GuardrailStats, Guardrail, GuardrailPipeline
  security/https_middleware.py: HTTPSEnforcementMiddleware, SecureCookieMiddleware, create_https_app
  security/log_redactor.py: RedactionFilter, setup_redaction, setup_root_redaction
  security/mcp_https_client.py: MCPHTTPSClient
  security/memory_barrier.py: BarrierViolationError, GTTAllocation, BarrierEvent, MemoryMappedBarrier
  security/middleware.py: add_security_middleware, create_context_harness
  security/output_filter.py: FilterResult, FilteredOutput, InsightPacketGenerator, OutputFilter
  security/pipeline.py: GuardrailAction, GuardrailResult, SecurityPolicy, Guardrail, SecurityPipeline, SimpleSecurity
  security/pre_commit_config.py: PreCommitConfiguration
  security/prompt_guard.py: ThreatLevel, PromptAnalysis, normalize_text, PromptGuard
  security/provenance_hash.py: ProvenanceRecord, ProvenanceRegistry
  security/rate_limiter.py: RateLimitConfig, TokenBucket, RateLimitResult, RateLimiter, get_rate_limiter, reset_rate_limiter
  security/sandbox_security.py: PenetrationResult, SandboxAuditEvent, SandboxRedTeam
  security/tee_key_manager.py: KeyAccessMode, SecurityEvent, TEEKeyManager
  security/tls_config.py: TLSConfig, get_tls_config, reset_tls_config
  security/validators.py: ValidationResult, ValidationError, validate_input, sanitize_text, validate_json_field
  security/vault.py: BitwardenVault, get_vault
pkg services (5 files)
  services/agent_service.py: AgentConfig, AgentStatus, AgentService
  services/knowledge_service.py: KnowledgeNode, KnowledgeEdge, KnowledgeQuery, KnowledgeService
  services/physics_service.py: PhysicsConfig, PhysicsAnalysis, PhysicsService
  services/swarm_service.py: QuadratureConfig, QuadratureResult, QuadraturePhase, SwarmService
pkg sessions (3 files)
  sessions/__main__.py: main
  sessions/session_bus.py: MessageKind, SessionRegistry, SessionBus
pkg simulation (13 files)
  simulation/analysis_prime.py: SimulationAnalyzer
  simulation/benchmark_runner.py: BenchmarkConfig, BenchmarkMetrics, BenchmarkRunner
  simulation/distributed.py: ShardSpec, AgentState, ShardMetrics, GlobalMetrics, compute_shard_layout, ShardWorker, CoherenceAggregator, ShardedUniverse
  simulation/emergent_detector.py: EmergentEvent, EmergenceReport, EmergentDetector
  simulation/enhanced_simulator.py: FlumeTrajectoryPoint, FlumeIntegration, AllostaticaChallenge, RZeroSolution, RZeroEvaluation, RZeroEnhancedTriad, EnhancedSimulationResult, EnhancedSimulator, main
  simulation/fractal_universe.py: Sector, StabilizerAgent, RedTeamAgent, BlueTeamAgent, UniverseGrid, FractalSimulator
  simulation/glass_box_debate.py: run_simulation, visualize_debate
  simulation/lifecycle_presim.py: SimulationStep, TopologicalKnot, PreSimResult, LifecyclePreSimulator
  simulation/rl_framework.py: Transition, ExperienceBuffer, HihoEnvironment, PolicyNetwork, ValueNetwork, PPOAgent, train_hiho_agent
  simulation/simulation_logger.py: SimulationLogger
  simulation/simulation_validator.py: ValidationResult, ValidationReport, SimulationValidator, validate_from_parquet
  simulation/vectorized_env.py: VectorizedHihoEnv, AsyncVectorizedHihoEnv, ScheduleType, CurriculumConfig, CurriculumScheduler, train_vectorized_ppo
pkg simulations (5 files)
  simulations/regime_benchmark.py: RegimeBenchmark
  simulations/sundarbans_restoration.py: MockRegimeProvider, run_sundarbans_simulation
  simulations/surgical_benchmark.py: SurgicalRegimeBenchmark, main
  simulations/symphony_max_benchmark.py: SymphonyMaxBenchmark, main
pkg skillopt (6 files)
  skillopt/lemonade_backend.py: LemonadeBackend
  skillopt/runner.py: run_skillopt, main
  skillopt/surreal_trajectory_loader.py: load_trajectories, dump_corpus, list_skills_with_traces
  skillopt/trace_augmentor.py: SurrealTraceAugmentor, make_augmentor
  skillopt/trace_writer.py: SurrealTraceWriter, make_trace_writer
pkg skills (29 files)
  skills/cohezion_mcp.py: CohezionMCP
  skills/kaggle/modules/badge-collector/scripts/badge_registry.py: Badge, get_badges_by_phase, get_automatable_badges, get_badge_by_id
  skills/kaggle/modules/badge-collector/scripts/badge_tracker.py: load_progress, save_progress, set_status, get_status, is_earned, should_attempt, print_status_table
  skills/kaggle/modules/badge-collector/scripts/orchestrator.py: dry_run, run_phase, main
  skills/kaggle/modules/badge-collector/scripts/phase_1_instant_api.py: run
  skills/kaggle/modules/badge-collector/scripts/phase_2_competition.py: run
  skills/kaggle/modules/badge-collector/scripts/phase_3_pipeline.py: run
  skills/kaggle/modules/badge-collector/scripts/phase_4_browser.py: run
  skills/kaggle/modules/badge-collector/scripts/phase_5_streaks.py: run
  skills/kaggle/modules/badge-collector/scripts/templates/utility_script.py: generate_report
  skills/kaggle/modules/badge-collector/scripts/utils.py: get_username, get_kaggle_cli, run_kaggle_cli, make_temp_dir, check_credentials, resource_name, slug
  skills/kaggle/modules/comp-report/scripts/competition_details.py: is_writeup_kernel, get_competition_files, get_leaderboard, get_top_kernels, get_details, main
  skills/kaggle/modules/comp-report/scripts/list_competitions.py: extract_slug, competition_to_dict, is_hackathon, classify_status, within_lookback, fetch_competitions, main
  skills/kaggle/modules/comp-report/scripts/utils.py: get_api, get_username, get_kaggle_cli, check_credentials, unwrap_response, rate_limit
  skills/kaggle/modules/kllm/scripts/check_credentials.py: check_credentials
  skills/kaggle/modules/kllm/scripts/kagglehub_download.py: download_dataset, download_model
  skills/kaggle/modules/kllm/scripts/kagglehub_publish.py: publish_dataset, publish_model
  skills/kaggle/modules/registration/scripts/check_registration.py: check_registration
  skills/kaggle/shared/check_all_credentials.py: check_all_credentials
  skills/mcp_inference_tools.py: elite_ocr_analysis, agentic_coding_workflow, compound_engineering_orchestrator, pocket_tts_generate
  skills/mcp_model_tools.py: elite_model_selection, performance_benchmark, get_compound_config, select_model
  skills/mcp_paths.py: cohezion_root, skill_registry_path, workflow_registry_path, knowledge_graph_path, model_registry_path, compound_config_path, load_json
  skills/mcp_reliability_tools.py: resolve_claims, offload_task, batch_offload, inspect_cache
  skills/mcp_skill_tools.py: execute_skill, get_truth_anchors, remember_fact, recall_context, daily_scout_research
  skills/mcp_tool_definitions.py: build_tool_list
pkg storage (2 files)
  storage/surreal_client.py: TrajectoryNode, SurrealDBClient
pkg substrate (5 files)
  substrate/hardware_monitor.py: marginal_power_w, joules_per_token, HardwareMetrics, HardwareMonitor, get_hardware_monitor
  substrate/kv_cache_tracker.py: KVCacheEntry, AllocationResult, KVCacheTracker
  substrate/overload_coordinator.py: ProtectionLevel, ProtectionAction, ProtectionConfig, OverloadCoordinator, OverloadError
  substrate/popcorn.py: SubmitResult, submit
pkg swarm (101 files)
  swarm/adaptive_router.py: RoutingDecision, RoutingHistory, TaskAnalyzer, AdaptiveRouter, route_task
  swarm/agent_factory.py: AgentConfig, AgentFactory
  swarm/agents/anti_pattern_scout.py: AntiPatternScout
  swarm/agents/arc_agi_3_wrapper.py: ARCAGI3Env, RecursiveChainOfThought
  swarm/agents/architecture_scout.py: ArchitectureScout
  swarm/agents/base_scout.py: Finding, ASTSummary, BaseScout
  swarm/agents/code_review_swarm.py: SwarmReport, CodeReviewSwarm
  swarm/agents/eigent_agent.py: EigentAgent
  swarm/agents/pattern_scout.py: PatternScout
  swarm/agents/quality_scout.py: QualityScout
  swarm/anomaly_detector.py: AnomalyType, AnomalyAlert, ModelCostHistory, AnomalyDetector, get_anomaly_detector, reset_anomaly_detector
  swarm/auto_improving_parser.py: LearnedPattern, PatternLearner, AutoImprovementResult, AutoImprovingParser, demo_auto_improvement
  swarm/autoresearch/base.py: ExperimentResult, ResearchDriver
  swarm/autoresearch_executor.py: AutoresearchExecutor
  swarm/batch_processor.py: CacheEntry, BatchItem, BatchResult, BatchProcessor
  swarm/compat.py: SwarmOrchestrator, LegacyAgentResult, AgentCapability
  swarm/compound_client.py: create_compound_client, get_compound_client, reset_compound_client
  swarm/compute_backend_router.py: BackendType, BackendStatus, BackendCapability, RoutingDecision, BackendConstraints, ComputeBackendRouter, route_compute
  swarm/context_model_router.py: ModelContextProfile
  swarm/core/edge_gateway.py: EdgeNode, RegistrationRequest, EdgeGateway, get_edge_gateway
  swarm/cost_aware_router.py: QueryComplexity, ModelRoutingDecision, RoutingStatistics, QueryComplexityAnalyzer, CostAwareRouter, get_cost_aware_router, reset_cost_aware_router
  swarm/democratic_debate.py: AgentRole, AgentPersona, VoteValue, AgentVote, DebateRound, DebateSession, DemocraticDebate, run_improvement_debate
  swarm/deterministic_discovery_with_skill_fallback.py: DeterministicDiscovery, HeuristicDiscovery, BalancedModelDiscovery, run_balanced_discovery
  swarm/dynamic_agent_registry.py: AgentModule, DynamicAgentRegistry, get_global_registry, reset_global_registry
  swarm/dynamic_concurrency_gate.py: HardwareMetrics, HardwareProfilerFactory, ConcurrencyDecision, DynamicConcurrencyGate, get_concurrency_gate
  swarm/dynamic_levers.py: LeverGoal, LeverRange, DynamicLever, DynamicLeverSystem, create_default_lever_system, demo_levers
  swarm/dynamic_model_router.py: IDEPriority, ModelTier, ModelConfig, MemoryBandwidthAnalyzer, AdaptiveTemplateManager, DynamicModelRouter, get_router, main
  swarm/execution_orchestrator.py: TaskResult, ExecutionReport, ExecutionOrchestrator
  swarm/fallback_strategy.py: CircuitBreakerState, ModelHealthMetrics, FallbackEvent, CircuitBreaker, FallbackStrategy, get_fallback_strategy, reset_fallback_strategy
  swarm/gemma4_router.py: RoutingDecision, Gemma4Router
  swarm/hardware_aware_router.py: Priority, RoutingRequest, RoutingDecision
  swarm/hf_modelfile_builder.py: HFModelfileBuilder, main
  swarm/hiho_vector_engine.py: HihoVectorEngine
  swarm/improved_deterministic_parser.py: FLMFormatPattern, ImprovedFLMParser, AutoImprovementCycle, test_improved_parser
  swarm/intelligence_pipeline.py: ModelProfile, OrchestrationRequest, SandboxManager, MixtureOfExpertsRouter
  swarm/journey_narrator.py: JourneyNarrator
  swarm/latent_research_team.py: SotaInferenceReport, LatentSwarmResearchTeam
  swarm/lemonade_manager.py: LemonadeManager
  swarm/lemonade_model_enhancer.py: LemonadeModelEnhancer, demo_enhanced_discovery
  swarm/lru_persistent_cache.py: LRUPersistentCache
  swarm/lru_persistent_token_cache.py: LRUPersistentTokenCache
  swarm/meta_learner.py: LearningStrategy, MetaLearningRecord, MetaLearner, demo_meta_learner
  swarm/mitosis_apoptosis.py: AgentState, MitosisEvent, ApoptosisEvent, SwarmGovernor
  swarm/mode_controller.py: SystemMode, ModeController, get_mode_controller
  swarm/model_adapter.py: ModelSelection, SmartRouterAdapter
  swarm/model_capability_registry.py: ModelCapability, ModelBenchmark, ModelProfile, ModelCapabilityRegistry, discover_and_benchmark_all_models
  swarm/model_capability_registry_resource_safe.py: ResourceConstraints, ResourceGuard, ResourceSafeModelCapabilityRegistry, run_resource_safe_discovery
  swarm/model_fallback_strategy.py: CircuitBreakerState, ModelHealthMetrics, ModelCircuitBreaker, ModelFallbackStrategy, get_fallback_strategy, reset_fallback_strategy
  swarm/model_manager.py: ModelMetrics, ModelConfig, OllamaModelManager, get_manager
  swarm/model_pool_config.py: ModelTierPolicy, PooledModel, TierConfig, PoolStatus
  swarm/model_pool_manager.py: ModelPoolManager, get_pool_manager, reset_pool_manager
  swarm/model_ranker.py: RankingStrategy, ModelScore, ModelRanker
  swarm/multi_agent_orchestrator.py: ExecutionResult, TaskContext, MultiAgentOrchestrator, get_orchestrator, execute_task, quick_orchestrate
  swarm/multi_layer_cache.py: CacheEntry, ContextPoolEntry, KVCacheMetrics, SemanticCacheStore, ContextPoolManager, KVCacheOptimizer, MultiLayerCache
  swarm/ollama_context_manager.py: TaskType, TruncationStrategy, ModelContextProfile, ContextConfig, OllamaContextManager, main
  swarm/ollama_resilience.py: ResilientOllamaClient
  swarm/orchestrator.py: Agent, Task, AgentResult, SwarmConfig, Swarm, SimpleSwarm
  swarm/parser_v3_validation_oracle.py: ValidationResult, ValidationOracle, ParserV3, demo_validation_oracle
  swarm/persistent_cache.py: CacheEntry, PersistentCache, get_persistent_cache
  swarm/persistent_token_cache.py: PersistentTokenCache
  swarm/plasma_swarm_router.py: EvoTopologyRequest, PlasmaSwarmRouter
  swarm/predictive_lever_adjuster.py: AdjustmentFeatures, PredictionResult, SimplePredictionModel, HumanApprovalRequest, PredictiveLeverAdjuster, demo_predictive_adjuster
  swarm/providers/gemini_provider.py: GeminiProvider
  swarm/providers/gemma4_provider.py: Gemma4Provider
  swarm/providers/lemonade_provider.py: LemonadeProvider
  swarm/providers/model_provider.py: GenerationResult, ModelProvider, register_model_provider, get_model_provider, list_providers
  swarm/providers/multi_model_orchestrator.py: ComputeUnit, ModelType, ModelProfile, MultiModelOrchestrator, demo
  swarm/providers/ollama_provider.py: OllamaProvider
  swarm/providers/tip_spear_provider.py: ModelSize, ReasoningMode, TipSpearProfile, TipSpearProvider, demo
  swarm/quadrature_nexus.py: VoiceType, QuadratureProposal, VoiceResponse, QuadratureResult, StrategicDirective, QuadratureNexus
  swarm/r_zero_evolver.py: RZeroEvolver
  swarm/redundancy_suppression.py: RedundancyManager
  swarm/research_orchestrator.py: ResearchFinding, CompoundSynthesis, TokenBudgetManager, HuggingFaceAgent, ArXivAgent, GitHubAgent, WebAgent, SynthesisEngine, ResearchOrchestrator, run_research
  swarm/resonance.py: ResonanceState, ResonanceProtocol, SwarmOrchestrator
  swarm/routing_orchestrator.py: UnifiedRoutingDecision, RoutingOrchestrator
  swarm/scripts/a2a_guard.py: sync_a2a
  swarm/scripts/agent_guard.py: load_config, generate_markdown, sync_agents
  swarm/scripts/github_scout.py: load_processed, save_processed, poll_github
  swarm/scripts/routing_guard.py: extract_models_from_py, get_master_models, sync_platform_config, run_guard
  swarm/semantic_cache.py: EmbeddingResult, SemanticCacheHit, EmbeddingModel, DistilledEmbeddingModel, FlumeVAEEmbeddingModel, SemanticCache
  swarm/smart_router.py: TaskType, ModelCapability, ModelProfile, RoutingDecision, AgentAction, SmartRouter, get_router, smart_execute
  swarm/specialist_agents.py: AgentMetadata, ToolDefinition, ToolRegistry, ToolNotFoundError, SpecialistAgent, get_specialist, list_validated_specialists, list_all_specialists
  swarm/swarm_types.py: Perspective, ThoughtVector, Contradiction, CritiqueResult, SynthesizedResponse, SwarmConfig
  swarm/team_execution.py: TeamCompoundExecutor
  swarm/team_metrics.py: WaveMetrics, TeamCompoundMetrics, TeamMetricsAggregator
  swarm/team_orchestrator.py: AgentSpec, TaskSpec, TeamPlan, TeamOrchestrator
  swarm/tip_of_spear_router.py: ModelTier, ConstitutionalViolation, SovereigntyCheckResult, RoutingResult, ConstitutionalChecker, TipOfTheSpearRouter
  swarm/token_cache_optimizer.py: CacheOptimizationConfig, TokenCacheOptimizer, get_token_cache_optimizer
  swarm/token_client.py: ResilientOllamaClient, TokenEfficientClient
  swarm/topological_router.py: SpectralFeatures, TopologicalRegime, AgentTopology, RoutingDecision, TopologicalRouter
  swarm/triune_consensus.py: AgentProposal, GeometricEquilibrium, ConsensusReport, TriuneConsensus
  swarm/triune_integration.py: TriuneState, Doer, Knowera, TriuneAGI, demo_triune_agi
  swarm/unified_thinker.py: ReasoningState, JEPAWorldModel, EpisodicMemory, SimplifiedEncoder, UnifiedThinker, demo_unified_thinker
  swarm/vmodel_engineering.py: VPhase, VVerification, VPhaseState, LeverAdjustmentLifecycle, VModelEngineeringProcess, VModelIntegratedLeverSystem, demo_vmodel_integration
  swarm/vmodel_phase_optimizer.py: PhaseMetrics, BottleneckAnalysis, PhaseOptimizer, InstrumentedVModelEngineering, demo_phase_optimizer
  swarm/workflows/debate_protocol.py: DebateWorkflow, main
pkg tools (2 files)
  tools/test_generator.py: FunctionInfo, ClassInfo, ModuleInfo, TestGenerator, main
pkg traceability (5 files)
  traceability/plan_graph.py: PlanGraph
  traceability/record_commit.py: main
  traceability/record_touch.py: main
  traceability/register_plan.py: parse_plan, slug_from_filename, register_plan, main
pkg universe (30 files)
  universe/advanced_components.py: SacredGeometryEngine, PenroseTwistorEngine, QuantumEmergenceEngine, BioelectricsEngine, EsotericPhysicsEngine, KordylewskiSwarmEngine, PlasmaMCPEngine
  universe/adversarial_grounding.py: PerturbationResult, HallucinationAlert, AdversarialGrounding
  universe/agentic_env.py: ToolResult, ToolCall, ToolResponse, ToolSpec, ToolRegistry, SuccessCriterionType, SuccessCriterion, TaskScenario, EnvObservation, StepRecord, AgenticEnvironment, TrajectoryRecorder, build_coding_scenarios
  universe/agentic_evo_mhd.py: IonizationState, EVOMagneticState, MHDField, AgenticEVOMHD, AgenticMHDSystem, demo_mhd_simulation
  universe/agentic_evo_swift.py: VacuumCoherence, EVOLatentState, EVOPhysicalState, EVOCoupling, AgenticEVO, AgenticEVOSimulation, demo_agentic_evo_simulation
  universe/capability_eval.py: TaskDomain, ScoringMethod, Difficulty, ScoringCriterion, ScoringRubric, EvalTask, TaskSuite, CriterionResult, TaskResult, SuiteResult, AgentProtocol, EvalScorer, EvalRunner, RegressionAlert, RegressionReport, RegressionDetector, build_core_capability_suite
  universe/components.py: CellularAutomataState, CellularAutomataEngine, ChaosTheoryParameters, ChaosTheoryEngine, EvoState, MagnetohydrodynamicsEngine, EVOInitializationFactory, HIHOStabilizationEngine
  universe/divergence.py: DivergenceStatus, DivergenceDetector
  universe/engine.py: AxiomaticState, LatentState, TrajectoryPoint, UniverseJourney, EncoderProtocol, UniverseSimulationEngine, SimpleEncoder
  universe/evo_simulation.py: VacuumState, JourneyEvent, ExoticVacuumObject, FLUMEJourneyStream, VAIEMetrics, EVOSimulation, demo_simulation
  universe/experiment_tracker.py: RunStatus, MetricEntry, CheckpointRef, RunConfig, ExperimentRun, MetricComparison, RunComparison, ExperimentTracker, tracked_training_run
  universe/factory.py: UniverseSpec, Universe, UniverseFactory
  universe/freeze_frame.py: FreezeFrame, FreezeFrameCapture, FreezeFrameStore
  universe/hiho_unified_engine.py: HIHOUnifiedEngine
  universe/intent_action_sync.py: IntentActionPair, SyncVerdict, IntentActionSync
  universe/intent_capture.py: IntentPayload, IntentViolation, StateChangeRequest, CheckResult, IntentCapture
  universe/llm_training_bridge.py: TrajectoryStep, AgentTrajectory, PreferencePair, JudgmentAssessment, TokenReward, TrajectoryToReward, PreferencePairGenerator, JudgmentEvaluator, ExperienceDataset
  universe/sandbox.py: SandboxResult, ContainerizedUniverse
  universe/sandbox_backends.py: BackendResult, IsolationBackend, DockerBackend, SystemdRunBackend, SubprocessBackend, select_backend
  universe/sandbox_manager.py: SandboxInstance, SandboxManager, get_sandbox_manager
  universe/sandbox_profiles.py: SandboxTier, SandboxProfile, get_profile
  universe/sandbox_results.py: persist_result
  universe/spatial_phonons.py: PhononParameters, SpatialPhononsEngine
  universe/triune_engine.py: TriuneSimulationEngine
  universe/triune_manifold.py: TriuneState, calculate_hiho_coherence, compute_restoring_force
  universe/truth_anchor.py: TruthAnchor, CoherenceBubble, RestoringForceResult, ValidationResult, TruthAnchorValidator
  universe/viz_bridge.py: VisualizationBridge
pkg validation (4 files)
  validation/agent_schema.py: AgentFileValidationError, AgentFileSchema, extract_frontmatter, validate_agent_file, validate_all_agent_files, generate_agent_frontmatter
  validation/calibration_harness.py: get_project_root, redact_pii, load_local_logs, save_calibration_profile, run_parameter_sweep
  validation/constitutional.py: ConstitutionalShield, ManifoldEquilibrium
pkg vanguard (5 files)
  vanguard/attribution.py: LicenseStatus, AttributionMetadata, AttributedRecord, AttributionEngine
  vanguard/connectors.py: VanguardScoutReport, HuggingFaceConnector, GitHubTrendingConnector, RedditConnector, OllamaConnector, VanguardScout
  vanguard/sandbox_validation.py: ValidationVerdict, SandboxScript, ValidationReport, SubstrateSandbox
  vanguard/source_connector.py: SourceHealth, DiscoveryRecord, SourceHealthReport, SourceConnector, ArXivConnector, FailingConnector
pkg vibe (7 files)
  vibe/compiler.py: VibeCompiler
  vibe/orchestrator.py: VibeOrchestrator
  vibe/parser.py: VibeParser
  vibe/specifier.py: VibeSpecifier
  vibe/types.py: OperationType, VibeIntent, NodeDescription, EdgeDescription, VibeWorkflowSpec
pkg wiring (2 files)
  wiring/orphan_bridge.py: verify_wiring
pkg world_model (9 files)
  world_model/jepa_world_model.py: ManifoldEncoder, ActionEncoder, Predictor, CausalMask, TrainingMetrics, JEPAWorldModel, generate_synthetic_training_data
  world_model/jepa_world_model_persistent.py: JEPAWorldModelPersistent
  world_model/observer.py: Observer
  world_model/observer_world_model.py: ObserverWorldModel, get_default_observer_model
  world_model/sigreg.py: SIGReg
  world_model/surprise_action_gate.py: GateOutcome, SurpriseActionGate
  world_model/surprise_explorer.py: SurpriseRegion, SurpriseExplorer
  world_model/surprise_router.py: ActionMode, SurpriseDecision, SurpriseRouter
pkg worldviews (3 files)
  worldviews/tradition_data.py: StepMapping, UniqueContribution, Tradition, Convergence, get_traditions, get_tradition, get_step_across_traditions, get_convergences
  worldviews/vault_graph.py: GraphNode, GraphEdge, VaultGraph, parse_cortex, get_vault_graph

table CONVERGES_TO: WIRE-GAP(no code refs)
table DEPENDS_ON: WIRE-GAP(no code refs)
table IMPLEMENTS: refs=1
table INTRODUCES: WIRE-GAP(no code refs)
table MANAGES: WIRE-GAP(no code refs)
table MONITORS: WIRE-GAP(no code refs)
table OPTIMIZES: WIRE-GAP(no code refs)
table adjacent_to: WIRE-GAP(no code refs)
table agent_journey: refs=11
table agent_task: refs=1
table agt_lecture: WIRE-GAP(no code refs)
table alternative_to: WIRE-GAP(no code refs)
table arc_agi3_ingest_summary: WIRE-GAP(no code refs)
table ard_run: WIRE-GAP(no code refs)
table automerge_log: refs=1
table beta_belief_ledger: WIRE-GAP(no code refs)
table code_module: refs=1
table cognitive_profile: refs=2
table cohezion_mem0_live2: WIRE-GAP(no code refs)
table complements: refs=2
table compound_learnings: refs=1
table compound_local_run: WIRE-GAP(no code refs)
table compound_loop: refs=6
table concept: refs=38
table data_product_event: refs=6
table derived_from: WIRE-GAP(no code refs)
table documents: refs=20
table evo_experiment: WIRE-GAP(no code refs)
table evo_journey: refs=1
table evo_vacuum: refs=2
table execution_trace: refs=6
table experiment_run: WIRE-GAP(no code refs)
table experiment_runs: refs=1
table fable_prompt: WIRE-GAP(no code refs)
table fact: refs=18
table feeds: refs=17
table fixture_run: refs=1
table fleet_lock: refs=3
table fleet_node: WIRE-GAP(no code refs)
table fleet_research: refs=5
table gate_review: WIRE-GAP(no code refs)
table golden_fixture: refs=3
table grounds: refs=2
table hash_chain: refs=2
table implements: refs=31
table implements_spec: WIRE-GAP(no code refs)
table import_drift: refs=2
table inference_bench: WIRE-GAP(no code refs)
table influences: refs=2
table informed_by: refs=4
table integration: refs=168
table inward_analysis: WIRE-GAP(no code refs)
table journey_knowledge: WIRE-GAP(no code refs)
table journey_point: refs=4
table journey_roundtrip: WIRE-GAP(no code refs)
table journey_transition: refs=1
table kanban_item: refs=2
table learning: refs=139
table learnings: refs=54
table led_to: refs=1
table link: refs=34
table located_in: WIRE-GAP(no code refs)
table mem0_df: WIRE-GAP(no code refs)
table mem0migrations: WIRE-GAP(no code refs)
table model_capabilities: WIRE-GAP(no code refs)
table model_performance: refs=2
table model_specialties: WIRE-GAP(no code refs)
table mycelium_patterns: refs=3
table mycelium_skill: WIRE-GAP(no code refs)
table narrative_learning: refs=2
table neuron: refs=18
table paper: refs=56
table part_of: WIRE-GAP(no code refs)
table physics_session: WIRE-GAP(no code refs)
table precipitation_event: refs=2
table prompt_version: refs=1
table proof_obligation: refs=3
table qa_gate: refs=4
table quality_gate: refs=2
table references: refs=41
table replaces: refs=19
table research_brief: WIRE-GAP(no code refs)
table research_consumer: WIRE-GAP(no code refs)
table research_finding: refs=1
table research_item: WIRE-GAP(no code refs)
table research_source: WIRE-GAP(no code refs)
table research_tools: WIRE-GAP(no code refs)
table research_topic: WIRE-GAP(no code refs)
table semantic_fact: refs=1
table service_registry: WIRE-GAP(no code refs)
table session_bus: refs=5
table session_message: WIRE-GAP(no code refs)
table session_presence: WIRE-GAP(no code refs)
table session_recovery: WIRE-GAP(no code refs)
table session_registry: refs=1
table shadow_portfolio: WIRE-GAP(no code refs)
table similar_to: WIRE-GAP(no code refs)
table snapshots: refs=25
table source_document: WIRE-GAP(no code refs)
table spawned: refs=10
table state_transitions: WIRE-GAP(no code refs)
table telegram_telemetry: refs=1
table test: refs=303
table thesis_hypothesis: WIRE-GAP(no code refs)
table traces: refs=39
table trajectory: refs=171
table transition_to: refs=1
table universe_node: refs=3
table universe_region: WIRE-GAP(no code refs)
table vault_neuron: refs=6
table vmodel_gate: refs=8
table yielded: refs=5

hook SessionStart[all]: bash
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/check-settings-size.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/autocompact-calibrate.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/version-watch.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/_safe_run.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/reload-skills-on-update.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/lemonade-warmup.sh
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/session-register.sh
hook SessionStart[all]: python3
hook SessionStart[all]: /home/mike-anderson/.claude/hooks/session-title.sh
hook PreToolUse[Bash]: /home/mike-anderson/.claude/hooks/pre-bash-check.sh
hook PreToolUse[Bash]: python3
hook PreToolUse[Write]: python3
hook PreToolUse[Agent]: /home/mike-anderson/.claude/hooks/lemonade-research-gate.sh
hook PostCompact[all]: /home/mike-anderson/.claude/hooks/post-compact-context.sh
hook PostToolUse[Bash]: /home/mike-anderson/.claude/hooks/post-bash-cleanup.sh
hook PostToolUse[Edit|Write]: /home/mike-anderson/.claude/hooks/post-edit-lint.sh
hook PostToolUse[Bash|Write|Edit]: python3
hook PostToolUse[TaskUpdate]: /home/mike-anderson/.claude/hooks/retro-watch.sh
hook PostToolUse[Write|Edit]: /home/mike-anderson/.claude/hooks/compound-self-improve.sh
hook PostToolUseFailure[all]: python3
hook PermissionDenied[all]: /home/mike-anderson/.claude/hooks/on-permission-denied.sh
hook PreCompact[*]: /home/mike-anderson/.claude/hooks/pre-compact-checkpoint.sh
hook UserPromptSubmit[all]: /home/mike-anderson/.claude/hooks/autoresearch-context.sh
hook UserPromptSubmit[all]: python3
hook UserPromptSubmit[all]: /home/mike-anderson/.claude/hooks/session-inbox.sh
hook UserPromptSubmit[all]: /home/mike-anderson/.claude/hooks/retro-watch.sh
hook UserPromptSubmit[all]: /home/mike-anderson/.claude/hooks/ponytail-gate.sh
hook Stop[all]: /home/mike-anderson/.claude/hooks/autoresearch-stop.sh

skills[global] (100): agent-claim-verification, aiter-kernel-parameter-semantics, aiter-mxfp4-api-limitations, amd-ctypes-hip-kernel-dispatch, amd-gemm-mxfp4-optimization, amd-gfx950-tl-dot-scaled-constraints, amd-mla-decode-optimization, amd-moe-mxfp4-optimization, amd-speedrun-research-baseline, amd-triton-jit-callsite-correctness, autoharness-init, autoharness-skill, autoharness-update, autoresearch, autoresearch-team, autoresearch-team-long, benchmark-experiment-design, check-git-log-before-low-level-unlock, ci-green-ruff-fractal-campaign, claude-code-agent-teams, claude-code-bouncer-extension, claude-code-bwrap-sandbox-missing-bind, claude-code-token-optimization, claude-code-transcript-replay-file-recovery, close-deferral, cohezion-dynamic-modularity, cohezion-extend-availability, cohezion-land, competition-research-untapped, competitive-kernel-optimization-ceiling, compound-build, deepseek-mla-decode-flash-attention-gap, dreamserver-lemonade-external, dynamic-template-generator, electron-appimage-erofs-fix, evo-loop-fleet-operations, evo-loop-hiho-coherence-init, evo-loop-research-grounding, falsifiable-eval-harness, find-skills …
skills[vault] (44): a2a-per-specialist-agent-cards, a3-metaheuristic-optimizer, arc-agi-onnx-zero-param, claude-code-hook-stdin-protocol, cohezion-ecological-percolation-env, cohezion-orphan-wiring-sweep, compound-monitoring-serialization, compound-self-improvement-lm-wiring, eigent-lemonade-local-inference, fail-open-compound-gate, fleet-registry-gateway-pattern, frontier-oracle-cascade, got-aggregate-hierarchical-synthesis, gstack-canary-cohezion, gstack-cso-cohezion, gstack-scope-drift-review, hermes-cron-daemon-audit, kaggle-kernel-push-traps, kaggle-midnight-submit-mcp, kaggle-notebook-data-mount, kaggle-savekernel-rate-limit, kaggle-wellbore-tvt-spatial, land-worktree-onto-consolidated-main, lemonade-gguf-vulkan-no-logprobs, lemonade-mcp-models-as-tools, lemonade-nomic-embed-batch-limit, lemonade-omni-recipe-health-probe, lemonade-resource-advisor, lemonade-url-research-task, local-first-honest-backend-attribution, npu-exclusive-slot-benchmarking, playwright-precommit-artifact-conflict, playwright-webgl-headless, pyright-bughunt-workflow, python-venv-package-corruption-triage, report-findings-fallback, research-daemon-local-inference-consumer, robinhood-backtest-daemon, session-recovery-triage, strix-halo-fleet-research …
skills[repo_prime] (252): 3d_rendering, ADAPTIVE_TEMPLATE_PRIME, ADVERSARIAL_TDD_PRIME, ADVERSARIAL_TESTING_PRIME, AGENTIC_DESIGN_PRIME, AGENTJET_PRIME, AGENT_CONFIG_PRIME, AGENT_SOVEREIGNTY_ETHICS_PRIME, AGUI_EVENT_STREAMING_PRIME, AMBIENT_SONIFICATION_PRIME, AMD_GEMM_MXFP4_PRIME, AMD_MLA_DECODE_PRIME, AMD_MOE_MXFP4_PRIME, ANTHROPIC_SKILL_BUILDER_PRIME, ANTI_PATTERN_DEFENSE_PRIME, ANTI_PATTERN_GUARDIAN_PRIME, API_ERROR_RESILIENCE_PRIME, ARC_INTERACTIVE_REASONING, ARC_TOPOLOGICAL_PIVOT_PRIME, ASCENSION_SKILL_PRIME, AUTODQA_PRIME, AUTOHARNESS_PRIME, AUTONOMIC_ANALYST_PRIME, AUTONOMIC_EVOLUTION_PRIME, AUTONOMIC_HEALING_PRIME, AUTONOMIC_QUALITY_GUARD_PRIME, AUTONOMIC_RESEARCH_PRIME, AUTONOMOUS_RESILIENCE_PRIME, AUTORESEARCH_PRIME, BATCHING_PROTOCOL_PRIME, BEC_MHD_BRIDGE, BLACKWELL_HARDWARE_OPTIMIZATION_PRIME, BRAINSTORMING_PRIME, CAPABILITY_REGISTRY_PRIME, CITATIONS_PRIME, CI_INFRASTRUCTURE_FIXES_S104, CLAUDE_SPECIALIST_PRIME, CODEBASE_COHERENCE_PRIME, COLIBRE_BRIDGE, COMPOUND_ENGINEERING_PRIME …

labs orphan zone (12): cascade_orchestrator.py, compound_daemon.py, fleet_control.py, fleet_roster.py, kaggle_autopilot.py, local_inference_optimization_daemon.py, oreilly_harvest.py, research_daemon.py, review_draft.py, review_gate.py, robinhood_backtest.py, roster_research.py
