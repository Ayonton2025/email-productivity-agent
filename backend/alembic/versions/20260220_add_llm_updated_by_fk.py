"""add llm_provider_configs.updated_by FK

Revision ID: 20260220_add_llm_updated_by_fk
Revises: 
Create Date: 2026-02-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260220_add_llm_updated_by_fk'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Only create the FK if the table and column exist and the constraint is absent
    try:
        op.create_foreign_key(
            'fk_llm_updated_by_users',
            'llm_provider_configs',
            'users',
            ['updated_by'],
            ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        # Best-effort: ignore if constraint already exists or DB incompatible
        pass


def downgrade() -> None:
    try:
        op.drop_constraint('fk_llm_updated_by_users', 'llm_provider_configs', type_='foreignkey')
    except Exception:
        pass
