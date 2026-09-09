import hashlib
import json
from pathlib import Path

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable


def schema_fingerprints(metadata):
    def default_value(value):
        if value is None:
            return None
        return getattr(value.arg, "__name__", str(value.arg))

    result = {}
    for name, table in sorted(metadata.tables.items()):
        contract = {
            "ddl": [
                str(CreateTable(table).compile(dialect=dialect)) for dialect in (sqlite.dialect(), postgresql.dialect())
            ],
            "indexes": sorted(str(CreateIndex(index).compile(dialect=postgresql.dialect())) for index in table.indexes),
            "defaults": {
                column.name: [default_value(column.default), default_value(column.onupdate)] for column in table.columns
            },
        }
        result[name] = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    return result


def test_schema_matches_pre_consolidation_snapshot():
    from app.models import register_models
    from app.models.base import Base

    register_models()
    expected = json.loads((Path(__file__).parent / "fixtures" / "model_schema.json").read_text())
    assert schema_fingerprints(Base.metadata) == expected


def test_legacy_imports_share_canonical_classes_and_metadata():
    import importlib
    import pkgutil

    import app.models
    from app.models import database, email_models, email_provider_models, prompt_models, provider_models, user_models
    from app.models.base import Base

    app.models.register_models()
    assert database.User is app.models.User is user_models.User
    assert database.UserEmailAccount is user_models.UserEmailAccount is email_models.UserEmailAccount
    assert database.Email is email_provider_models.Email is email_models.Email
    assert database.EmailDraft is email_models.EmailDraft
    assert database.PromptTemplate is prompt_models.PromptTemplate
    assert (
        database.EmailProviderConfig is email_provider_models.EmailProviderConfig is provider_models.EmailProviderConfig
    )
    assert database.SyncHistory is email_provider_models.SyncHistory is provider_models.SyncHistory
    classes_by_table = {}
    for spec in pkgutil.iter_modules(app.models.__path__):
        if spec.name.endswith("_models"):
            module = importlib.import_module(f"app.models.{spec.name}")
            for value in vars(module).values():
                if isinstance(value, type) and hasattr(value, "__table__"):
                    assert value.metadata is Base.metadata
                    classes_by_table.setdefault(value.__tablename__, set()).add(value)
    assert classes_by_table.keys() == Base.metadata.tables.keys()
    assert all(len(classes) == 1 for classes in classes_by_table.values())


def test_cold_model_import_order_has_no_duplicate_registry_or_database_side_effect():
    import os
    import subprocess
    import sys

    backend = Path(__file__).resolve().parents[1]
    code = """
import importlib, pkgutil, sys
import app.models
from app.models.base import Base
names = sorted(item.name for item in pkgutil.iter_modules(app.models.__path__) if item.name.endswith('_models'))
if sys.argv[1] == 'reverse': names.reverse()
for name in names: importlib.import_module('app.models.' + name)
app.models.register_models()
assert 'app.models.database' not in sys.modules
assert len(Base.registry.mappers) == len(Base.metadata.tables) == 58
"""
    for order in ("forward", "reverse"):
        result = subprocess.run(
            [sys.executable, "-c", code, order],
            cwd=backend,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
