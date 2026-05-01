"""Autoresearch Funding Optimizer — Long-Horizon Funding Discovery Loop

Uses the Cohezion autoresearch K-Search tree + UCB1 bandit to discover,
evaluate, and prioritize funding opportunities over extended time horizons.

Targets map to funding sources (VCs, grants, accelerators, competitions).
Metrics: fit_score (0–1), estimated_amount ($K), deadline_weeks_to_apply.
Direction: maximize fit_score.

Usage:
    python scripts/autoresearch_funding.py --target all --iterations 30 --budget-hours 2
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)


@dataclass
class FundingSource:
    name: str
    category: str
    estimated_amount_k: int
    fit_dimensions: list[str]
    deadline_weeks: int
    application_effort_hours: int
    success_rate_estimate: float
    open_status: bool = True
    notes: str = ""
    url: str = ""
    verified_date: str = ""


# CRITERIA: non-dilutive preferred, IP retained, aligned with plasma physics / MHD /
# cosmogony / AGI / quantum / ecosystem services / biodiversity
_DEFAULT_FUNDING_SOURCES: list[FundingSource] = [
    # --- KAGGLE COMPETITIONS (Solo eligible, IP retained) ---
    FundingSource("ARC Prize 2026 - Interactive", "competition", 850,
        ["agi", "reasoning", "code"], 27, 200, 0.05, True,
        "670 teams. ENTERED. Solo eligible. Deadline: 2026-11-02.",
        "https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3",
        "2026-04-28"),
    FundingSource("ARC Prize 2026 - Static", "competition", 700,
        ["agi", "pattern-recognition", "code"], 27, 200, 0.05, True,
        "503 teams. ENTERED. Solo eligible. Deadline: 2026-11-02.",
        "https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2",
        "2026-04-28"),
    FundingSource("ARC Prize 2026 - Paper", "competition", 450,
        ["agi", "research-paper", "cognitive-science"], 28, 100, 0.10, True,
        "32 teams. ENTERED. Solo eligible. Deadline: 2026-11-09.",
        "https://www.kaggle.com/competitions/arc-prize-2026-paper-track",
        "2026-04-28"),
    FundingSource("Gemma 4 Good Hackathon", "competition", 200,
        ["agi", "social-impact", "gemma", "demo"], 3, 80, 0.08, True,
        "147 teams. ENTERED. Solo eligible. Deadline: 2026-05-18.",
        "https://www.kaggle.com/competitions/gemma-4-good-hackathon",
        "2026-04-28"),
    FundingSource("NVIDIA Nemotron Reasoning", "competition", 106,
        ["reasoning", "nvidia", "code"], 7, 120, 0.04, True,
        "2491 teams. ENTERED. Solo eligible. Deadline: 2026-06-15.",
        "https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge",
        "2026-04-28"),

    # --- XPRIZE / MAJOR PRIZES (Solo eligible, IP retained) ---
    FundingSource("AGI Prize (Future of Life)", "competition", 5000,
        ["agi", "safety", "open-ended"], 52, 300, 0.01, True,
        "$5M grand prize. Solo eligible. Open application.",
        "https://futureoflife.org/agi-prize", "2026-04-28"),
    FundingSource("XPRIZE Quantum Applications", "competition", 5000,
        ["quantum", "demonstration", "google-quantum-ai"], 52, 80, 0.04, True,
        "$5M. Quantum computing demos. 3-year comp. Solo eligible.",
        "https://www.xprize.org/prizes/quantum-applications", "2026-04-28"),
    FundingSource("XPRIZE Water Scarcity", "competition", 119000,
        ["water", "ecosystem", "aridity", "biodiversity"], 40, 200, 0.01, True,
        "$119M. Clean water access. MBZ Water Initiative. Solo eligible.",
        "https://www.xprize.org/prizes/water-scarcity", "2026-04-28"),
    FundingSource("XPRIZE Wildfire", "competition", 11000,
        ["climate", "fire", "forest", "ecosystem"], 36, 100, 0.03, True,
        "$11M. Autonomous wildfire detection. PG&E + Moore Fdn. Solo eligible.",
        "https://www.xprize.org/prizes/wildfire", "2026-04-28"),
    FundingSource("XPRIZE Rainforest", "competition", 10000,
        ["biodiversity", "rainforest", "conservation", "inventory"], 40, 120, 0.02, True,
        "$10M. Rainforest biodiversity inventory. Solo eligible.",
        "https://www.xprize.org/prizes/rainforest", "2026-04-28"),

    # --- GOVERNMENT GRANTS (Require institutional affiliation: LLC, university, nonprofit) ---
    FundingSource("NSF SBIR Phase I", "grant_gov", 300,
        ["research", "commercialization", "small-business"], 16, 40, 0.15, True,
        "$300K non-dilutive. REQUIRES small business / LLC. 6-month cycle.",
        "https://www.sbir.gov", "2026-04-28"),
    FundingSource("NSF SBIR Phase II", "grant_gov", 1000,
        ["research", "traction", "small-business"], 40, 60, 0.10, True,
        "$1M non-dilutive. REQUIRES Phase I completion + LLC.",
        "https://www.sbir.gov", "2026-04-28"),
    FundingSource("DOE ASCR", "grant_gov", 500,
        ["plasma-physics", "mhd", "cosmogony", "simulation", "computing"], 20, 50, 0.12, True,
        "Advanced scientific computing. REQUIRES university / lab affiliation.",
        "https://science.osti.gov/ascr", "2026-04-28"),
    FundingSource("DOE FES - Fusion Energy", "grant_gov", 1000,
        ["plasma-physics", "mhd", "fusion", "simulation"], 24, 60, 0.10, True,
        "Plasma confinement, MHD instability. REQUIRES institution.",
        "https://science.osti.gov/fes", "2026-04-28"),
    FundingSource("NSF OCE - Oceanography", "grant_gov", 500,
        ["mhd", "fluid-dynamics", "geodynamo", "ecosystem"], 20, 50, 0.10, True,
        "Ocean circulation / MHD dynamo. REQUIRES university.",
        "https://www.nsf.gov/div/index.jsp?div=OCE", "2026-04-28"),
    FundingSource("NSF AST - Astronomy", "grant_gov", 600,
        ["cosmogony", "simulation", "gravity", "observational-cosmos"], 20, 50, 0.08, True,
        "Cosmological simulation. REQUIRES university / observatory.",
        "https://www.nsf.gov/div/index.jsp?div=AST", "2026-04-28"),
    FundingSource("NSF PHY - Physics", "grant_gov", 500,
        ["quantum", "mhd", "plasma", "cosmogony", "foundations"], 20, 50, 0.09, True,
        "Quantum foundations, plasma physics. REQUIRES institution.",
        "https://www.nsf.gov/div/index.jsp?div=PHY", "2026-04-28"),
    FundingSource("NOAA B-WET / Education", "grant_gov", 150,
        ["biodiversity", "ecosystem", "education", "ocean"], 12, 30, 0.15, True,
        "Bay/ocean watershed education. REQUIRES nonprofit / school.",
        "https://www.noaa.gov/education/grants", "2026-04-28"),
    FundingSource("USGS - Ecosystems", "grant_gov", 400,
        ["biodiversity", "ecosystem", "conservation", "modeling"], 18, 40, 0.11, True,
        "Species modeling, biodiversity prediction. REQUIRES institution.",
        "https://www.usgs.gov/programs/ecosystems", "2026-04-28"),
    FundingSource("NASA ROSES - Astrobiology", "grant_gov", 500,
        ["cosmogony", "origin-of-life", "extremophiles", "simulation"], 24, 50, 0.08, True,
        "Origin of life, planetary habitability. REQUIRES university.",
        "https://nspires.nasaprs.com", "2026-04-28"),
    FundingSource("NIH BRAIN Initiative", "grant_gov", 500,
        ["agi", "neuroscience", "cognitive-science", "bioelectric"], 20, 50, 0.09, True,
        "Brain circuit mapping, bioelectric computation. REQUIRES university / hospital.",
        "https://braininitiative.nih.gov", "2026-04-28"),

    # --- CORPORATE GRANTS (Mixed; solo case-by-case) ---
    FundingSource("Google AI for Social Good", "grant_corp", 250,
        ["agi", "social-impact", "open-source", "ecosystem"], 12, 20, 0.08, True,
        "Solo eligible case-by-case. Check terms per cycle.",
        "https://ai.google/social-good", "2026-04-28"),
    FundingSource("Meta AI Research Grant", "grant_corp", 300,
        ["agi", "open-source", "llm"], 14, 25, 0.07, True,
        "Solo eligible case-by-case. Check publication/IP terms.",
        "https://ai.meta.com/research", "2026-04-28"),

    # --- ACCELERATORS / CREDITS (Solo eligible, no IP claim) ---
    FundingSource("AWS Activate", "accelerator", 100,
        ["cloud", "infrastructure", "startup"], 4, 5, 0.30, True,
        "$100K AWS credits. Solo eligible. Non-dilutive. No IP claim.",
        "https://aws.amazon.com/activate", "2026-04-28"),
    FundingSource("NVIDIA Inception", "accelerator", 0,
        ["gpu", "ai", "startup"], 2, 5, 0.40, True,
        "GPU credits + go-to-market. Solo eligible. No equity. No IP claim.",
        "https://www.nvidia.com/en-us/startups/inception", "2026-04-28"),

    # --- EQUITY-BASED (Require company, low priority) ---
    FundingSource("Y Combinator S26", "accelerator", 500,
        ["idea", "team", "traction"], 4, 20, 0.02, True,
        "TAKES EQUITY ~7%. Apply by May 4 2026.",
        "https://www.ycombinator.com/apply", "2026-04-28"),
    FundingSource("a16z SPEEDRUN", "vc_seed", 1000,
        ["demo", "traction", "team"], 6, 15, 0.01, True,
        "TAKES SIGNIFICANT EQUITY. High dilution.",
        "https://a16z.com", "2026-04-28"),
    FundingSource("Sequoia Arc", "vc_seed", 1000,
        ["idea", "team", "market"], 10, 20, 0.01, True,
        "TAKES EQUITY. Idea-stage. High dilution.",
        "https://www.sequoiacap.com/arc", "2026-04-28"),
    FundingSource("OpenAI Startup Fund", "vc_seed", 1000,
        ["product", "traction", "openai-api"], 8, 15, 0.02, True,
        "TAKES EQUITY. Prefers API users. High dilution.",
        "https://openai.com/fund", "2026-04-28"),
    FundingSource("Antler", "accelerator", 100,
        ["founder", "idea", "speed"], 6, 10, 0.04, True,
        "TAKES EQUITY. Monthly cohorts.",
        "https://www.antler.co", "2026-04-28"),
    FundingSource("Techstars AI", "accelerator", 120,
        ["idea", "team", "market"], 8, 15, 0.03, True,
        "TAKES EQUITY ~6%. IP stays with startup.",
        "https://www.techstars.com/accelerators", "2026-04-28"),
    FundingSource("Nous Research Fellowships", "accelerator", 50,
        ["open-source", "agi", "community"], 12, 10, 0.05, True,
        "Open-source AI grants. Unverified status.",
        "https://nousresearch.com", "2026-04-28"),
]

FUNDING_TARGETS: dict[str, list[str]] = {
    "all": [s.name for s in _DEFAULT_FUNDING_SOURCES],
    "vc_seed": [s.name for s in _DEFAULT_FUNDING_SOURCES if s.category == "vc_seed"],
    "grants": [s.name for s in _DEFAULT_FUNDING_SOURCES if s.category.startswith("grant")],
    "accelerators": [s.name for s in _DEFAULT_FUNDING_SOURCES if s.category == "accelerator"],
    "competitions": [s.name for s in _DEFAULT_FUNDING_SOURCES if s.category == "competition"],
    "solo_eligible": [s.name for s in _DEFAULT_FUNDING_SOURCES
                       if "competition" in s.category or "xprize" in s.name.lower()
                       or s.name in ("Google AI for Social Good", "Meta AI Research Grant",
                                     "AWS Activate", "NVIDIA Inception")],
}

# K-Search tree persistence
KSEARCH_DIR = Path.home() / ".cohezion-research" / "ksearch" / "funding"
KSEARCH_DIR.mkdir(parents=True, exist_ok=True)


def _load_tree(target: str) -> dict:
    path = KSEARCH_DIR / f"{target}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    sources = FUNDING_TARGETS.get(target, [])
    return {
        "target": target,
        "total_trials": 0,
        "nodes": {name: {"hypothesis": name, "wins": 0, "trials": 0,
                         "fit_scores": [], "z_vector": []} for name in sources},
    }


def _save_tree(target: str, tree: dict) -> None:
    with open(KSEARCH_DIR / f"{target}.json", "w") as f:
        json.dump(tree, f, indent=2)


def _ucb1_select(tree: dict) -> str:
    nodes = tree["nodes"]
    total = tree["total_trials"]
    if total == 0:
        return random.choice(list(nodes.keys()))
    best_score, best_name = -1.0, list(nodes.keys())[0]
    for name, node in nodes.items():
        if node["trials"] == 0:
            return name
        mean = node["wins"] / node["trials"]
        exploration = 1.414 * math.sqrt(math.log(total) / node["trials"])
        score = mean + exploration
        if score > best_score:
            best_score, best_name = score, name
    return best_name


def _update_tree(tree: dict, source_name: str, fit_score: float, estimated_k: int) -> None:
    node = tree["nodes"][source_name]
    node["trials"] += 1
    node["fit_scores"].append(fit_score)
    node["z_vector"] = [fit_score, estimated_k / 1000.0]
    if fit_score >= 0.10:  # HIHO threshold for funding
        node["wins"] += 1
    tree["total_trials"] += 1


def _compute_fit(source: FundingSource) -> float:
    base = source.success_rate_estimate
    effort_penalty = min(0.02, source.application_effort_hours / 1000)
    deadline_penalty = min(0.05, 2.0 / max(source.deadline_weeks, 1))
    boost = 0.0
    if "research" in source.fit_dimensions:
        boost += 0.05
    if "open-source" in source.fit_dimensions:
        boost += 0.03
    if "agi" in source.fit_dimensions or "cosmogony" in source.fit_dimensions:
        boost += 0.05
    if "traction" in source.fit_dimensions:
        boost -= 0.03
    return max(0.05, min(1.0, base - effort_penalty - deadline_penalty + boost))


def _research_source(source: FundingSource) -> dict:
    fit = _compute_fit(source)
    ev = fit * source.estimated_amount_k * 1000
    return {
        "source": source.name,
        "fit_score": fit,
        "estimated_amount_k": source.estimated_amount_k,
        "expected_value": ev,
        "deadline_weeks": source.deadline_weeks,
        "effort_hours": source.application_effort_hours,
        "notes": source.notes,
        "url": source.url,
        "category": source.category,
        "verified_date": source.verified_date,
        "deadline_passed": source.deadline_weeks < 0,
    }


def _run_command(cmd_parts: list[str], timeout: int = 60) -> dict:
    env = os.environ.copy()
    src = str(Path(__file__).parent.parent / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=timeout, env=env)
        return {"success": result.returncode == 0, "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class FundingAutoresearchDriver:
    """Long-horizon autoresearch loop for funding discovery."""

    def __init__(self, target: str = "all", budget_hours: int = 4):
        if target not in FUNDING_TARGETS:
            raise ValueError(f"Unknown target '{target}'. Valid: {list(FUNDING_TARGETS)}")
        self.target = target
        self.budget_hours = budget_hours
        self.budget_seconds = budget_hours * 3600
        self.sources_by_name = {s.name: s for s in _DEFAULT_FUNDING_SOURCES}
        self.tree = _load_tree(target)
        self.results_log: list[dict] = []

    def run_loop(self, iterations: int = 10) -> list[dict]:
        start = time.perf_counter()
        for i in range(iterations):
            if time.perf_counter() - start > self.budget_seconds:
                logger.warning(f"Budget exhausted ({self.budget_hours}h). Stopping.")
                break
            source_name = _ucb1_select(self.tree)
            source = self.sources_by_name.get(source_name)
            if not source:
                logger.warning(f"Source not found: {source_name}")
                continue
            result = _research_source(source)
            self.results_log.append(result)
            _update_tree(self.tree, source_name, result["fit_score"], result["estimated_amount_k"])
            _save_tree(self.target, self.tree)
            logger.info(
                f"  ✓ Iteration {i+1}/{iterations}: {source_name} | "
                f"Fit={result['fit_score']:.2f} | EV=${result['expected_value']:,.0f} | "
                f"Deadline={result['deadline_weeks']}w"
            )
        return self.results_log

    def get_ranked(self) -> list[dict]:
        return sorted(self.results_log, key=lambda r: r["expected_value"], reverse=True)

    def generate_report(self) -> str:
        # Dedup by source name, keeping latest
        seen: dict[str, dict] = {}
        for r in self.results_log:
            seen[r["source"]] = r
        ranked = sorted(seen.values(), key=lambda r: r["expected_value"], reverse=True)
        active = [r for r in ranked if not r.get("deadline_passed")]
        solo = [r for r in active if r["source"] in FUNDING_TARGETS.get("solo_eligible", [])]
        inst = [r for r in active if r["source"] not in FUNDING_TARGETS.get("solo_eligible", [])]
        total_solo = sum(r["estimated_amount_k"] for r in solo)
        total_ev = sum(r["expected_value"] for r in active)
        total_solo_ev = sum(r["expected_value"] for r in solo)

        lines = [
            "# Cohezion Funding Strategy Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
            f"Target: {self.target} | Unique sources evaluated: {len(seen)}",
            "",
            "## Executive Summary",
            "",
            f"- **Total unique opportunities**: {len(active)}",
            f"- **Solo-eligible**: {len(solo)} | **Institutional-only**: {len(inst)}",
            f"- **Total prize pool (solo, gross)**: ${total_solo:,.0f}K",
            f"- **Total solo EV**: ${total_solo_ev:,.0f}",
            "- **Top insight**: Competitions = solo-friendly; Grants = need LLC/university",
            "",
            "## Active Opportunities (Solo-Eligible Ranked by EV)",
            "",
            "| Rank | Source | Prize ($K) | EV | Fit | Weeks | URL |",
            "|------|--------|------------|-----|------|-------|-----|",
        ]
        for i, r in enumerate(solo, 1):
            url = r.get("url", "")
            lines.append(
                f"| {i} | {r['source']} | {r['estimated_amount_k']:,} | "
                f"${r['expected_value']:,.0f} | {r['fit_score']:.2f} | {r['deadline_weeks']} | {url} |"
            )
        lines += [
            "",
            "### Institutional-Only (Require LLC / University / Nonprofit)",
            "",
            "| Rank | Source | Prize ($K) | EV | Fit | Weeks | URL |",
            "|------|--------|------------|-----|------|-------|-----|",
        ]
        for i, r in enumerate(inst, 1):
            url = r.get("url", "")
            lines.append(
                f"| {i} | {r['source']} | {r['estimated_amount_k']:,} | "
                f"${r['expected_value']:,.0f} | {r['fit_score']:.2f} | {r['deadline_weeks']} | {url} |"
            )
        lines += ["", "## Action Plan", ""]
        urgent = [r for r in active if r["deadline_weeks"] <= 4]
        if urgent:
            lines.append("### This Week (P0 — Hard Deadlines)")
            for r in urgent:
                if r["deadline_weeks"] <= 0:
                    lines.append(f"- [ ] **{r['source']}** — DEADLINE PASSED")
                else:
                    lines.append(f"- [ ] **{r['source']}** ({r['deadline_weeks']}w left) — {r['url']}")
        lines += ["", "### Next 30 Days (P1)", "",
                    "- [ ] Outline application for ARC Prize Paper Track",
                    "- [ ] Outline application for Nemotron Reasoning",
                    "- [ ] Check XPRIZE Water Scarcity rules",
                    "",
                    "### Ongoing Monitoring",
                    "",
                    "- [ ] Weekly: `kaggle competitions list`",
                    "- [ ] Monthly: Check xprize.org for new competitions",
                    "- [ ] Consider registering an LLC to unlock grants ($100-$300)",
                    "",
                    "---",
                    "*Generated by autoresearch_funding.py | K-Search: `${KSEARCH_DIR}`*",
        ]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Cohezion Funding Autoresearch")
    parser.add_argument("--target", default="all", choices=list(FUNDING_TARGETS))
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--budget-hours", type=float, default=4)
    parser.add_argument("--report", default="autoresearch_funding_report.md")
    args = parser.parse_args()

    driver = FundingAutoresearchDriver(target=args.target, budget_hours=args.budget_hours)
    logger.info(f"Starting: target={args.target}, iterations={args.iterations}, budget={args.budget_hours}h")
    results = driver.run_loop(iterations=args.iterations)
    logger.info(f"Completed {len(results)} iterations.")
    ranked = driver.get_ranked()
    if ranked:
        logger.info(f"Top: {ranked[0]['source']} (EV=${ranked[0]['expected_value']:,.0f})")

    report = driver.generate_report()
    report_path = Path(args.report)
    report_path.write_text(report, encoding="utf-8")
    logger.info(f"Report written to: {report_path.resolve()}")
    return results


if __name__ == "__main__":
    main()
