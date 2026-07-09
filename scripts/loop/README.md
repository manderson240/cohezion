# Persistent self-improvement loop (systemd user timer)

Makes the `/loop` self-improvement loop survive session-close **and** reboot, by running ONE
guardrailed tick per timer fire via headless `claude --print`. Fleet-dependent, so it runs locally
(not in the cloud). **Inert until you enable it** — and even then it cannot commit until you opt into
full autonomy (guardrail 5 below).

## Files
- `loop_tick.sh` — the guardrailed single-tick runner (kill-switch, branch-guard, daily cap, flock, log).
- `build_loop_prompt.txt` — the `/loop` prompt (headless one-shot: ONE item, no ScheduleWakeup).
- `cohezion-build-loop.service` / `.timer` — the systemd user units.

## The guardrails (charter-aligned)
1. **Kill switch** — `touch .loop-off` in the repo stops every future tick immediately. `rm` to resume.
2. **Branch guard** — refuses `main`/`develop`/`master`; only `feat/ fix/ kaggle/ isolated/ spec/`.
3. **Daily budget cap** — `COHEZION_LOOP_MAX_TICKS` (default 40/day). Each tick is a full headless
   **Opus** session = real $. 40 ticks/day is the ceiling; lower it or raise the cadence interval to spend less.
4. **Flock** — never two overlapping ticks.
5. **Permission mode** — DEFAULT `acceptEdits` means Bash is blocked, so a tick **cannot commit**
   (effectively a dry run / safe). Full autonomy (self-committing, spends $) requires you to set
   `COHEZION_LOOP_PERMISSION_MODE=bypassPermissions` in the `.service` — the deliberate trigger.
6. **Observability** — `tail -f .loop-state/loop.log`.

## Cost reality (read before enabling)
Each tick = one fresh headless Opus session (full context + one backlog item). At the default
30-min cadence that is ~48 fires/day, capped to 40 actual ticks by the budget guard. Estimate the
$/tick from your own usage and multiply — this is **not** free. Start with a SMALL cap and a LONG
interval, watch the log + your usage, then adjust.

## Enable (your deliberate action — this is when it starts spending)
```bash
# 1. install the units
ln -sf "$PWD/scripts/loop/cohezion-build-loop.service" ~/.config/systemd/user/
ln -sf "$PWD/scripts/loop/cohezion-build-loop.timer"   ~/.config/systemd/user/

# 2. (optional) grant full autonomy — ONLY if you want it to actually commit + spend:
#    edit ~/.config/systemd/user/cohezion-build-loop.service and uncomment the
#    Environment=COHEZION_LOOP_PERMISSION_MODE=bypassPermissions line.

# 3. start the timer (survives reboot once lingering is on)
systemctl --user daemon-reload
systemctl --user enable --now cohezion-build-loop.timer
loginctl enable-linger "$USER"     # so the timer runs even when you are logged out

# verify
systemctl --user list-timers cohezion-build-loop.timer
```

## Pause / stop
```bash
touch .loop-off                                   # fastest: stop ticks, keep the timer
systemctl --user stop  cohezion-build-loop.timer  # stop the cadence
systemctl --user disable cohezion-build-loop.timer# remove from boot
```

## Auto-stop when there's nothing left to do
The prompt instructs the tick to check `frontier_is_human_gated_from_state()` (item 40): when the
backlog has no auto-actionable TODO and every frontier gap is human-gated, it writes
`.loop-state/frontier-exhausted` and makes no changes — so you are not paying for a loop that can
only spin. (You can wire that file to `.loop-off` via a one-line cron if you want a hard stop.)
