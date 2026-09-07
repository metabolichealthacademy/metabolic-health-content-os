"""Create workflows and append-only audit-event storage."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("topic", sa.String(300), nullable=False),
        sa.Column("audience", sa.String(100), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("claims", sa.JSON(), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("artifacts", sa.JSON(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflows_stage", "workflows", ["stage"])
    op.create_index("ix_workflows_status", "workflows", ["status"])
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_id",
            sa.String(36),
            sa.ForeignKey("workflows.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("from_stage", sa.String(32), nullable=False),
        sa.Column("to_stage", sa.String(32), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("actor_id", sa.String(128)),
        sa.UniqueConstraint("workflow_id", "sequence", name="uq_workflow_event_sequence"),
    )
    op.create_index(
        "ix_workflow_events_workflow_timestamp", "workflow_events", ["workflow_id", "timestamp"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_events_workflow_timestamp", table_name="workflow_events")
    op.drop_table("workflow_events")
    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_index("ix_workflows_stage", table_name="workflows")
    op.drop_table("workflows")
