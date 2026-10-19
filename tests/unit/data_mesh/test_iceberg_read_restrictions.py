"""Unit tests for Apache Iceberg REST Catalog Fine-Grained Access Control & Read-Restrictions.

Tests compliance with Google Cloud / Apache Iceberg standard (October 1, 2026):
- 9 canonical masking actions bit-for-bit behavior.
- Two-phase execution invariant (row filters evaluated on raw data first, column projections second).
- Strict fail-closed zero-leakage abort semantics.
- Query-local salt entropy and uniqueness.
"""

from __future__ import annotations

import datetime

import pytest

from cohezion.data_mesh.iceberg_read_restrictions import (
    ColumnProjection,
    FailClosedViolationError,
    FineGrainedAccessController,
    MaskingAction,
    ReadRestrictions,
)


def test_mask_alphanum_preserves_allowlist_punctuation() -> None:
    controller = FineGrainedAccessController()
    email = "iceberg16112018@apache.org"
    proj = ColumnProjection(field_id=1, action=MaskingAction.MASK_ALPHANUM)
    res = controller._apply_masking_action(email, proj)
    # Digits -> n, letters -> x, @ and . preserved
    assert res == "xxxxxxxnnnnnnnn@xxxxxx.xxx"


def test_show_first_4_and_show_last_4() -> None:
    controller = FineGrainedAccessController()
    card = "4111-1111-1111-4444"

    # show-first-4
    proj_first = ColumnProjection(field_id=1, action=MaskingAction.SHOW_FIRST_4)
    res_first = controller._apply_masking_action(card, proj_first)
    assert res_first.startswith("4111")
    assert res_first[4:] == "-nnnn-nnnn-nnnn"

    # show-last-4
    proj_last = ColumnProjection(field_id=2, action=MaskingAction.SHOW_LAST_4)
    res_last = controller._apply_masking_action(card, proj_last)
    assert res_last.endswith("4444")
    assert res_last[:-4] == "nnnn-nnnn-nnnn-"


def test_replace_with_null_and_mask_to_fixed_value() -> None:
    controller = FineGrainedAccessController()

    # replace-with-null on nullable field
    proj_null = ColumnProjection(
        field_id=1, action=MaskingAction.REPLACE_WITH_NULL, is_nullable=True
    )
    assert controller._apply_masking_action("sensitive_data", proj_null) is None

    # mask-to-fixed-value
    proj_fixed = ColumnProjection(field_id=2, action=MaskingAction.MASK_TO_FIXED_VALUE)
    assert controller._apply_masking_action(12345, proj_fixed) == 0
    assert controller._apply_masking_action(True, proj_fixed) is False
    assert controller._apply_masking_action("secret_user", proj_fixed) == "XXXXXXXX"
    assert controller._apply_masking_action(datetime.date(2026, 10, 18), proj_fixed) == "1970-01-01"


def test_truncate_to_year_and_month() -> None:
    controller = FineGrainedAccessController()
    dt_str = "2026-10-18T22:00:00Z"

    proj_year = ColumnProjection(field_id=1, action=MaskingAction.TRUNCATE_TO_YEAR)
    assert controller._apply_masking_action(dt_str, proj_year) == "2026-01-01"

    proj_month = ColumnProjection(field_id=2, action=MaskingAction.TRUNCATE_TO_MONTH)
    assert controller._apply_masking_action(dt_str, proj_month) == "2026-10-01"


def test_sha_256_global_and_query_local_salt_isolation() -> None:
    ctrl_a = FineGrainedAccessController()
    ctrl_b = FineGrainedAccessController()

    val = "user_account_id_98765"
    proj_global = ColumnProjection(field_id=1, action=MaskingAction.SHA_256_GLOBAL)
    proj_local = ColumnProjection(field_id=2, action=MaskingAction.SHA_256_QUERY_LOCAL)

    # Global SHA-256 is deterministic across different controllers
    assert ctrl_a._apply_masking_action(val, proj_global) == ctrl_b._apply_masking_action(
        val, proj_global
    )

    # Query-local SHA-256 uses distinct salts per controller/query instance
    local_hash_a = ctrl_a._apply_masking_action(val, proj_local)
    local_hash_b = ctrl_b._apply_masking_action(val, proj_local)
    assert local_hash_a != local_hash_b

    # But within the same controller/query instance, local hash is reproducible
    assert ctrl_a._apply_masking_action(val, proj_local) == local_hash_a


def test_two_phase_evaluation_filter_then_project() -> None:
    """Crucial Invariant: row filter MUST evaluate on RAW untransformed data before projection."""
    controller = FineGrainedAccessController()

    records = [
        {"id": 1, "region": "US", "email": "alice@example.com"},
        {"id": 2, "region": "EU", "email": "bob@example.com"},
        {"id": 3, "region": "US", "email": "charlie@example.com"},
    ]
    field_id_map = {101: "id", 102: "region", 103: "email"}

    # Policy: Filter for region = 'US', AND mask region with mask-alphanum
    restrictions = ReadRestrictions(
        required_row_filter="region = 'US'",
        required_column_projections=[
            ColumnProjection(field_id=102, action=MaskingAction.MASK_ALPHANUM),
            ColumnProjection(field_id=103, action=MaskingAction.MASK_ALPHANUM),
        ],
    )

    sanitized = controller.apply_restrictions(records, field_id_map, restrictions)

    # Rows 1 and 3 survived the raw filter
    assert len(sanitized) == 2
    assert sanitized[0]["id"] == 1
    assert sanitized[1]["id"] == 3
    # Both region and email are now projected/masked
    assert sanitized[0]["region"] == "xx"
    assert sanitized[0]["email"] == "xxxxx@xxxxxxx.xxx"


def test_fail_closed_on_duplicate_field_ids() -> None:
    controller = FineGrainedAccessController()
    restrictions = ReadRestrictions(
        required_column_projections=[
            ColumnProjection(field_id=101, action=MaskingAction.SHOW_LAST_4),
            ColumnProjection(field_id=101, action=MaskingAction.REPLACE_WITH_NULL),
        ]
    )
    with pytest.raises(FailClosedViolationError, match="Duplicate field_id"):
        controller.validate_restrictions(restrictions)


def test_fail_closed_on_map_key_projection() -> None:
    controller = FineGrainedAccessController()
    restrictions = ReadRestrictions(
        required_column_projections=[
            ColumnProjection(field_id=101, action=MaskingAction.MASK_ALPHANUM, is_map_key=True),
        ]
    )
    with pytest.raises(FailClosedViolationError, match="Projections on map keys are forbidden"):
        controller.validate_restrictions(restrictions)


def test_fail_closed_on_replace_with_null_for_non_nullable_field() -> None:
    controller = FineGrainedAccessController()
    restrictions = ReadRestrictions(
        required_column_projections=[
            ColumnProjection(
                field_id=101, action=MaskingAction.REPLACE_WITH_NULL, is_nullable=False
            ),
        ]
    )
    with pytest.raises(
        FailClosedViolationError,
        match="Action 'replace-with-null' cannot be applied to required non-nullable field",
    ):
        controller.validate_restrictions(restrictions)


def test_fail_closed_on_unparseable_predicate() -> None:
    controller = FineGrainedAccessController()
    records = [{"id": 1, "status": "active"}]
    field_id_map = {101: "id", 102: "status"}
    restrictions = ReadRestrictions(required_row_filter="status ~~~ invalid")

    with pytest.raises(FailClosedViolationError, match="Unparseable predicate"):
        controller.apply_restrictions(records, field_id_map, restrictions)


def test_fail_closed_on_missing_field_id() -> None:
    controller = FineGrainedAccessController()
    records = [{"id": 1}]
    field_id_map = {101: "id"}
    restrictions = ReadRestrictions(
        required_column_projections=[
            ColumnProjection(field_id=999, action=MaskingAction.MASK_ALPHANUM),
        ]
    )
    with pytest.raises(FailClosedViolationError, match="Field ID 999"):
        controller.apply_restrictions(records, field_id_map, restrictions)


def test_fail_closed_on_short_salt() -> None:
    with pytest.raises(FailClosedViolationError, match="at least 16 bytes"):
        FineGrainedAccessController(query_salt=b"too_short")
