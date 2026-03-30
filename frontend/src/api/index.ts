import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 项目 API
export const projectApi = {
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: { title: string; genre?: string; style?: string; premise?: string }) =>
    api.post('/projects', data),
  update: (id: number, data: any) => api.patch(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  bootstrap: (id: number) => api.post(`/projects/${id}/bootstrap`),
  planArcs: (id: number, params?: { total_arcs?: number; target_chapters_per_arc?: number }) =>
    api.post(`/projects/${id}/arcs/plan`, null, { params }),
  planChapters: (id: number, params?: { volume_id?: number; chapter_count?: number }) =>
    api.post(`/projects/${id}/chapters/plan`, null, { params }),
}

// 章节 API
export const chapterApi = {
  list: (projectId: number, params?: { volume_id?: number; skip?: number; limit?: number }) =>
    api.get(`/projects/${projectId}/chapters`, { params }),
  get: (projectId: number, chapterId: number) =>
    api.get(`/projects/${projectId}/chapters/${chapterId}`),
  create: (projectId: number, data: { chapter_no?: number; title?: string; outline?: string }) =>
    api.post(`/projects/${projectId}/chapters`, data),
  update: (projectId: number, chapterId: number, data: any) =>
    api.patch(`/projects/${projectId}/chapters/${chapterId}`, data),
  generate: (projectId: number, chapterId: number, data?: { outline?: string; style_hints?: string }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/generate`, data),
  continue: (projectId: number, chapterId: number, data: { target_word_count?: number }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/continue`, data),
  rewrite: (projectId: number, chapterId: number, data: { rewrite_instructions: string }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/rewrite`, data),
  patch: (projectId: number, chapterId: number, data: { segment_id: string; segment_content: string; patch_instructions: string }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/patch`, data),
  review: (projectId: number, chapterId: number, data?: { check_types?: string[] }) =>
    api.post(`/projects/${projectId}/chapters/${chapterId}/review`, data),
}

// 记忆 API
export const memoryApi = {
  getStoryBible: (projectId: number) => api.get(`/projects/${projectId}/memory/story-bible`),
  updateStoryBible: (projectId: number, data: any) =>
    api.patch(`/projects/${projectId}/memory/story-bible`, data),
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
  getCharacterStates: (projectId: number, characterId?: number) =>
    api.get(`/projects/${projectId}/memory/characters/state`, { params: { character_id: characterId } }),
  buildContextPack: (projectId: number, data: {
    chapter_id?: number;
    include_story_bible?: boolean;
    include_character_states?: boolean;
    include_recent_chapters?: number;
    include_foreshadows?: boolean;
  }) => api.post(`/projects/${projectId}/memory/context-pack`, data),
  search: (projectId: number, params: { query: string; search_type?: string; limit?: number }) =>
    api.get(`/projects/${projectId}/memory/search`, { params }),
  getForeshadows: (projectId: number) =>
    api.get(`/projects/${projectId}/memory/foreshadow`),
  recordForeshadow: (projectId: number, data: { chapter_id: number; content: string; related_entities?: string[] }) =>
    api.post(`/projects/${projectId}/memory/foreshadow`, data),
}

// 发布 API
export const publishApi = {
  registerSession: (data: { platform: string; session_token: string }) =>
    api.post('/platform/accounts/register-session', data),
  bindBook: (data: { platform: string; account_id: string; remote_book_id: string; book_title: string }) =>
    api.post('/platform/books/bind', data),
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
}

export default api
