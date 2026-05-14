#!/usr/bin/env bash
set -euo pipefail
# Autoresearch: Nemotron accuracy improvement
# Measures overall accuracy and equations accuracy (primary metric = equations_accuracy)
cd "$(dirname "$0")"

WINNERS=$(grep -c '"winner".*[Tt]rue\|[Tt]rue.*"winner"' autoresearch.jsonl 2>/dev/null || echo 0)
TOTAL=$(wc -l < autoresearch.jsonl 2>/dev/null || echo 0)
echo "METRIC winners=$WINNERS / $TOTAL total"

# Extract equations_accuracy and overall accuracy from the most recent winner
python3 - <<'EOF'
import json
try:
    lines = open('autoresearch.jsonl').readlines()
    winners = [l for l in lines if '"winner":true' in l or '"winner": true' in l or '"winner":True' in l or '"winner": True' in l]
    if winners:
        d = json.loads(winners[-1])
        m = d.get('metrics', d)
        eq = m.get('equations_accuracy', m.get('eq_accuracy', m.get('uc_after', '?')))
        ov = m.get('overall_accuracy', m.get('overall_after', '?'))
        print(f"METRIC last_winner_equations_accuracy={eq}")
        print(f"METRIC last_winner_overall_accuracy={ov}")
    else:
        print("METRIC last_winner_equations_accuracy=no_winners_yet")
    # Show last experiment regardless
    all_lines = [l.strip() for l in lines if l.strip()]
    if all_lines:
        d = json.loads(all_lines[-1])
        name = d.get('experiment_id', d.get('name', '?'))
        win = 'WIN' if (d.get('winner') is True or str(d.get('winner','')).lower() == 'true') else 'FAIL'
        print(f"METRIC last_experiment={name} → {win}")
except Exception as e:
    print(f"METRIC error={e}")
EOF
