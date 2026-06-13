#!/usr/bin/env bash
set -euo pipefail
# Autoresearch: FLUME VAE quality optimization
# Primary metric: recon_loss (lower is better)
cd "$(dirname "$0")"

WINNERS=$(grep -c '"winner": true\|"winner":true\|"winner":True\|"winner": True' autoresearch.jsonl 2>/dev/null || echo 0)
TOTAL=$(wc -l < autoresearch.jsonl 2>/dev/null || echo 0)
echo "METRIC winners=$WINNERS / $TOTAL total"

python3 - <<'EOF'
import json
try:
    lines = open('autoresearch.jsonl').readlines()
    winners = [l for l in lines if '"winner":true' in l or '"winner": true' in l or '"winner":True' in l or '"winner": True' in l]
    if winners:
        d = json.loads(winners[-1])
        m = d.get('metrics', d)
        recon = m.get('recon_loss', '?')
        kl = m.get('kl_loss', '?')
        print(f"METRIC last_winner_recon_loss={recon}")
        print(f"METRIC last_winner_kl_loss={kl}")
    else:
        print("METRIC last_winner_recon_loss=no_winners_yet")
    all_lines = [l.strip() for l in lines if l.strip()]
    if all_lines:
        d = json.loads(all_lines[-1])
        name = d.get('experiment_id', d.get('name', '?'))
        win = 'WIN' if (d.get('winner') is True or str(d.get('winner','')).lower() == 'true') else 'FAIL'
        print(f"METRIC last_experiment={name} -> {win}")
except Exception as e:
    print(f"METRIC error={e}")
EOF
