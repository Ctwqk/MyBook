import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ==================== 项目 API ====================
export const projectApi = {
  // 基础CRUD
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: { title: string; genre?: string; style?: string; premise?: string }) =>
    api.post('/projects', data),
  update: (id: number, data: any) => api.patch(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  
  // 项目引导
  bootstrap: (id: number) => api.post(`/projects/${id}/bootstrap`),
  
  // 规划
  planArcs: (id: number, params?: { total_arcs?: number; target_chapters_per_arc?: number }) =>
    api.post(`/projects/${id}/arcs/plan`, null, { params }),
  planChapters: (id: number, params?: { volume_id?: number; chapter_count?: number }) =>
    api.post(`/projects/${id}/chapters/plan`, null, { params }),
  
  // 修订大纲
  reviseOutline: (projectId: number, outlineId: number, notes: string) =>
    api.post(`/projects/${projectId}/outlines/${outlineId}/revise`, { notes }),
}

// ==================== 章节 API ====================
export const chapterApi = {
  // 基础CRUD
  list: (projectId: number, params?: { volume_id?: number; skip?: number; limit?: number }) =>
    api.get(`/projects/${projectId}/chapters`, { params }),
  get: (projectId: number, chapterId: number) =>
    api.get(`/projects/${projectId}/chapters/${chapterId}`),
  create: (projectId: number, data: { chapter_no?: number; title?: string; outline?: string }) =>
    api.post(`/projects/${projectId}/chapters`, data),
  update: (projectId: number, chapterId: number, data: any) =>
    api.patch(`/projects/${projectId}/chapters/${chapterId}`, data),
  
  // 章节生成
  generate: (projectId: number, chapterId: number, data?: { outline?: string; style_hints?: string }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/generate`, data),
  
  // 续写/重写/修补
  continue: (projectId: number, chapterId: number, data: { target_word_count?: number }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/continue`, data),
  rewrite: (projectId: number, chapterId: number, data: { rewrite_instructions: string }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/rewrite`, data),
  patch: (projectId: number, chapterId: number, data: { 
    segment_id: string; 
    segment_content?: string; 
    patch_instructions: string 
  }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/patch`, data),
  
  // 审查
  review: (projectId: number, chapterId: number, data?: { check_types?: string[] }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/review`, data),
  reviewPartial: (projectId: number, chapterId: number, data: { 
    start_line?: number; 
    end_line?: number; 
    focus_areas?: string[] 
  }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/review/partial`, data),
}

// ==================== 记忆 API ====================
export const memoryApi = {
  // 故事设定
  getStoryBible: (projectId: number) => api.get(`/projects/${projectId}/memory/story-bible`),
  updateStoryBible: (projectId: number, data: any) =>
    api.patch(`/projects/${projectId}/memory/story-bible`, data),
  
  // 角色管理
  getCharacters: (projectId: number) =>
    api.get(`/projects/${projectId}/memory/characters`),
  createCharacter: (projectId: number, data: {
    name: string;
    role_type?: string;
    profile?: string;
    personality?: string;
    motivation?: string;
    secrets?: string;
  }) => api.post(`/projects/${projectId}/memory/characters`, data),
  updateCharacter: (projectId: number, characterId: number, data: any) =>
    api.patch(`/projects/${projectId}/memory/characters/${characterId}`, data),
  deleteCharacter: (projectId: number, characterId: number) =>
    api.delete(`/projects/${projectId}/memory/characters/${characterId}`),
  
  // 角色状态
  getCharacterStates: (projectId: number, characterId?: number) =>
    api.get(`/projects/${projectId}/memory/characters/state`, { params: { character_id: characterId } }),
  updateCharacterState: (projectId: number, characterId: number, data: {
    chapter_id?: number;
    location?: string;
    emotional_state?: string;
    physical_state?: string;
    relationships?: any;
  }) => api.patch(`/projects/${projectId}/memory/characters/${characterId}/state`, data),
  
  // 上下文包
  buildContextPack: (projectId: number, data: {
    chapter_id?: number;
    include_story_bible?: boolean;
    include_character_states?: boolean;
    include_recent_chapters?: number;
    include_foreshadows?: boolean;
  }) => api.post(`/projects/${projectId}/memory/context-pack`, data),
  
  // 搜索
  search: (projectId: number, params: { query: string; search_type?: string; limit?: number }) =>
    api.get(`/projects/${projectId}/memory/search`, { params }),
  
  // 伏笔
  getForeshadows: (projectId: number) =>
    api.get(`/projects/${projectId}/memory/foreshadow`),
  recordForeshadow: (projectId: number, data: { chapter_id: number; content: string; related_entities?: string[] }) =>
    api.post(`/projects/${projectId}/memory/foreshadow`, data),
  
  // 审查笔记
  getReviewNotes: (projectId: number, params?: { chapter_id?: number }) =>
    api.get(`/projects/${projectId}/memory/review-notes`, { params }),
  createReviewNote: (projectId: number, data: {
    chapter_id: number;
    note_type: string;
    content: string;
    severity?: string;
  }) => api.post(`/projects/${projectId}/memory/review-notes`, data),
}

// ==================== Arc管理 API ====================
export const arcApi = {
  // 获取项目分档
  getProjectTier: (projectId: number) =>
    api.get(`/arc-envelopes/project/${projectId}/tier`),
  
  // 预览Arc
  previewArcs: (projectId: number, params?: { total_chapters?: number }) =>
    api.get(`/arc-envelopes/project/${projectId}/preview`, { params }),
  
  // 获取项目所有Arc
  getProjectArcs: (projectId: number) =>
    api.get(`/arc-envelopes/project/${projectId}`),
  
  // 获取单个Arc
  getArc: (projectId: number, arcNo: number) =>
    api.get(`/arc-envelopes/project/${projectId}/arc/${arcNo}`),
  
  // 激活Arc
  activateArc: (projectId: number, arcNo: number) =>
    api.post(`/arc-envelopes/project/${projectId}/activate`, { arc_no: arcNo }),
  
  // 调整Arc
  adjustArc: (projectId: number, arcNo: number, adjustment: 'expand' | 'compress' | 'keep') =>
    api.post(`/arc-envelopes/project/${projectId}/arc/${arcNo}/adjust`, { adjustment }),
}

// ==================== 发布 API ====================
export const publishApi = {
  // 平台会话
  registerSession: (data: { platform: string; session_token: string }) =>
    api.post('/platform/accounts/register-session', data),
  getAccountStatus: (platform: string, accountId: string) =>
    api.get(`/platform/accounts/${accountId}/status`, { params: { platform } }),
  
  // 书籍绑定
  bindBook: (data: { platform: string; account_id: string; remote_book_id: string; book_title: string }) =>
    api.post('/platform/books/bind', data),
  
  // 发布任务
  createDraft: (projectId: number, data: { chapter_id: number; platform: string; account_id: string }) =>
    api.post(`/projects/${projectId}/publish/draft`, data),
  submit: (projectId: number, data: { chapter_id: number; platform: string; account_id: string; remote_book_id: string }) =>
    api.post(`/projects/${projectId}/publish/submit`, data),
  listTasks: (projectId: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/projects/${projectId}/publish/tasks`, { params }),
  getTask: (projectId: number, taskId: number) =>
    api.get(`/projects/${projectId}/publish/tasks/${taskId}`),
  syncTask: (projectId: number, taskId: number, forceRefresh?: boolean) =>
    api.post(`/projects/${projectId}/publish/tasks/${taskId}/sync`, { force_refresh: forceRefresh }),
  cancelTask: (projectId: number, taskId: number) =>
    api.post(`/projects/${projectId}/publish/tasks/${taskId}/cancel`),
  
  // ========== 平台登录 API ==========
  // 获取平台列表
  getPlatforms: () =>
    api.get('/platform/platforms'),
  
  // 获取平台详情
  getPlatform: (platform: string) =>
    api.get(`/platform/platforms/${platform}`),
  
  // 二维码登录
  getQrCode: (platform: string) =>
    api.post('/platform/login/qr', { platform }),
  checkQrStatus: (sessionId: string) =>
    api.get(`/platform/login/qr/${sessionId}`),
  
  // 密码登录
  loginWithPassword: (data: { platform: string; username: string; password: string }) =>
    api.post('/platform/login/password', data),
  
  // 短信登录
  sendSmsCode: (data: { platform: string; phone: string }) =>
    api.post('/platform/login/sms/send', data),
  verifySmsCode: (data: { platform: string; phone: string; code: string }) =>
    api.post('/platform/login/sms/verify', data),
  
  // Cookie登录
  loginWithCookie: (data: { platform: string; cookies: string }) =>
    api.post('/platform/login/cookie', data),
  
  // 退出登录
  logout: (accountId: string) =>
    api.post('/platform/logout', { account_id: accountId }),
}

// ==================== 编排器 API ====================
export const orchestratorApi = {
  // 任务状态
  getTaskStatus: (taskId: string) =>
    api.get(`/orchestrator/tasks/${taskId}`),
  
  // 模式切换
  getMode: (projectId: number) =>
    api.get(`/orchestrator/mode`, { params: { project_id: projectId } }),
  setMode: (projectId: number, mode: 'supervised' | 'checkpoint' | 'blackbox') =>
    api.post(`/orchestrator/mode`, { project_id: projectId, mode }),
  
  // 待处理决策
  getPendingDecisions: (projectId: number) =>
    api.get(`/orchestrator/pending-decisions/${projectId}`),
  approveTask: (taskId: string, decision: { approved: boolean; notes?: string }) =>
    api.post(`/orchestrator/approve-task`, { task_id: taskId, decision: decision.approved ? 'proceed' : 'reject' }),
  
  // 从检查点恢复
  resumeCheckpoint: (taskId: string) =>
    api.post(`/orchestrator/checkpoint/${taskId}/resume`),
}

// ==================== 读者反馈 API ====================
export const audienceApi = {
  // 提交反馈
  submitFeedback: (projectId: number, data: {
    chapter_id?: number;
    feedback_type: string;
    content: string;
    rating?: number;
  }) => api.post(`/audience/feedback/${projectId}`, data),
  
  // 获取反馈
  getFeedback: (projectId: number, params?: { chapter_id?: number; limit?: number }) =>
    api.get(`/audience/feedback/${projectId}`, { params }),
  
  // 获取分析
  getAnalysis: (projectId: number) =>
    api.get(`/audience/analysis/${projectId}`),
  
  // 获取行为数据
  getBehaviorData: (projectId: number, params?: { start_date?: string; end_date?: string }) =>
    api.get(`/audience/behavior/${projectId}`, { params }),
  
  // 获取告警
  getAlerts: (projectId: number) =>
    api.get(`/audience/alerts/${projectId}`),
  
  // Arc Director信号
  getArcDirectorSignals: (projectId: number) =>
    api.get(`/audience/arc-director/${projectId}`),
  
  // Pacing信号
  getPacingSignals: (projectId: number) =>
    api.get(`/audience/pacing/${projectId}`),
  
  // 动作映射建议
  getActionSuggestions: (projectId: number) =>
    api.get(`/audience/actions/${projectId}`),
  
  // Writer提示包
  getHintPack: (projectId: number) =>
    api.get(`/audience/hint-pack/${projectId}`),
  
  // 分析评论
  analyzeComments: (projectId: number) =>
    api.post(`/audience/analyze/${projectId}`),
  
  // 摄入单条评论
  ingestComment: (data: {
    project_id: number;
    content: string;
    source?: string;
    chapter_no?: number;
  }) => api.post(`/audience/comments`, data),
  
  // 批量摄入评论
  ingestCommentsBatch: (comments: Array<{
    project_id: number;
    content: string;
    source?: string;
    chapter_no?: number;
  }>) => api.post(`/audience/comments/batch`, { comments }),
  
  // 获取信号
  getSignals: (projectId: number) =>
    api.get(`/audience/signals/${projectId}`),
  
  // 评论统计
  getCommentStats: (projectId: number) =>
    api.get(`/audience/comments/stats/${projectId}`),
}

export default api
