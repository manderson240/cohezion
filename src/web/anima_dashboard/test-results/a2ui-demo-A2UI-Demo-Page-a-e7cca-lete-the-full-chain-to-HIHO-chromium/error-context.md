# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - heading "A2UI Demo — Genesis Cosmogony" [level=1] [ref=e3]
    - paragraph [ref=e4]: Declarative rendering via A2UI component catalog. Agent-inspectable state below.
    - generic [ref=e5]: "Catalog validation: PASSED | Components: 8 | Scenes: 5"
    - generic [ref=e7]:
      - button "Click the void to begin the cosmogony" [ref=e8] [cursor=pointer]
      - generic [ref=e10]: “In the beginning, there was nothing. Not even nothing.”
    - generic [ref=e11]:
      - generic [ref=e12]:
        - heading "Inspection State" [level=2] [ref=e13]
        - generic [ref=e14]: "{ \"experienceId\": \"genesis-cosmogony\", \"currentScene\": \"void\", \"activeComponents\": [ { \"id\": \"void-sphere\", \"component\": \"cohezion-void-sphere\", \"props\": { \"scale\": 0.055, \"dustCount\": 100, \"showClickPrompt\": true } }, { \"id\": \"void-narration\", \"component\": \"cohezion-narration\", \"props\": { \"text\": \"In the beginning, there was nothing. Not even nothing.\", \"style\": \"cinematic\", \"ttsEnabled\": true } }, { \"id\": \"void-sound\", \"component\": \"cohezion-sound-engine\", \"props\": { \"phase\": \"void-drone\", \"muted\": true } } ], \"dataModel\": { \"temperature\": 200, \"symmetry\": \"void\", \"stage\": -1, \"hasInteracted\": false, \"animElapsed\": 0, \"coherence\": 0, \"orderParameter\": 0 }, \"elapsed\": 0.01, \"catalogValid\": true }"
      - generic [ref=e15]:
        - heading "Action Log" [level=2] [ref=e16]
        - paragraph [ref=e17]: No actions yet. Click the void to begin.
    - group [ref=e18]:
      - generic "Full Catalog JSON" [ref=e19] [cursor=pointer]
  - button "Open Next.js Dev Tools" [ref=e25] [cursor=pointer]:
    - img [ref=e26]
  - alert [ref=e29]
```