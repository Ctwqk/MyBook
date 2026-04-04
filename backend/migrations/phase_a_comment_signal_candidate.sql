-- Phase A: Add CommentSignalCandidate table (v2.6)
-- 此文件为备选方案，如 alembic 迁移失败可手动执行

-- ============================================
-- CommentSignalCandidate 表
-- 存储 LLM 解析后的结构化信号候选
-- ============================================

CREATE TABLE IF NOT EXISTS comment_signal_candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    source_comment_id INT NOT NULL,
    signal_type VARCHAR(20) NOT NULL COMMENT 'confusion/pacing/character_heat/risk',
    target_type VARCHAR(20) NULL COMMENT 'character/arc/plot/setting',
    target_name VARCHAR(200) NULL COMMENT '自由文本，如"主角动机"',
    severity INT DEFAULT 1 COMMENT '1~4',
    confidence FLOAT DEFAULT 0.5 COMMENT '0~1',
    evidence_span TEXT NULL COMMENT '原文摘录',
    signal_level VARCHAR(20) DEFAULT 'candidate' COMMENT 'noise/candidate/confirmed/watchlist',
    is_llm_generated BOOLEAN DEFAULT TRUE COMMENT 'True=LLM生成, False=关键词匹配fallback',
    is_fallback BOOLEAN DEFAULT FALSE COMMENT '是否是 fallback 到关键词的结果',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (source_comment_id) REFERENCES raw_comments(id)
);

-- 索引
CREATE INDEX ix_csc_project_id ON comment_signal_candidates(project_id);
CREATE INDEX ix_csc_source_comment_id ON comment_signal_candidates(source_comment_id);
CREATE INDEX ix_csc_signal_type ON comment_signal_candidates(signal_type);
CREATE INDEX ix_csc_target_type ON comment_signal_candidates(target_type);
CREATE INDEX ix_csc_signal_level ON comment_signal_candidates(signal_level);
CREATE INDEX ix_csc_created_at ON comment_signal_candidates(created_at);

-- 回滚
-- DROP TABLE IF EXISTS comment_signal_candidates;
