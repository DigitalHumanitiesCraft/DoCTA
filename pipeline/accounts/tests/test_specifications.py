"""Alignment tests for the committed accounts core specification."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.accounts.models import (
    CORE_SPECIFICATION_ID,
    CORE_SPECIFICATION_VERSION,
    EditorialDecision,
    PublicationStatus,
    Side,
    VerificationStatus,
    model_schemas,
)

SPECIFICATION = Path(__file__).parents[1] / "specifications" / "core-v1.json"


def _values(enum_type: type) -> list[str]:
    return [item.value for item in enum_type]


def test_committed_specification_matches_models_and_vocabularies() -> None:
    specification = json.loads(SPECIFICATION.read_text(encoding="utf-8"))
    assert specification["specificationId"] == CORE_SPECIFICATION_ID
    assert specification["version"] == CORE_SPECIFICATION_VERSION
    schemas = model_schemas()
    assert set(specification["models"]) == set(schemas)
    for name, fields in specification["models"].items():
        assert set(fields) == set(schemas[name]["properties"]), name
        assert schemas[name]["additionalProperties"] is False
        assert all("_" not in field for field in fields), name
    assert specification["vocabularies"] == {
        "verification": _values(VerificationStatus),
        "editorialDecision": _values(EditorialDecision),
        "publication": _values(PublicationStatus),
        "side": _values(Side),
    }
