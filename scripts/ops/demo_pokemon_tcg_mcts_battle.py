#!/usr/bin/env python3
"""Live Pokemon TCG MCTS Battle Simulation Harness."""

import time
from cohezion.competitions.pokemon_tcg.tcg_simulator import PokemonTCGSimulator, BattleState

def main():
    print("\n" + "=" * 95)
    print("⚔️ POKEMON TCG AI BATTLE CHALLENGE: MCTS STRATEGY HARNESS")
    print("=" * 95)

    sim = PokemonTCGSimulator("data/kaggle/pokemon_tcg/EN_Card_Data.csv")
    print(f"• Loaded Official Card Database: {len(sim.cards)} competition cards parsed.")

    state = BattleState(player_active_hp=120, opponent_active_hp=120)
    print(f"• Initial State: Player HP={state.player_active_hp}, Opponent HP={state.opponent_active_hp}")

    # Run Battle Loop with MCTS decision-making
    turn = 1
    t0 = time.perf_counter()
    while not state.game_over and turn <= 10:
        action = sim.monte_carlo_tree_search(state, num_simulations=200)
        state = sim.step(state, action)
        print(f"  [Turn {turn}] Action: `{action:<15}` | Player HP: {state.player_active_hp:3d} | Opponent HP: {state.opponent_active_hp:3d}")
        turn += 1

    dt_ms = (time.perf_counter() - t0) * 1000.0
    print("\n" + "=" * 95)
    print(f"🎉 BATTLE COMPLETE in {dt_ms:.2f} ms | Winner: {state.winner.upper() if state.winner else 'DRAW'}")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    main()
