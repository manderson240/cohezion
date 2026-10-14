"""Unit tests for Kaggle Discussion Learner & Competitive Knowledge Extractor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.researcher.kaggle_discussion_learner import (
    KaggleDiscussionLearner,
    classify_topic_category,
    clean_html,
    compute_signal_score,
)


def test_clean_html():
    raw = "<p>Hello <b>World</b>!</p><br/>Check this out &amp; learn."
    cleaned = clean_html(raw)
    assert "Hello World!" in cleaned
    assert "Check this out & learn." in cleaned
    assert "<" not in cleaned
    assert ">" not in cleaned


def test_signal_scoring_and_categorization():
    bug_title = "Submission finished in ~15 minutes with 0.00 score and no error"
    bug_msgs = [{"content": "We had a timeout and docker path resolution failure causing 0.00."}]
    score_bug = compute_signal_score(bug_title, bug_msgs, votes=25, comments=21)
    category_bug = classify_topic_category(bug_title, bug_msgs)
    assert category_bug == "BUG_ALERT"
    assert score_bug > 10.0

    sota_title = "RSNA Raptor Weights and Multi-Slice CoAtNet SOTA"
    sota_msgs = [{"content": "Here are pretrained weights achieving 0.943 LB with DinoV2."}]
    category_sota = classify_topic_category(sota_title, sota_msgs)
    assert category_sota == "SOTA_RECIPE"

    rules_title = "Chasing medals with price ineligible sources"
    rules_msgs = [{"content": "External database license disqualifies prize eligibility."}]
    category_rules = classify_topic_category(rules_title, rules_msgs)
    assert category_rules == "RULES_COMPLIANCE"

    spam_title = "Looking for teammates for the competition! WhatsApp me"
    spam_msgs = [{"content": "Beginner here, let's connect on telegram."}]
    score_spam = compute_signal_score(spam_title, spam_msgs, votes=1, comments=1)
    assert score_spam < score_bug


@patch("cohezion.researcher.kaggle_discussion_learner.KaggleApi")
def test_fetch_competition_discussions_mocked(mock_api_cls):
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    # Mock competition_list_topics for 'top' and 'active'
    topic1 = MagicMock(id=101, title="Bug with 0.00 score", comment_count=10, votes=10, topic_url="/c/test/101")
    topic2 = MagicMock(id=102, title="Pretrained weights SOTA", comment_count=5, votes=5, topic_url="/c/test/102")
    
    # Return topic1 on 'top', topic1 and topic2 on 'active' to test de-duplication
    resp_top = MagicMock(topics=[topic1])
    resp_active = MagicMock(topics=[topic1, topic2])
    mock_api.competition_list_topics.side_effect = lambda slug, sort_by: (
        resp_top if sort_by == "top" else resp_active
    )

    msg1 = MagicMock(content="<p>Fatal bug in test set</p>", author_name="GrandmasterX", post_date="2026-10-01", votes=15)
    mock_api.competition_list_topic_messages.return_value = MagicMock(messages=[msg1])

    learner = KaggleDiscussionLearner()
    results = learner.fetch_competition_discussions("arc-prize-2026-arc-agi-2", max_topics_per_mode=2)

    assert len(results) == 2
    # Verify de-duplication: topic1 should appear only once
    topic_ids = [t["id"] for t in results]
    assert topic_ids == [101, 102]
    assert results[0]["category"] in ["BUG_ALERT", "SOTA_RECIPE"]
    assert "signal_score" in results[0]


def test_generate_markdown_report(tmp_path: Path):
    mock_data = {
        "arc-prize-2026-arc-agi-2": [
            {
                "id": 101,
                "title": "Bug with 0.00 score",
                "url": "/c/arc-prize-2026-arc-agi-2/discussion/101",
                "comments": 10,
                "signal_score": 15.5,
                "category": "BUG_ALERT",
                "messages": [
                    {
                        "author": "GrandmasterX",
                        "date": "2026-10-01",
                        "votes": 15,
                        "content": "Fatal bug in test set",
                    }
                ],
            }
        ]
    }
    learner = KaggleDiscussionLearner.__new__(KaggleDiscussionLearner)
    out_file = tmp_path / "test_report.md"
    learner.generate_markdown_report(mock_data, out_file)

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "arc-prize-2026-arc-agi-2" in content
    assert "BUG_ALERT" in content
    assert "GrandmasterX" in content
    assert "Fatal bug in test set" in content
