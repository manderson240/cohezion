# Auto-Improving Code Review Agent — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTO-IMPROVING CODE REVIEW AGENT                     │
│                     Compound Engineering Workflow                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  REQUEST → Review code: "Data processing function"                      │
│            code: "def process_data(data):..."                           │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌──────────┐     ┌──────────┐
│SKILL #1  │  │SKILL #2  │     │SKILL #4  │
│Compound  │  │HIHO      │     │Model     │
│Engineer- │  │Stability │     │Routing   │
│ing       │  │          │     │          │
└────┬─────┘  └────┬─────┘     └────┬─────┘
     │              │               │
     ▼              ▼               ▼
┌──────────┐  ┌──────────┐     ┌──────────┐
│Alignment │  │Coherence │     │Task      │
│Gate      │  │Check     │     │Classify  │
│          │  │(0.60✓)   │     │→ code    │
│coherence │  │          │     │          │
│= 0.60    │  │regime:   │     │Select:   │
│proceed=✓ │  │HIHO-     │     │qwen3.5   │
└────┬─────┘  │stable    │     │32b       │
     │        └──────────┘     └────┬─────┘
     │                                │
     └────────────┬───────────────────┘
                  │
                  ▼
         ┌──────────────┐
         │ EXECUTE      │
         │ Review Code  │
         │ (Simulated)  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │SKILL #3      │
         │FLUME         │
         │              │
         │• Encode exp  │──→ Experience Cache (256D vectors)
         │• Find similar│     └── 1 similar experience found
         │              │
         └──────────────┘
                │
                ▼
         ┌──────────────┐
         │SKILL #5      │
         │Retrospective │
         │              │
         │• Analyze exe │
         │• Calc comp   │──→ Learning extracted (score: 0.707)
         │  score       │    └── Stored in session.learnings
         │• Suggest ref │
         └──────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  OUTPUT                                                                 │
│  ✓ Review Complete                                                      │
│  ✓ Coherence: 0.60 (HIHO-stable)                                        │
│  ✓ Compound Score: 0.707                                                │
│  ✓ Similar experiences: 1                                               │
│  ✓ Learning extracted                                                     │
└─────────────────────────────────────────────────────────────────────────┘


## Session Retrospective

┌─────────────────────────────────────────────────────────────────────────┐
│                    SESSION RETROSPECTIVE                                │
│                    Session: a81c648105cbc08d                            │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Total Execs   │  │  Success Rate  │  │ Avg Coherence  │
│       2        │  │    100.0%      │  │     0.60       │
└────────────────┘  └────────────────┘  └────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ HIHO Stable    │  │  Learnings     │  │ Skill Refine   │
│    100.0%      │  │      2         │  │       0        │
│ (All in HIHO)  │  │                │  │ (Need 3+)      │
└────────────────┘  └────────────────┘  └────────────────┘


## Skill Interactions (Sequence Diagram)

User                    CompoundEngine      HIHOMonitor       FLUME           ModelRouter     Retrospective
 │                            │                  │               │                  │                │
 │───review_code()───────────>│                  │               │                  │                │
 │                            │                  │               │                  │                │
 │                            │───check_align()─>│               │                  │                │
 │                            │<──align 0.60────│               │                  │                │
 │                            │                  │               │                  │                │
 │                            │───────────────────────────────────────────────────────>select_model()   │
 │                            │<────────────────────────────────────────qwen3.5:32b───│                │
 │                            │                  │               │                  │                │
 │                            │───execute_task()───────────────────────────────────────────────────────>
 │                            │<──result─────────────────────────────────────────────────────────────
 │                            │                  │               │                  │                │
 │                            │────────────────>HIHO check     │                  │                │
 │                            │<────────0.60 regime─────────────│               │                │
 │                            │                  │               │                  │                │
 │                            │─────────────────────────────────>cache_exp()────────────────────────>
 │                            │                  │<──z-vector───│                  │                │
 │                            │<──────────────────similar exp found────────────────────────────────────
 │                            │                  │               │                  │                │
 │                            │───────────────────────────────────────────────────────────────────────>
 │                            │<───────────────────────────────────────────────────analysis (0.707)───
 │                            │                  │               │                  │                │
 │<───result (comp 0.707)─────────────────────────────────────────────────────────────────────────────


## Data Flow

1. **Input** → Code snippet + context
              │
              ▼
2. **Alignment Gate** (Compound Engineering)
   - Check coherence requirement (>= 0.5)
   - Decompose if needed
   - Blocked #2: "Something with variables" (coherence 0.30)
              │
              ▼
3. **Model Selection** (Model Routing)
   - Classify task (code, analyze, fast, embed)
   - Select optimal Ollama model
   - Fallback chain if unavailable
              │
              ▼
4. **Execute** → Simulated code review
              │
              ▼
5. **Experience Encoding** (FLUME)
   - Encode task → 256D vector
   - Cache result
   - Find similar past experiences
              │
              ▼
6. **HIHO Monitoring**
   - Measure execution coherence
   - Diagnose regime (sub-HIHO / HIHO-stable / super-HIHO)
   - Apply damping if over-coherent (> 0.7)
              │
              ▼
7. **Retrospection**
   - Quadrature assessment (4 perspectives)
   - Calculate compound score
   - Extract learnings if warranted (3+ = refine skill)
              │
              ▼
8. **Output** → Review results + learnings


## Key Results

| Metric | Value |
|--------|-------|
| Total Reviews | 3 |
| Blocked (low alignment) | 1 (33%) |
| Successful | 2 |
| Success Rate | 100% (of proceeded) |
| Avg Coherence | 0.60 (optimal) |
| HIHO Stable Time | 100% |
| Learnings Extracted | 2 |
| Skill Refinements | 0 (need 3+ learnings) |


## Blocked Request Analysis

Request: "Something with variables" (code: "x = 5\ny = 10")

Problem detected by Alignment Gate:
- ❌ Vague target
- ❌ No specific file mentioned
- ❌ Coherence: 0.30 (< 0.50 threshold)

Action: Blocked before wasting tokens


## Successful Request Analysis

Request: "Data processing function"

✓ Clear action ("processing")
✓ Specific target (function)
✓ Coherence: 0.60 (HIHO-stable)
✓ Model: qwen3.5:32b (code-appropriate)
✓ Learning extracted: compound score 0.707

## What Makes It "Auto-Improving"

Each execution feeds into the compound loop:

```
Execute #1 → Learning extracted
      │
      ▼
Execute #2 → FLUME finds similar experience from #1
      │
      ▼
Execute #3 → Retrospection sees pattern
      │
      ▼
Skill Refinement (when 3+ learnings accumulated)
      │
      ▼
Future executions benefit from refined skill
```

This is the **Compound Loop** in action:
Every execution makes future executions easier/better.


## Skills Exercised

┌─────────────────────────────────────────────────────────────────────────┐
│  ✓ cohezion-compound-engineering                                        │
│    → Alignment gates, session management, execution orchestration      │
│                                                                         │
│  ✓ cohezion-hiho-stability                                              │
│    → Coherence monitoring (0.6 = optimal HIHO), regime diagnosis     │
│                                                                         │
│  ✓ cohezion-flume                                                       │
│    → Experience encoding to 256D, similarity search (cosine)          │
│                                                                         │
│  ✓ cohezion-model-routing                                               │
│    → Task classification (code/analyze/fast), model selection        │
│                                                                         │
│  ✓ cohezion-retrospective                                               │
│    → Quadrature assessment, compound scoring, skill refinement         │
└─────────────────────────────────────────────────────────────────────────┘
