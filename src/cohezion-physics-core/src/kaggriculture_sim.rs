//! High-performance parallel simulation engine for Kaggriculture.
//! Uses Rayon to simulate thousands of 720-step market/farming trajectories across 32 Zen 5 threads.

use rayon::prelude::*;

#[derive(Clone, Debug)]
pub struct FarmState {
    pub coins: f64,
    pub carrots: u32,
    pub melons: u32,
    pub tomatoes: u32,
    pub milk: u32,
    pub cows: u32,
    pub fertilizer: u32,
}

#[derive(Clone, Debug)]
pub struct PolicyParams {
    pub slow_crop_freeze_day: u32,
    pub dutch_auction_day: u32,
    pub liquidation_day: u32,
    pub fertilizer_liquidation_day: u32,
    pub min_spot_price_sell: f64,
}

impl Default for PolicyParams {
    fn default() -> Self {
        Self {
            slow_crop_freeze_day: 27,
            dutch_auction_day: 27,
            liquidation_day: 28,
            fertilizer_liquidation_day: 29,
            min_spot_price_sell: 5.0,
        }
    }
}

/// Simulates a single 720-turn episode of Kaggriculture under stochastic market prices.
pub fn simulate_single_episode(seed: u64, params: &PolicyParams) -> f64 {
    let mut state = FarmState {
        coins: 100.0,
        carrots: 0,
        melons: 0,
        tomatoes: 0,
        milk: 0,
        cows: 4,
        fertilizer: 2,
    };

    // SplitMix64 PRNG state
    let mut rng = seed ^ 0x5555555555555555;
    let mut next_f64 = || -> f64 {
        rng = rng.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = rng;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        (z ^ (z >> 31)) as f64 / u64::MAX as f64
    };

    // Queue of maturing crops: (maturity_turn, crop_type, quantity)
    // crop_type: 0 = carrot (24 turns), 1 = tomato (120 turns), 2 = melon (144 turns)
    let mut maturing: Vec<(u32, u8, u32)> = Vec::with_capacity(64);

    for turn in 0..720 {
        let day = turn / 24;

        // 1. Milk production from cows (every 4 turns = 6 hours)
        if turn % 4 == 0 {
            state.milk += state.cows * 2;
        }

        // 2. Harvest maturing crops
        let mut idx = 0;
        while idx < maturing.len() {
            if maturing[idx].0 <= turn {
                let (_, crop_type, qty) = maturing.swap_remove(idx);
                match crop_type {
                    0 => state.carrots += qty,
                    1 => state.tomatoes += qty,
                    2 => state.melons += qty,
                    _ => {}
                }
            } else {
                idx += 1;
            }
        }

        // 3. Stochastic Market Prices (random walk with mean reversion)
        let milk_price = 5.0 + 3.0 * (next_f64() - 0.45);
        let melon_price = 12.0 + 5.0 * (next_f64() - 0.45);
        let tomato_price = 8.0 + 3.5 * (next_f64() - 0.45);
        let carrot_price = 3.0 + 1.5 * (next_f64() - 0.45);
        let fert_price = 4.0 + 1.0 * (next_f64() - 0.5);

        // 4. Planting strategy
        if day < params.slow_crop_freeze_day {
            // Early game: plant high-yield slow crops (melons & tomatoes)
            if state.coins >= 30.0 && state.melons < 10 {
                state.coins -= 20.0;
                maturing.push((turn + 144, 2, 8)); // Melon
            }
            if state.coins >= 25.0 && state.tomatoes < 10 {
                state.coins -= 15.0;
                maturing.push((turn + 120, 1, 6)); // Tomato
            }
        } else if day <= 28 {
            // Endgame: only plant fast carrots (24 turns)
            if state.coins >= 10.0 {
                state.coins -= 10.0;
                maturing.push((turn + 24, 0, 10)); // Carrot
            }
        }

        // 5. Market sales & Dutch auction liquidation
        if day == params.dutch_auction_day && turn % 24 == 0 {
            // Phase 1 Dutch auction: sell half of peak inventory
            if milk_price >= params.min_spot_price_sell && state.milk > 0 {
                let to_sell = (state.milk / 2).max(1);
                state.coins += to_sell as f64 * milk_price;
                state.milk -= to_sell;
            }
            if melon_price >= 12.0 && state.melons > 0 {
                let to_sell = (state.melons / 2).max(1);
                state.coins += to_sell as f64 * melon_price;
                state.melons -= to_sell;
            }
        } else if day >= params.liquidation_day {
            // Phase 2: Complete commodity liquidation before turn 720
            if state.milk > 0 {
                state.coins += state.milk as f64 * milk_price;
                state.milk = 0;
            }
            if state.melons > 0 {
                state.coins += state.melons as f64 * melon_price;
                state.melons = 0;
            }
            if state.tomatoes > 0 {
                state.coins += state.tomatoes as f64 * tomato_price;
                state.tomatoes = 0;
            }
            if state.carrots > 0 {
                state.coins += state.carrots as f64 * carrot_price;
                state.carrots = 0;
            }
        }

        // 6. Fertilizer liquidation on Day 29
        if day >= params.fertilizer_liquidation_day && state.fertilizer > 0 {
            state.coins += state.fertilizer as f64 * fert_price;
            state.fertilizer = 0;
        }
    }

    state.coins
}

/// Runs N parallel simulations using Rayon across all available CPU cores.
/// Returns (mean_coins, min_coins, max_coins, win_rate_vs_benchmark_2000).
pub fn simulate_parallel_rollouts(
    num_sims: usize,
    base_seed: u64,
    params: &PolicyParams,
) -> (f64, f64, f64, f64) {
    let scores: Vec<f64> = (0..num_sims)
        .into_par_iter()
        .map(|i| {
            let seed = base_seed.wrapping_add(i as u64).wrapping_mul(0x9E3779B97F4A7C15);
            simulate_single_episode(seed, params)
        })
        .collect();

    let count = scores.len() as f64;
    let sum: f64 = scores.iter().sum();
    let mean = sum / count;

    let min = scores.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    let wins = scores.iter().filter(|&&s| s >= 2000.0).count() as f64;
    let win_rate = wins / count;

    (mean, min, max, win_rate)
}

#[derive(Clone, Debug)]
pub struct AdversarialMarketParams {
    pub slow_crop_freeze_day: u32,
    pub dutch_auction_day: u32,
    pub liquidation_day: u32,
    pub fertilizer_liquidation_day: u32,
    pub min_spot_price_sell: f64,
    pub predatory_dump_day: u32,
    pub dump_crash_factor: f64,
}

impl Default for AdversarialMarketParams {
    fn default() -> Self {
        Self {
            slow_crop_freeze_day: 25,
            dutch_auction_day: 25,
            liquidation_day: 27,
            fertilizer_liquidation_day: 28,
            min_spot_price_sell: 5.0,
            predatory_dump_day: 26,
            dump_crash_factor: 0.35, // Market drops 65% due to competitor dump
        }
    }
}

/// Simulates a single episode with predatory market competition.
pub fn simulate_adversarial_episode(seed: u64, params: &AdversarialMarketParams) -> f64 {
    let mut state = FarmState {
        coins: 100.0,
        carrots: 0,
        melons: 0,
        tomatoes: 0,
        milk: 0,
        cows: 4,
        fertilizer: 2,
    };

    let mut rng = seed ^ 0x5555555555555555;
    let mut next_f64 = || -> f64 {
        rng = rng.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = rng;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        (z ^ (z >> 31)) as f64 / u64::MAX as f64
    };

    let mut maturing: Vec<(u32, u8, u32)> = Vec::with_capacity(64);

    for turn in 0..720 {
        let day = turn / 24;

        if turn % 4 == 0 {
            state.milk += state.cows * 2;
        }

        let mut idx = 0;
        while idx < maturing.len() {
            if maturing[idx].0 <= turn {
                let (_, crop_type, qty) = maturing.swap_remove(idx);
                match crop_type {
                    0 => state.carrots += qty,
                    1 => state.tomatoes += qty,
                    2 => state.melons += qty,
                    _ => {}
                }
            } else {
                idx += 1;
            }
        }

        // Market prices with potential predatory crash
        let market_multiplier = if day >= params.predatory_dump_day {
            params.dump_crash_factor
        } else {
            1.0
        };

        let milk_price = (5.0 + 3.0 * (next_f64() - 0.45)) * market_multiplier;
        let melon_price = (12.0 + 5.0 * (next_f64() - 0.45)) * market_multiplier;
        let tomato_price = (8.0 + 3.5 * (next_f64() - 0.45)) * market_multiplier;
        let carrot_price = (3.0 + 1.5 * (next_f64() - 0.45)) * market_multiplier;
        let fert_price = (4.0 + 1.0 * (next_f64() - 0.5)) * market_multiplier;

        // Planting
        if day < params.slow_crop_freeze_day {
            if state.coins >= 30.0 && state.melons < 10 {
                state.coins -= 20.0;
                maturing.push((turn + 144, 2, 8));
            }
            if state.coins >= 25.0 && state.tomatoes < 10 {
                state.coins -= 15.0;
                maturing.push((turn + 120, 1, 6));
            }
        } else if day <= 28 {
            if state.coins >= 10.0 {
                state.coins -= 10.0;
                maturing.push((turn + 24, 0, 10));
            }
        }

        // Dutch auction
        if day == params.dutch_auction_day && turn % 24 == 0 {
            if milk_price >= params.min_spot_price_sell && state.milk > 0 {
                let to_sell = (state.milk / 2).max(1);
                state.coins += to_sell as f64 * milk_price;
                state.milk -= to_sell;
            }
            if melon_price >= (10.0 * market_multiplier) && state.melons > 0 {
                let to_sell = (state.melons / 2).max(1);
                state.coins += to_sell as f64 * melon_price;
                state.melons -= to_sell;
            }
        } else if day >= params.liquidation_day {
            if state.milk > 0 {
                state.coins += state.milk as f64 * milk_price;
                state.milk = 0;
            }
            if state.melons > 0 {
                state.coins += state.melons as f64 * melon_price;
                state.melons = 0;
            }
            if state.tomatoes > 0 {
                state.coins += state.tomatoes as f64 * tomato_price;
                state.tomatoes = 0;
            }
            if state.carrots > 0 {
                state.coins += state.carrots as f64 * carrot_price;
                state.carrots = 0;
            }
        }

        if day >= params.fertilizer_liquidation_day && state.fertilizer > 0 {
            state.coins += state.fertilizer as f64 * fert_price;
            state.fertilizer = 0;
        }
    }

    state.coins
}

/// Runs parallel adversarial market simulations across all CPU threads.
pub fn simulate_adversarial_rollouts(
    num_sims: usize,
    base_seed: u64,
    params: &AdversarialMarketParams,
) -> (f64, f64, f64, f64) {
    let scores: Vec<f64> = (0..num_sims)
        .into_par_iter()
        .map(|i| {
            let seed = base_seed.wrapping_add(i as u64).wrapping_mul(0x9E3779B97F4A7C15);
            simulate_adversarial_episode(seed, params)
        })
        .collect();

    let count = scores.len() as f64;
    let sum: f64 = scores.iter().sum();
    let mean = sum / count;

    let min = scores.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    let wins = scores.iter().filter(|&&s| s >= 2000.0).count() as f64;
    let win_rate = wins / count;

    (mean, min, max, win_rate)
}

