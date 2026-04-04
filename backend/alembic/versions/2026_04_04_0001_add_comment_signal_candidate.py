"""Phase A: Add CommentSignalCandidate table

Revision ID: 2026_04_04_0001
Revises: 
Create Date: 2026-04-04 00:00:00.000000

新增：
- CommentSignalCandidate 表：存储 LLM 解析后的结构化信号候选
  - signal_type: confusion / pacing / character_heat / risk
  - target_type: character / arc / plot / setting
  - target_name: 自由文本，如 "主角动机"
  - severity: 1~4
  - confidence: 0~1
  - evidence_span: 原文摘录
  - signal_level: noise / candidate / confirmed / watchlist (硬规则分级)
  - is_llm_generated: 是否是 LLM 生成
  - is_fallback: 是否是 fallback 到关键词的结果

注意：
- 不替代现有的 CommentSignal，是独立的新表
- RawComment 的 like_count 和 reply_count 字段已在原表中存在
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_04_04_0001'
down_revision = None  # 设置为 None 或上一个 migration 的 revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 comment_signal_candidates 表
    op.create_table(
        'comment_signal_candidates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('source_comment_id', sa.Integer(), nullable=False),
        sa.Column('signal_type', sa.String(length=20), nullable=False),
        sa.Column('target_type', sa.String(length=20), nullable=True),
        sa.Column('target_name', sa.String(length=200), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('evidence_span', sa.Text(), nullable=True),
        sa.Column('signal_level', sa.String(length=20), nullable=True),
        sa.Column('is_llm_generated', sa.Boolean(), nullable=True),
        sa.Column('is_fallback', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['source_comment_id'], ['raw_comments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_comment_signal_candidates_project_id', 'comment_signal_candidates', ['project_id'])
    op.create_index('ix_comment_signal_candidates_source_comment_id', 'comment_signal_candidates', ['source_comment_id'])
    op.create_index('ix_comment_signal_candidates_signal_type', 'comment_signal_candidates', ['signal_type'])
    op.create_index('ix_comment_signal_candidates_target_type', 'comment_signal_candidates', ['target_type'])
    op.create_index('ix_comment_signal_candidates_signal_level', 'comment_signal_candidates', ['signal_level'])
    op.create_index('ix_comment_signal_candidates_created_at', 'comment_signal_candidates', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_comment_signal_candidates_created_at', table_name='comment_signal_candidates')
    op.drop_index('ix_comment_signal_candidates_signal_level', table_name='comment_signal_candidates')
    op.drop_index('ix_comment_signal_candidates_target_type', table_name='comment_signal_candidates')
    op.drop_index('ix_comment_signal_candidates_signal_type', table_name='comment_signal_candidates')
    op.drop_index('ix_comment_signal_candidates_source_comment_id', table_name='comment_signal_candidates')
    op.drop_index('ix_comment_signal_candidates_project_id', table_name='comment_signal_candidates')
    op.drop_table('comment_signal_candidates')
