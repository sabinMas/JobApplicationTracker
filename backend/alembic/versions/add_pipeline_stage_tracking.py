"""Add pipeline stage tracking and discovery limits

Revision ID: add_pipeline_stage_001
Revises: 9df78440fd86
Create Date: 2025-04-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_pipeline_stage_001'
down_revision = '9df78440fd86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pipeline stage tracking columns to jobs table
    op.add_column('jobs', sa.Column('pipeline_stage', sa.String(50), server_default='discovered', nullable=False))
    op.add_column('jobs', sa.Column('pipeline_data', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('jobs', sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('enrichment_data', sa.Text(), nullable=True))
    
    # Add discovery limits to search_preferences table
    op.add_column('search_preferences', sa.Column('max_jobs_per_discovery_run', sa.Integer(), server_default='25', nullable=False))
    op.add_column('search_preferences', sa.Column('max_jobs_to_score_per_run', sa.Integer(), server_default='25', nullable=False))
    op.add_column('search_preferences', sa.Column('score_batch_size', sa.Integer(), server_default='5', nullable=False))
    
    # Create index for pipeline stage queries
    op.create_index('idx_pipeline_stage', 'jobs', ['pipeline_stage'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_pipeline_stage', table_name='jobs')
    
    # Remove columns from jobs
    op.drop_column('jobs', 'enrichment_data')
    op.drop_column('jobs', 'enriched_at')
    op.drop_column('jobs', 'pipeline_data')
    op.drop_column('jobs', 'pipeline_stage')
    
    # Remove columns from search_preferences
    op.drop_column('search_preferences', 'score_batch_size')
    op.drop_column('search_preferences', 'max_jobs_to_score_per_run')
    op.drop_column('search_preferences', 'max_jobs_per_discovery_run')
