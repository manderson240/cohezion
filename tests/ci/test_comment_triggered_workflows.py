"""A workflow that anyone can start by commenting must not hand them a secret.

Comment and issue events fire for every GitHub user, including people with no
access to the repo. A job on those events that uses a secret has to check the
commenter's ``author_association`` first.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
OPEN_EVENTS = {
    "issue_comment",
    "pull_request_review_comment",
    "pull_request_review",
    "issues",
    "discussion_comment",
}
TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")


def _events(doc: dict) -> set[str]:
    on = doc.get(True, doc.get("on"))  # PyYAML reads the key `on` as True
    if isinstance(on, str):
        return {on}
    return set(on or [])


def _has_own_guard(job: dict) -> bool:
    condition = str(job.get("if", ""))
    return "author_association" in condition and all(t in condition for t in TRUSTED)


def _uses_secret(job: dict) -> bool:
    return "secrets." in yaml.safe_dump(job) or job.get("secrets") == "inherit"


def unguarded_jobs(doc: dict) -> list[str]:
    """Jobs on open events that use a secret without an author_association check.

    A job also counts as guarded when every job it ``needs`` is guarded, because it
    can't run unless they did. ``always()`` breaks that, so an ``always()`` job is
    only guarded through its needs when its condition also requires an upstream
    failure or output (``failure()`` / ``needs.``).
    """
    if not _events(doc) & OPEN_EVENTS:
        return []
    jobs = doc.get("jobs") or {}
    guarded: dict[str, bool] = {}

    def is_guarded(name: str) -> bool:
        if name not in guarded:
            job = jobs[name]
            needs = job.get("needs") or []
            needs = [needs] if isinstance(needs, str) else needs
            condition = str(job.get("if", ""))
            through_needs = bool(needs) and all(is_guarded(n) for n in needs)
            if "always()" in condition and not ("failure()" in condition or "needs." in condition):
                through_needs = False
            guarded[name] = _has_own_guard(job) or through_needs
        return guarded[name]

    return [name for name, job in jobs.items() if _uses_secret(job) and not is_guarded(name)]


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_open_event_jobs_check_the_commenter(path: Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert not unguarded_jobs(doc), (
        f"{path.name}: jobs {unguarded_jobs(doc)} run on comment/issue events and use a "
        "secret, so they must check author_association against OWNER/MEMBER/COLLABORATOR"
    )


def test_checker_flags_an_unguarded_job() -> None:
    doc = yaml.safe_load(
        "on: issue_comment\n"
        "jobs:\n"
        "  agent:\n"
        "    if: contains(github.event.comment.body, '/oc')\n"
        "    steps:\n"
        "      - env: {KEY: '${{ secrets.KEY }}'}\n"
    )
    assert unguarded_jobs(doc) == ["agent"]


def test_checker_accepts_a_guarded_job() -> None:
    doc = yaml.safe_load(
        "on: issue_comment\n"
        "jobs:\n"
        "  agent:\n"
        '    if: contains(fromJSON(\'["OWNER", "MEMBER", "COLLABORATOR"]\'), '
        "github.event.comment.author_association)\n"
        "    steps:\n"
        "      - env: {KEY: '${{ secrets.KEY }}'}\n"
    )
    assert unguarded_jobs(doc) == []


def test_checker_follows_needs_but_not_a_bare_always() -> None:
    doc = yaml.safe_load(
        "on: issue_comment\n"
        "jobs:\n"
        "  gate:\n"
        '    if: contains(fromJSON(\'["OWNER", "MEMBER", "COLLABORATOR"]\'), '
        "github.event.comment.author_association)\n"
        "    steps: [{run: 'true'}]\n"
        "  after:\n"
        "    needs: gate\n"
        "    uses: ./.github/workflows/x.yml\n"
        "    secrets: inherit\n"
        "  always_runs:\n"
        "    needs: gate\n"
        "    if: always()\n"
        "    uses: ./.github/workflows/x.yml\n"
        "    secrets: inherit\n"
    )
    assert unguarded_jobs(doc) == ["always_runs"]
