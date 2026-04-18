"""v2.7 Reader Experience Overlay 迁移

新增表：
- chapter_rewrite_attempts: 章节重写尝试记录
- band_experience_plans: Band 体验计划

新增字段：
- chapters.experience_plan_json
- arc_structure_drafts.reader_promise_json
- arc_structure_drafts.arc_payoff_map_json
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = 'v2_7_reader_experience'
down_revision = None  # 指向最新的迁移
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增 chapters.experience_plan_json 字段
    op.add_column(
        'chapters',
        sa.Column('experience_plan_json', sa.Text(), nullable=True)
    )
    
    # 2. 新增 arc_structure_drafts.reader_promise_json 字段
    op.add_column(
        'arc_structure_drafts',
        sa.Column('reader_promise_json', sa.Text(), nullable=True)
    )
    
    # 3. 新增 arc_structure_drafts.arc_payoff_map_json 字段
    op.add_column(
        'arc_structure_drafts',
        sa.Column('arc_payoff_map_json', sa.Text(), nullable=True)
    )
    
    # 4. 新增 chapter_rewrite_attempts 表
    op.create_table(
        'chapter_rewrite_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('attempt_no', sa.Integer(), nullable=False),
        sa.Column('trigger_review_id', sa.Integer(), nullable=True),
        sa.Column('repair_scope', sa.String(20), nullable=False),
        sa.Column('design_patch_json', sa.Text(), nullable=True),
        sa.Column('source_draft_id', sa.Integer(), nullable=True),
        sa.Column('result_draft_id', sa.Integer(), nullable=True),
        sa.Column('result_verdict', sa.String(20), nullable=True),
        sa.Column('forced_accept_applied', sa.Boolean(), nullable=True),
        sa.Column('repair_instruction_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. 新增 band_experience_plans 表
    op.create_table(
        'band_experience_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('arc_no', sa.Integer(), nullable=False),
        sa.Column('band_no', sa.Integer(), nullable=False),
        sa.Column('band_name', sa.String(200), nullable=True),
        sa.Column('start_chapter', sa.Integer(), nullable=False),
        sa.Column('end_chapter', sa.Integer(), nullable=False),
        sa.Column('delight_schedule_json', sa.Text(), nullable=True),
        sa.Column('delight_per_chapter_avg', sa.Float(), nullable=True),
        sa.Column('distribution', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 6. 新增 review_notes.forced_accept_applied 字段
    op.add_column(
        'review_notes',
        sa.Column('forced_accept_applied', sa.Boolean(), nullable=True)
    )
    
    # 7. 新增 review_notes.override_reason 字段
    op.add_column(
        'review_notes',
        sa.Column('override_reason', sa.Text(), nullable=True)
    )
    
    # 8. 新增 review_notes.rewrite_attempt_count 字段
    op.add_column(
        'review_notes',
        sa.Column('rewrite_attempt_count', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    # 删除 review_notes 的新增字段
    op.drop_column('review_notes', 'rewrite_attempt_count')
    op.drop_column('review_notes', 'override_reason')
    op.drop_column('review_notes', 'forced_accept_applied')
    
    # 删除表
    op.drop_table('band_experience_plans')
    op.drop_table('chapter_rewrite_attempts')
    
    # 删除 arc_structure_drafts 的新增字段
    op.drop_column('arc_structure_drafts', 'arc_payoff_map_json')
    op.drop_column('arc_structure_drafts', 'reader_promise_json')
    
    # 删除 chapters 的新增字段
    op.drop_column('chapters', 'experience_plan_json')
