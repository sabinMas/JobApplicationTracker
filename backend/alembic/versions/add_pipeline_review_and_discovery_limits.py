"""Add pipeline review stage, discovery limits, and URL deduplication.

Revision ID: add_pipeline_review
Revises: 9df78440fd86
Create Date: 2026-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_pipeline_review'
down_revision: Union[str, Sequence[str], None] = '9df78440fd86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to search_preferences
    op.add_column('search_preferences',
                  sa.Column('max_jobs_per_discovery_run', sa.Integer(), nullable=True, server_default='50'))
    op.add_column('search_preferences',
                  sa.Column('skip_previously_discovered', sa.Boolean(), nullable=True, server_default='1'))

    # Add pipeline_stage, pipeline_data, enriched_at, enrichment_data to jobs
    op.add_column('jobs',
                  sa.Column('pipeline_stage', sa.String(length=50), nullable=True, server_default='discovered'))
    op.add_column('jobs',
                  sa.Column('pipeline_data', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('jobs',
                  sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs',
                  sa.Column('enrichment_data', sa.Text(), nullable=True))

    # Create discovered_job_urls table
    op.create_table('discovered_job_urls',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_url', sa.String(length=1000), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_url', name='uq_discovered_job_url')
    )
    op.create_index('idx_discovered_job_url_source', 'discovered_job_urls', ['source', 'discovered_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_discovered_job_url_source', table_name='discovered_job_urls')
    op.drop_table('discovered_job_urls')
    op.drop_column('jobs', 'enrichment_data')
    op.drop_column('jobs', 'enriched_at')
    op.drop_column('jobs', 'pipeline_data')
    op.drop_column('jobs', 'pipeline_stage')
    op.drop_column('search_preferences', 'skip_previously_discovered')
    op.drop_column('search_preferences', 'max_jobs_per_discovery_run')
