import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import ProjectListPage from './pages/ProjectListPage'
import WorkspacePage from './pages/WorkspacePage'
import MemoryPage from './pages/MemoryPage'
import PublishPage from './pages/PublishPage'
import AgentPromptsPage from './pages/AgentPromptsPage'
import ArcPage from './pages/ArcPage'
import AudienceFeedbackPage from './pages/AudienceFeedbackPage'
import OrchestratorPage from './pages/OrchestratorPage'
import PlatformAccountsPage from './pages/PlatformAccountsPage'
import Header from './components/Header'

const { Content } = Layout

function App() {
  return (
    <BrowserRouter>
      <Layout className="layout" style={{ minHeight: '100vh' }}>
        <Header />
        <Content style={{ padding: '0 50px', marginTop: 64 }}>
          <div className="site-layout-content">
            <Routes>
              <Route path="/" element={<Navigate to="/projects" replace />} />
              <Route path="/projects" element={<ProjectListPage />} />
              <Route path="/projects/:projectId" element={<WorkspacePage />} />
              <Route path="/projects/:projectId/memory" element={<MemoryPage />} />
              <Route path="/projects/:projectId/publish" element={<PublishPage />} />
              <Route path="/projects/:projectId/arc" element={<ArcPage />} />
              <Route path="/projects/:projectId/feedback" element={<AudienceFeedbackPage />} />
              <Route path="/projects/:projectId/orchestrator" element={<OrchestratorPage />} />
              <Route path="/projects/:projectId/platforms" element={<PlatformAccountsPage />} />
              <Route path="/settings/prompts" element={<AgentPromptsPage />} />
            </Routes>
          </div>
        </Content>
      </Layout>
    </BrowserRouter>
  )
}

export default App
