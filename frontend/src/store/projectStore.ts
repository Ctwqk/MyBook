import { create } from 'zustand'

interface Project {
  id: number
  title: string
  genre?: string
  style?: string
  premise?: string
  status: string
  created_at: string
  updated_at: string
}

interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  error: string | null
  
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  addProject: (project: Project) => void
  updateProject: (id: number, updates: Partial<Project>) => void
  removeProject: (id: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,
  
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
  addProject: (project) => set((state) => ({ projects: [...state.projects, project] })),
  updateProject: (id, updates) => set((state) => ({
    projects: state.projects.map((p) => p.id === id ? { ...p, ...updates } : p),
    currentProject: state.currentProject?.id === id ? { ...state.currentProject, ...updates } : state.currentProject,
  })),
  removeProject: (id) => set((state) => ({
    projects: state.projects.filter((p) => p.id !== id),
    currentProject: state.currentProject?.id === id ? null : state.currentProject,
  })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))
