"""Protect the database contract captured before the domain extraction."""

import json
from pathlib import Path

from sqlalchemy.orm import configure_mappers

from app.models import billing_models
from app.models.database import Base


def test_billing_schema_matches_the_pre_refactor_contract():
    configure_mappers()
    expected = json.loads((Path(__file__).parent / "fixtures" / "billing_schema.json").read_text())
    actual = {}
    for name in expected:
        table = Base.metadata.tables[name]
        actual[name] = {
            "columns": {
                c.name: {
                    "type": str(c.type),
                    "nullable": c.nullable,
                    "primary_key": c.primary_key,
                    "foreign_keys": sorted(f.target_fullname for f in c.foreign_keys),
                }
                for c in table.columns
            },
            "indexes": sorted([i.name, i.unique, [c.name for c in i.columns]] for i in table.indexes),
            "unique_constraints": sorted(
                sorted(c.name for c in constraint.columns)
                for constraint in table.constraints
                if type(constraint).__name__ == "UniqueConstraint"
            ),
        }
    assert actual == expected


def test_legacy_billing_exports_refer_to_the_same_mapped_classes():
    from app.models.billing import addons, credits, payments, subscriptions, usage

    for module in (addons, credits, payments, subscriptions, usage):
        for name, value in vars(module).items():
            if isinstance(value, type) and hasattr(value, "__tablename__"):
                assert getattr(billing_models, name) is value
                assert value.__table__ is Base.metadata.tables[value.__tablename__]
