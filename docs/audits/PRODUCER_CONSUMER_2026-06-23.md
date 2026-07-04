# Cohezion Producer/Consumer Audit
Generated: 2026-06-23 | Model: llama3.2-1b-FLM | Modules: 87

## Summary

| Module | Role | Wiring Gap |
|--------|------|------------|
| `agent` | UNKNOWN | parse failed |
| `agentjet` | PRODUCER | EmbeddingContext |
| `agents` | UNKNOWN | parse failed |
| `api` | UNKNOWN | parse failed |
| `api` | UNKNOWN | parse failed |
| `arc` | PRODUCER |  |
| `audio` | PRODUCER | Bioacoustic encoder, Neural audio streaming, Narrator, Moshi client, Bioacoustic |
| `benchmarks` | PRODUCER | ... |
| `branding` | UNKNOWN | parse failed |
| `cache` | PRODUCER | None |
| `cli` | PRODUCER |  |
| `competition` | PRODUCER | partial parse |
| `compound` | PRODUCER | Legacy API |
| `concurrency` | PRODUCER |  |
| `config` | PRODUCER | None |
| `core` | PRODUCER | ... |
| `cost_optimization` | UNKNOWN | parse failed |
| `data_mesh` | UNKNOWN | parse failed |
| `datamesh` | PRODUCER |  |
| `deployment` | PRODUCER | None |
| `dogfooding` | PRODUCER |  |
| `environments` | PRODUCER |  |
| `eval` | PRODUCER | None |
| `evaluation` | PRODUCER | None |
| `evo` | PRODUCER | data-flow |
| `evolution` | PRODUCER | data is passed from producer to consumer |
| `flume` | UNKNOWN | parse failed |
| `flux` | UNKNOWN | parse failed |
| `gateway` | PRODUCER | None |
| `governance` | PRODUCER |  |
| `graph` | UNKNOWN | parse failed |
| `healing` | UNKNOWN | parse failed |
| `hookify` | UNKNOWN | parse failed |
| `inference` | UNKNOWN | parse failed |
| `infrastructure` | PRODUCER | data |
| `integrations` | PRODUCER | ... |
| `knowledge` | CONSUMER | None |
| `knowledge_graph` | UNKNOWN | parse failed |
| `learning` | UNKNOWN | parse failed |
| `mass_sim` | UNKNOWN | parse failed |
| `mcp` | PRODUCER | None |
| `memory` | PRODUCER |  |
| `model` | PRODUCER |  |
| `models` | PRODUCER | infrastructure |
| `mycelium` | PRODUCER | None |
| `observability` | PRODUCER |  |
| `optimization` | PRODUCER | None |
| `ouroboros` | PRODUCER | ... |
| `patterns` | PRODUCER | ... |
| `persistence` | PRODUCER | None |
| `physics` | UNKNOWN | parse failed |
| `pipeline` | PRODUCER | data flow from input to output |
| `pipelines` | PRODUCER |  |
| `platform` | UNKNOWN | parse failed |
| `policies` | PRODUCER | partial parse |
| `precipitation` | UNKNOWN | parse failed |
| `protocols` | PRODUCER | None |
| `real_envs` | PRODUCER | ... |
| `recursive_trace` | UNKNOWN | parse failed |
| `registry` | PRODUCER | None |
| `reliability` | UNKNOWN | parse failed |
| `reporting` | PRODUCER | None |
| `research` | PRODUCER |  |
| `resilience` | PRODUCER | ... |
| `rewards` | PRODUCER | None |
| `rl` | PRODUCER | ... |
| `sandbox` | UNKNOWN | parse failed |
| `sandboxing` | PRODUCER | containerized/isolated execution environments for untrusted code. |
| `scripts` | PRODUCER | null |
| `security` | PRODUCER | GuardrailPipeline |
| `services` | PRODUCER | services |
| `simulation` | UNKNOWN | parse failed |
| `simulations` | PRODUCER |  |
| `skillopt` | PRODUCER | None |
| `skills` | PRODUCER | ... |
| `storage` | CONSUMER | None |
| `substrate` | PRODUCER | null |
| `swarm` | PRODUCER |  |
| `tools` | PRODUCER | None |
| `traceability` | PRODUCER | None |
| `universe` | PRODUCER |  |
| `validation` | PRODUCER | None |
| `vanguard` | PRODUCER | None |
| `vibe` | PRODUCER | ... |
| `wiring` | PRODUCER | data flow from producer to consumer |
| `world_model` | PRODUCER |  |
| `worldviews` | PRODUCER | ... |

## Producers

### `agentjet`
- **Produces:** JSON
- **Consumes:** EmbeddingContext
- **Gap:** EmbeddingContext

### `arc`
- **Produces:** ARC

### `audio`
- **Produces:** audio
- **Consumes:** audio
- **Gap:** Bioacoustic encoder, Neural audio streaming, Narrator, Moshi client, Bioacoustic encoder, ProtoCLR

### `benchmarks`
- **Produces:** JSON
- **Consumes:** ...
- **Gap:** ...

### `cache`
- **Produces:** RedisSemanticCache
- **Consumes:** RedisCache
- **Gap:** None

### `cli`
- **Produces:** ['app']
- **Consumes:** ['__all__']

### `competition`
- **Gap:** partial parse

### `compound`
- **Produces:** JSON
- **Consumes:** Legacy API
- **Gap:** Legacy API

### `concurrency`
- **Produces:** ...
- **Consumes:** ...

### `config`
- **Produces:** JSON
- **Consumes:** COHEZION
- **Gap:** None

### `core`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `datamesh`
- **Produces:** JSON
- **Consumes:** cohezion.datamesh

### `deployment`
- **Produces:** JSON
- **Consumes:** cohezion.deployment.feature_flags
- **Gap:** None

### `dogfooding`
- **Produces:** JSON
- **Consumes:** CI/CD integration

### `environments`
- **Produces:** ['ManifoldEnv', 'SwarmEnv']

### `eval`
- **Produces:** JSON
- **Consumes:** cohezion.eval
- **Gap:** None

### `evaluation`
- **Produces:** EvaluationResult
- **Consumes:** SelfEvaluationEngine
- **Gap:** None

### `evo`
- **Produces:** data
- **Gap:** data-flow

### `evolution`
- **Produces:** data
- **Gap:** data is passed from producer to consumer

### `gateway`
- **Produces:** JSON
- **Consumes:** DemoGateway
- **Gap:** None

### `governance`
- **Produces:** CONSUMER

### `infrastructure`
- **Produces:** data
- **Consumes:** data
- **Gap:** data

### `integrations`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `mcp`
- **Produces:** mcp
- **Consumes:** audit
- **Gap:** None

### `memory`
- **Produces:** memory
- **Consumes:** trust_hierarchy

### `model`
- **Produces:** TrainingData
- **Consumes:** CohezionLM

### `models`
- **Produces:** routing_log
- **Consumes:** routing_log
- **Gap:** infrastructure

### `mycelium`
- **Produces:** CoverageLoop
- **Consumes:** ChangeObserver
- **Gap:** None

### `observability`
- **Produces:** JSON
- **Consumes:** Observability and metrics infrastructure.

### `optimization`
- **Produces:** RZeroMetrics
- **Consumes:** LocalModelOptimizer
- **Gap:** None

### `ouroboros`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `patterns`
- **Produces:** JSON
- **Consumes:** ...
- **Gap:** ...

### `persistence`
- **Produces:** SurrealTrajectoryLogger
- **Consumes:** ObsidianMemoryMCP
- **Gap:** None

### `pipeline`
- **Produces:** data
- **Consumes:** input
- **Gap:** data flow from input to output

### `pipelines`
- **Produces:** TraceabilityLink
- **Consumes:** TraceabilityPipeline

### `policies`
- **Gap:** partial parse

### `protocols`
- **Produces:** A2A Server
- **Consumes:** A2A Server
- **Gap:** None

### `real_envs`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `registry`
- **Produces:** JSON
- **Consumes:** cohezion.registry
- **Gap:** None

### `reporting`
- **Produces:** JSON
- **Consumes:** cohezion.reporting.nightly
- **Gap:** None

### `research`
- **Produces:** ExperimentResult
- **Consumes:** ResearchConfig

### `resilience`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `rewards`
- **Produces:** RewardCalculator
- **Consumes:** RewardSystem
- **Gap:** None

### `rl`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `sandboxing`
- **Produces:** output
- **Consumes:** input
- **Gap:** containerized/isolated execution environments for untrusted code.

### `scripts`
- **Produces:** scripts
- **Consumes:** cohezion.scripts
- **Gap:** null

### `security`
- **Produces:** GuardrailResult
- **Consumes:** GuardrailPipeline
- **Gap:** GuardrailPipeline

### `services`
- **Produces:** services
- **Consumes:** services
- **Gap:** services

### `simulations`
- **Produces:** RegimeBenchmark
- **Consumes:** MockRegimeProvider

### `skillopt`
- **Produces:** text-space skill optimizer using local silicon
- **Consumes:** LemonadeBackend
- **Gap:** None

### `skills`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `substrate`
- **Produces:** output
- **Consumes:** input
- **Gap:** null

### `swarm`
- **Produces:** swarm
- **Consumes:** swarm

### `tools`
- **Produces:** TestGenerator
- **Consumes:** TestGenerator
- **Gap:** None

### `traceability`
- **Produces:** JSON
- **Consumes:** Plan traceability graph -- SurrealDB persistence for plan lifecycle tracking.
- **Gap:** None

### `universe`
- **Produces:** 12D/2048D manifold simulation
- **Consumes:** Experiment tracking

### `validation`
- **Produces:** validation
- **Consumes:** agent_file_schema
- **Gap:** None

### `vanguard`
- **Produces:** JSON
- **Consumes:** SourceConnector
- **Gap:** None

### `vibe`
- **Produces:** ...
- **Consumes:** ...
- **Gap:** ...

### `wiring`
- **Produces:** data
- **Gap:** data flow from producer to consumer

### `world_model`
- **Produces:** world_model

### `worldviews`
- **Produces:** JSON
- **Consumes:** ...
- **Gap:** ...


## Consumers

### `knowledge`
- **Produces:** JSON
- **Consumes:** cohezion.knowledge.llm_wiki
- **Gap:** None

### `storage`
- **Produces:** TrajectoryNode
- **Consumes:** SurrealDBClient
- **Gap:** None

## Critical Wiring Gaps

- **agentjet** (PRODUCER): EmbeddingContext
- **audio** (PRODUCER): Bioacoustic encoder, Neural audio streaming, Narrator, Moshi client, Bioacoustic encoder, ProtoCLR
- **benchmarks** (PRODUCER): ...
- **cache** (PRODUCER): None
- **competition** (PRODUCER): partial parse
- **compound** (PRODUCER): Legacy API
- **config** (PRODUCER): None
- **core** (PRODUCER): ...
- **deployment** (PRODUCER): None
- **eval** (PRODUCER): None
- **evaluation** (PRODUCER): None
- **evo** (PRODUCER): data-flow
- **evolution** (PRODUCER): data is passed from producer to consumer
- **gateway** (PRODUCER): None
- **infrastructure** (PRODUCER): data
- **integrations** (PRODUCER): ...
- **knowledge** (CONSUMER): None
- **mcp** (PRODUCER): None
- **models** (PRODUCER): infrastructure
- **mycelium** (PRODUCER): None
- **optimization** (PRODUCER): None
- **ouroboros** (PRODUCER): ...
- **patterns** (PRODUCER): ...
- **persistence** (PRODUCER): None
- **pipeline** (PRODUCER): data flow from input to output
- **policies** (PRODUCER): partial parse
- **protocols** (PRODUCER): None
- **real_envs** (PRODUCER): ...
- **registry** (PRODUCER): None
- **reporting** (PRODUCER): None
- **resilience** (PRODUCER): ...
- **rewards** (PRODUCER): None
- **rl** (PRODUCER): ...
- **sandboxing** (PRODUCER): containerized/isolated execution environments for untrusted code.
- **scripts** (PRODUCER): null
- **security** (PRODUCER): GuardrailPipeline
- **services** (PRODUCER): services
- **skillopt** (PRODUCER): None
- **skills** (PRODUCER): ...
- **storage** (CONSUMER): None
- **substrate** (PRODUCER): null
- **tools** (PRODUCER): None
- **traceability** (PRODUCER): None
- **validation** (PRODUCER): None
- **vanguard** (PRODUCER): None
- **vibe** (PRODUCER): ...
- **wiring** (PRODUCER): data flow from producer to consumer
- **worldviews** (PRODUCER): ...
