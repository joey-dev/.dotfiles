"""Reviewers may decorate their verdict with markdown."""

from __future__ import annotations

import pytest

from claude_workflow.stages.base import parse_verdict


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("APPROVED", "APPROVED"),
        ("# APPROVED", "APPROVED"),
        ("**APPROVED**", "APPROVED"),
        ("APPROVED.", "APPROVED"),
        ("\n\nApproved", "APPROVED"),
        ("`APPROVED`", "APPROVED"),
        ("CHANGES_REQUESTED", "CHANGES_REQUESTED"),
        ("## Changes requested", "CHANGES_REQUESTED"),
        ("CHANGES_REQUESTED: fix x", "CHANGES_REQUESTED"),
        ("> CHANGES REQUESTED", "CHANGES_REQUESTED"),
        ("NOT APPROVED", None),
        ("Looks good", None),
        ("APPROVEDISH", None),
        ("", None),
        ("APPROVED WITH CHANGES", None),
        ("Approved, but fix the typo first", None),
        ("Verdict: APPROVED", "APPROVED"),
        ("APPROVED — ready to merge", "APPROVED"),
    ],
)
def test_parse_verdict(text: str, expected: str | None) -> None:
    assert parse_verdict(text) == expected
