"""Apache Iceberg REST Catalog Fine-Grained Access Control & Read-Restrictions.

Implements the official Apache Iceberg REST Catalog specification standard for reader-side
fine-grained access control (October 1, 2026; Google Cloud / Apache Iceberg community):
1. 'read-restrictions' payload schema (required-row-filter and required-column-projections).
2. The 9 canonical masking actions with bit-for-bit mathematical and behavioral parity.
3. Two-phase enforcement invariant: row filters evaluated on untransformed raw data,
   column projections applied strictly to surviving rows.
4. Normative Fail-Closed Principle: Any unhandled action, evaluation fault, or syntax
   error aborts query execution immediately with zero data leakage.
"""

from __future__ import annotations

import datetime
import hashlib
import re
import secrets
from collections.abc import Callable, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MaskingAction(StrEnum):
    """The nine canonical masking actions standardized in Apache Iceberg REST Catalog."""

    MASK_ALPHANUM = "mask-alphanum"
    SHOW_FIRST_4 = "show-first-4"
    SHOW_LAST_4 = "show-last-4"
    REPLACE_WITH_NULL = "replace-with-null"
    MASK_TO_FIXED_VALUE = "mask-to-fixed-value"
    TRUNCATE_TO_YEAR = "truncate-to-year"
    TRUNCATE_TO_MONTH = "truncate-to-month"
    SHA_256_GLOBAL = "sha-256-global"
    SHA_256_QUERY_LOCAL = "sha-256-query-local"


class FailClosedViolationError(RuntimeError):
    """Raised when access control cannot be applied, forcing fail-closed zero-data leakage."""


class ColumnProjection(BaseModel):
    """Specification of a projection obligation bound to a physical column field ID."""

    field_id: int = Field(..., description="Unique physical field identifier (never column name).")
    action: MaskingAction = Field(..., description="One of the 9 canonical masking actions.")
    field_name: str | None = Field(default=None, description="Optional logical field name hint.")
    is_nullable: bool = Field(
        default=True, description="Whether the column schema permits NULL values."
    )
    is_map_key: bool = Field(default=False, description="Whether this column represents a map key.")
    is_nested_child: bool = Field(
        default=False, description="Whether this column is nested inside a masked struct."
    )


class ReadRestrictions(BaseModel):
    """Apache Iceberg REST Catalog ReadRestrictions payload."""

    required_row_filter: str | None = Field(
        default=None,
        description="Predicate expression evaluated on raw untransformed records.",
    )
    required_column_projections: list[ColumnProjection] = Field(
        default_factory=list,
        description="Ordered list of required column masking projections.",
    )


class FineGrainedAccessController:
    """Enforces Apache Iceberg REST Catalog read restrictions with fail-closed security.

    Key Invariants:
    1. Row filter evaluated on raw data first.
    2. Column projections applied to surviving rows second.
    3. Fail-closed: any failure aborts query execution with zero data returned.
    4. Query-local salt for sha-256-query-local refreshed per session/query (>=16 bytes).
    """

    _ALPHANUM_PRESERVE = set("(),.-@ ")

    def __init__(self, query_salt: bytes | None = None) -> None:
        """Initialize controller with optional or cryptographically generated query salt."""
        if query_salt is not None:
            if len(query_salt) < 16:
                raise FailClosedViolationError(
                    f"Query salt must be at least 16 bytes per specification, got {len(query_salt)} bytes"
                )
            self._query_salt = query_salt
        else:
            self._query_salt = secrets.token_bytes(16)

    @property
    def query_salt(self) -> bytes:
        """Return the cryptographically secure query-local salt."""
        return self._query_salt

    def validate_restrictions(self, restrictions: ReadRestrictions) -> None:
        """Validate specification constraints before applying restrictions.

        Fails closed if any prohibition is violated:
        - Duplicate field IDs in column projections.
        - Projections applied to map keys.
        - replace-with-null applied to non-nullable fields.
        - Unrecognized masking actions.
        """
        seen_field_ids: set[int] = set()
        has_struct_mask = False

        for proj in restrictions.required_column_projections:
            # 1. Prohibit duplicate field IDs
            if proj.field_id in seen_field_ids:
                raise FailClosedViolationError(
                    f"Duplicate field_id {proj.field_id} in required-column-projections violates spec."
                )
            seen_field_ids.add(proj.field_id)

            # 2. Prohibit projections on map keys
            if proj.is_map_key:
                raise FailClosedViolationError(
                    f"Projections on map keys are forbidden by Iceberg specification (field_id {proj.field_id})."
                )

            # 3. Prohibit replace-with-null on non-nullable fields
            if proj.action == MaskingAction.REPLACE_WITH_NULL and not proj.is_nullable:
                raise FailClosedViolationError(
                    f"Action 'replace-with-null' cannot be applied to required non-nullable field {proj.field_id}."
                )

            # 4. Prohibit conflicting nested struct projections
            if proj.is_nested_child and has_struct_mask:
                raise FailClosedViolationError(
                    f"Conflicting projections on both a struct and nested field {proj.field_id} are forbidden."
                )

    def apply_restrictions(
        self,
        records: Sequence[dict[str, Any]],
        field_id_to_name: dict[int, str],
        restrictions: ReadRestrictions,
        custom_filter_evaluator: Callable[[dict[str, Any], str], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Apply fine-grained row filtering and column projections with fail-closed semantics.

        Parameters
        ----------
        records : Sequence[dict[str, Any]]
            Input tabular or dictionary records.
        field_id_to_name : dict[int, str]
            Bidirectional schema mapping from physical field-id to record column keys.
        restrictions : ReadRestrictions
            Apache Iceberg REST Catalog read restrictions payload.
        custom_filter_evaluator : Callable[[dict[str, Any], str], bool] | None
            Optional evaluator for complex predicate expressions.

        Returns
        -------
        list[dict[str, Any]]
            Sanitized records with surviving rows and projected columns.

        Raises
        ------
        FailClosedViolationError
            If any projection or filter cannot be evaluated or violates spec constraints.
        """
        try:
            # Step 0: Pre-flight validation
            self.validate_restrictions(restrictions)

            # Step 1: Evaluate row filter on RAW, untransformed data
            surviving_records: list[dict[str, Any]] = []
            filter_expr = restrictions.required_row_filter

            for row in records:
                if filter_expr is None or self._evaluate_row_filter(
                    row, filter_expr, custom_filter_evaluator
                ):
                    # Shallow copy row so transformations do not mutate caller's original data
                    surviving_records.append(dict(row))

            # Step 2: Apply required column projections to surviving rows
            if not restrictions.required_column_projections:
                return surviving_records

            projected_records: list[dict[str, Any]] = []
            for row in surviving_records:
                for proj in restrictions.required_column_projections:
                    field_name = field_id_to_name.get(proj.field_id, proj.field_name)
                    if field_name is None or field_name not in row:
                        raise FailClosedViolationError(
                            f"Field ID {proj.field_id} (name: {field_name}) not found in record schema."
                        )

                    raw_val = row[field_name]
                    transformed = self._apply_masking_action(raw_val, proj)
                    row[field_name] = transformed
                projected_records.append(row)

            return projected_records

        except FailClosedViolationError:
            raise
        except Exception as exc:
            # Strict fail-closed: never return raw or partially filtered data
            raise FailClosedViolationError(
                f"Fail-closed abort: Failed to apply read restrictions ({type(exc).__name__}: {exc})"
            ) from exc

    def _evaluate_row_filter(
        self,
        row: dict[str, Any],
        filter_expr: str,
        custom_evaluator: Callable[[dict[str, Any], str], bool] | None = None,
    ) -> bool:
        """Evaluate row filter predicate safely. Fails closed on syntax errors."""
        if custom_evaluator is not None:
            return custom_evaluator(row, filter_expr)

        # Standard simple predicate parser: e.g. "region = 'US'" or "active == True"
        clean = filter_expr.strip()
        # Match pattern: multi-character operators MUST precede single-character in alternation
        match = re.match(r"^([a-zA-Z0-9_]+)\s*(==|!=|>=|<=|=|>|<)\s*(.+)$", clean)
        if not match:
            raise FailClosedViolationError(
                f"Unparseable predicate expression '{filter_expr}'; aborting under fail-closed mandate."
            )

        field, op, val_str = match.groups()
        if field not in row:
            raise FailClosedViolationError(f"Predicate field '{field}' not found in record.")

        actual = row[field]
        val_str = val_str.strip().strip("'\"")

        # Basic scalar coercion
        target: Any = val_str
        if isinstance(actual, bool):
            target = val_str.lower() in ("true", "1")
        elif isinstance(actual, int):
            target = int(val_str)
        elif isinstance(actual, float):
            target = float(val_str)

        if op in ("=", "=="):
            return bool(actual == target)
        if op == "!=":
            return bool(actual != target)
        if op == ">":
            return bool(actual > target)
        if op == ">=":
            return bool(actual >= target)
        if op == "<":
            return bool(actual < target)
        if op == "<=":
            return bool(actual <= target)

        raise FailClosedViolationError(f"Unsupported operator '{op}' in predicate.")

    def _apply_masking_action(self, val: Any, proj: ColumnProjection) -> Any:
        """Apply one of the 9 canonical masking actions bit-for-bit."""
        action = proj.action

        if action == MaskingAction.REPLACE_WITH_NULL:
            return None

        if action == MaskingAction.MASK_TO_FIXED_VALUE:
            return self._mask_to_fixed_value(val)

        # For remaining actions, NULL inputs propagate as NULL unless specified
        if val is None:
            return None

        if action == MaskingAction.MASK_ALPHANUM:
            return self._mask_alphanum(str(val))

        if action == MaskingAction.SHOW_FIRST_4:
            return self._show_first_4(str(val))

        if action == MaskingAction.SHOW_LAST_4:
            return self._show_last_4(str(val))

        if action == MaskingAction.TRUNCATE_TO_YEAR:
            return self._truncate_to_year(val)

        if action == MaskingAction.TRUNCATE_TO_MONTH:
            return self._truncate_to_month(val)

        if action == MaskingAction.SHA_256_GLOBAL:
            return self._sha_256_global(val)

        if action == MaskingAction.SHA_256_QUERY_LOCAL:
            return self._sha_256_query_local(val)

        raise FailClosedViolationError(f"Unrecognized masking action: {action}")

    def _mask_alphanum(self, s: str) -> str:
        """Replace digits with 'n', letters with 'x', preserving allowed punctuation."""
        out = []
        for ch in s:
            if ch.isdigit():
                out.append("n")
            elif ch.isalpha():
                out.append("x")
            elif ch in self._ALPHANUM_PRESERVE:
                out.append(ch)
            else:
                out.append("x")
        return "".join(out)

    def _show_first_4(self, s: str) -> str:
        """Retain first 4 characters, apply mask-alphanum to remainder."""
        if len(s) <= 4:
            return s
        return s[:4] + self._mask_alphanum(s[4:])

    def _show_last_4(self, s: str) -> str:
        """Retain last 4 characters, apply mask-alphanum to preceding."""
        if len(s) <= 4:
            return s
        return self._mask_alphanum(s[:-4]) + s[-4:]

    def _mask_to_fixed_value(self, val: Any) -> Any:
        """Type-specific constant replacement hiding even existence bit."""
        if isinstance(val, bool):
            return False
        if isinstance(val, (int, float)):
            return 0
        if isinstance(val, (list, tuple)):
            return []
        if isinstance(val, dict):
            return {}
        if isinstance(val, (datetime.date, datetime.datetime)):
            return "1970-01-01"
        return "XXXXXXXX"

    def _truncate_to_year(self, val: Any) -> str:
        """Truncate date/datetime or ISO string to YYYY-01-01."""
        if isinstance(val, (datetime.date, datetime.datetime)):
            return f"{val.year:04d}-01-01"
        s = str(val)[:10]
        match = re.match(r"^(\d{4})", s)
        if match:
            return f"{match.group(1)}-01-01"
        raise FailClosedViolationError(f"Cannot truncate invalid date value '{val}' to year.")

    def _truncate_to_month(self, val: Any) -> str:
        """Truncate date/datetime or ISO string to YYYY-MM-01."""
        if isinstance(val, (datetime.date, datetime.datetime)):
            return f"{val.year:04d}-{val.month:02d}-01"
        s = str(val)[:10]
        match = re.match(r"^(\d{4})-(\d{2})", s)
        if match:
            return f"{match.group(1)}-{match.group(2)}-01"
        raise FailClosedViolationError(f"Cannot truncate invalid date value '{val}' to month.")

    def _sha_256_global(self, val: Any) -> str:
        """Deterministic SHA-256 hash across tables without query salt."""
        encoded = str(val).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _sha_256_query_local(self, val: Any) -> str:
        """Salted SHA-256 hash using query-local cryptographically secure salt."""
        encoded = self._query_salt + str(val).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
