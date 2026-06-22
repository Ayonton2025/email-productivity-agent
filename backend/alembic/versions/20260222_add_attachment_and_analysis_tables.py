"""add attachment and document analysis tables

Revision ID: 20260222_add_attachment_and_analysis_tables
Revises: 20260220_add_llm_updated_by_fk
Create Date: 2026-02-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_add_attachment_and_analysis_tables"
down_revision = "20260220_add_llm_updated_by_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "email_attachments" not in tables:
        op.create_table(
            "email_attachments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("mime_type", sa.String(), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("file_hash", sa.String(), nullable=True),
            sa.Column("storage_path", sa.String(), nullable=False),
            sa.Column("storage_type", sa.String(), nullable=True, server_default="local"),
            sa.Column("is_downloadable", sa.Boolean(), nullable=True, server_default=sa.true()),
            sa.Column("extension", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("file_hash"),
        )
        op.create_index("ix_email_attachments_email_id", "email_attachments", ["email_id"])
        op.create_index("ix_email_attachments_user_id", "email_attachments", ["user_id"])

    if "document_analysis" not in tables:
        op.create_table(
            "document_analysis",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("attachment_id", sa.String(), sa.ForeignKey("email_attachments.id"), nullable=False),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("analysis_type", sa.String(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=False),
            sa.Column("file_extension", sa.String(), nullable=True),
            sa.Column("file_size_display", sa.String(), nullable=True),
            sa.Column("extracted_title", sa.String(), nullable=True),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("key_points", sa.JSON(), nullable=True),
            sa.Column("entities", sa.JSON(), nullable=True),
            sa.Column("sentiment", sa.String(), nullable=True),
            sa.Column("language", sa.String(), nullable=True),
            sa.Column("is_full_analysis", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("is_sensitive", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("confidence_score", sa.Integer(), nullable=True),
            sa.Column("analysis_status", sa.String(), nullable=True, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_analysis_attachment_id", "document_analysis", ["attachment_id"])
        op.create_index("ix_document_analysis_user_id", "document_analysis", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "document_analysis" in tables:
        op.drop_index("ix_document_analysis_user_id", table_name="document_analysis")
        op.drop_index("ix_document_analysis_attachment_id", table_name="document_analysis")
        op.drop_table("document_analysis")

    if "email_attachments" in tables:
        op.drop_index("ix_email_attachments_user_id", table_name="email_attachments")
        op.drop_index("ix_email_attachments_email_id", table_name="email_attachments")
        op.drop_table("email_attachments")
