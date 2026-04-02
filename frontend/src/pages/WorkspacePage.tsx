import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Button, Card, Space, Spin, message, Modal, Form, Input, Select, Collapse, Typography, Tag } from 'antd'
import { PlusOutlined, EditOutlined, BookOutlined, TeamOutlined } from '@ant-design/icons'
import { projectApi, chapterApi, memoryApi } from '../api'
import { useProjectStore } from '../store/projectStore'

const { Sider, Content } = Layout
const { Panel } = Collapse
const { Text } = Typography

// 角色类型映射
const roleLabels: Record<string, string> = {
  protagonist: '主角',
  supporting: '配角',
  antagonist: '反派',
  minor: '路人'
}

const WorkspacePage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setCurrentProject } = useProjectStore()
  const [loading, setLoading] = useState(true)
  const [chapters, setChapters] = useState<any[]>([])
  const [storyBible, setStoryBible] = useState<any>(null)
  const [characters, setCharacters] = useState<any[]>([])
  const [selectedChapter, setSelectedChapter] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'content' | 'outline' | 'summary'>('content')
  
  const [createCharModalOpen, setCreateCharModalOpen] = useState(false)
  const [createCharForm] = Form.useForm()
  const [createCharLoading, setCreateCharLoading] = useState(false)
  
  const [editBibleModalOpen, setEditBibleModalOpen] = useState(false)
  const [editBibleForm] = Form.useForm()
  const [editBibleLoading, setEditBibleLoading] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadProject()
      loadChapters()
      loadStoryBible()
      loadCharacters()
    }
  }, [projectId])

  const loadProject = async () => {
    try {
      const res = await projectApi.get(Number(projectId))
      setCurrentProject(res.data)
    } catch (err) {
      message.error('加载项目失败')
    }
  }

  const loadStoryBible = async () => {
    try {
      const res = await memoryApi.getStoryBible(Number(projectId))
      setStoryBible(res.data)
    } catch (err) {
      console.error('加载故事设定失败', err)
    }
  }

  const loadCharacters = async () => {
    try {
      const res = await memoryApi.getCharacters(Number(projectId))
      setCharacters(res.data)
    } catch (err) {
      console.error('加载角色失败', err)
    }
  }

  const loadChapters = async () => {
    try {
      setLoading(true)
      const res = await chapterApi.list(Number(projectId))
      setChapters(res.data)
    } catch (err) {
      message.error('加载章节失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateChapter = async (chapterId: number) => {
    try {
      await chapterApi.generate(Number(projectId), chapterId)
      message.success('章节生成完成')
      loadChapters()
    } catch (err) {
      message.error('生成失败')
    }
  }

  const handleReviewChapter = async (chapterId: number) => {
    try {
      const res = await chapterApi.review(Number(projectId), chapterId)
      message.success(`审查完成，评分: ${res.data.scores?.overall || res.data.verdict?.score || 'N/A'}`)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '审查失败，请重试')
    }
  }

  const handleCreateCharacter = async (values: any) => {
    try {
      setCreateCharLoading(true)
      await memoryApi.createCharacter(Number(projectId), values)
      message.success('角色创建成功')
      setCreateCharModalOpen(false)
      createCharForm.resetFields()
      loadCharacters()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '创建角色失败')
    } finally {
      setCreateCharLoading(false)
    }
  }

  const handleEditBible = () => {
    editBibleForm.setFieldsValue({
      title: storyBible?.title || '',
      genre: storyBible?.genre || '',
      theme: storyBible?.theme || '',
      logline: storyBible?.logline || '',
      synopsis: storyBible?.synopsis || '',
      tone: storyBible?.tone || '',
    })
    setEditBibleModalOpen(true)
  }

  const handleUpdateBible = async (values: any) => {
    try {
      setEditBibleLoading(true)
      await memoryApi.updateStoryBible(Number(projectId), values)
      message.success('故事设定更新成功')
      setEditBibleModalOpen(false)
      loadStoryBible()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '更新失败')
    } finally {
      setEditBibleLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      outline: 'default',
      draft: 'processing',
      writing: 'blue',
      reviewing: 'orange',
      approved: 'success',
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      outline: '大纲',
      draft: '草稿',
      writing: '写作中',
      reviewing: '审查中',
      approved: '已完成',
    }
    return labels[status] || status
  }

  // 获取角色类型中文标签
  const getRoleLabel = (roleType: string) => {
    return roleLabels[roleType] || roleType || '未知'
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      {/* 顶部导航 */}
      <Layout.Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Space>
          <BookOutlined style={{ fontSize: 24, color: '#fff' }} />
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>{currentProject?.title || '项目'}</span>
          {currentProject?.genre && <Tag color="blue">{currentProject.genre}</Tag>}
        </Space>
        <Space>
          <Button type="primary" onClick={() => navigate(`/projects/${projectId}/memory`)}>记忆库</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/publish`)}>发布</Button>
        </Space>
      </Layout.Header>

      <Layout>
        <Sider 
          width={300} 
          style={{ background: '#fff', borderRight: '1px solid #e8e8e8', overflow: 'auto' }}
        >
          <Collapse defaultActiveKey={['chapters', 'story', 'characters']} ghost>
            {/* 章节列表 */}
            <Panel 
              header={<span><BookOutlined /> 章节 ({chapters.length})</span>} 
              key="chapters"
            >
              {chapters.length > 0 ? chapters.map((chapter) => (
                <Card 
                  key={chapter.id}
                  size="small"
                  hoverable
                  onClick={() => setSelectedChapter(chapter)}
                  style={{ 
                    marginBottom: 8, 
                    cursor: 'pointer',
                    borderColor: selectedChapter?.id === chapter.id ? '#1890ff' : '#f0f0f0',
                    background: selectedChapter?.id === chapter.id ? '#e6f7ff' : '#fff'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Text strong style={{ fontSize: 14 }}>
                        第{chapter.chapter_no}章
                      </Text>
                      <div style={{ marginTop: 2 }}>
                        <Tag color={getStatusColor(chapter.status)} style={{ fontSize: 10 }}>
                          {getStatusLabel(chapter.status)}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>
                          {chapter.word_count || 0}字
                        </Text>
                      </div>
                    </div>
                    <Space size={4}>
                      <Button size="small" type="primary" onClick={(e) => { e.stopPropagation(); handleGenerateChapter(chapter.id) }}>生成</Button>
                      <Button size="small" onClick={(e) => { e.stopPropagation(); handleReviewChapter(chapter.id) }}>审查</Button>
                    </Space>
                  </div>
                </Card>
              )) : (
                <Text type="secondary" style={{ padding: '8px 0' }}>暂无章节，请先规划章节</Text>
              )}
            </Panel>
            
            {/* 故事设定 */}
            <Panel 
              header={<span><BookOutlined /> 故事设定</span>} 
              key="story"
              extra={<Button type="link" size="small" icon={<EditOutlined />} onClick={handleEditBible}>编辑</Button>}
            >
              {storyBible ? (
                <div>
                  <div style={{ marginBottom: 8 }}><Text strong>类型：</Text>{storyBible.genre || '待填充'}</div>
                  <div style={{ marginBottom: 8 }}><Text strong>主题：</Text>{storyBible.theme || '待填充'}</div>
                  <div style={{ marginBottom: 8 }}><Text strong>基调：</Text>{storyBible.tone || '待填充'}</div>
                  <div style={{ marginBottom: 8 }}><Text strong>目标读者：</Text>{storyBible.target_audience || '待填充'}</div>
                  {storyBible.synopsis ? (
                    <div>
                      <Text strong>概述：</Text>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {storyBible.synopsis.slice(0, 100)}...
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <Text type="secondary">暂无故事设定</Text>
              )}
            </Panel>
            
            {/* 角色 */}
            <Panel 
              header={<span><TeamOutlined /> 角色 ({characters.length})</span>}
              key="characters"
              extra={
                <Button type="link" size="small" icon={<PlusOutlined />} onClick={() => setCreateCharModalOpen(true)}>
                  新建
                </Button>
              }
            >
              {characters.length > 0 ? characters.map((char: any) => (
                <Card key={char.id} size="small" style={{ marginBottom: 8 }}>
                  <Text strong>{char.name}</Text>
                  <Tag color={char.role_type === 'protagonist' ? 'blue' : 'default'} style={{ marginLeft: 8, fontSize: 10 }}>
                    {getRoleLabel(char.role_type)}
                  </Tag>
                  {char.profile && (
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      {char.profile.slice(0, 50)}...
                    </div>
                  )}
                </Card>
              )) : (
                <Text type="secondary">暂无角色</Text>
              )}
            </Panel>
          </Collapse>
        </Sider>

        <Content style={{ padding: 24, overflow: 'auto' }}>
          {selectedChapter ? (
            <Card 
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <Text strong style={{ fontSize: 16 }}>第{selectedChapter.chapter_no}章</Text>
                    <Tag color={getStatusColor(selectedChapter.status)}>
                      {getStatusLabel(selectedChapter.status)}
                    </Tag>
                    <Text type="secondary">{selectedChapter.word_count || 0} 字</Text>
                  </Space>
                  <Space>
                    <Button type={activeTab === 'content' ? 'primary' : 'default'} onClick={() => setActiveTab('content')}>
                      正文
                    </Button>
                    <Button type={activeTab === 'outline' ? 'primary' : 'default'} onClick={() => setActiveTab('outline')}>
                      大纲
                    </Button>
                    <Button type={activeTab === 'summary' ? 'primary' : 'default'} onClick={() => setActiveTab('summary')}>
                      摘要
                    </Button>
                  </Space>
                </div>
              }
              style={{ height: 'calc(100vh - 140px)' }}
              bodyStyle={{ height: 'calc(100% - 60px)', overflow: 'auto', padding: 24 }}
            >
              {activeTab === 'content' && (
                <div style={{ 
                  whiteSpace: 'pre-wrap', 
                  lineHeight: 2, 
                  fontSize: 16,
                  letterSpacing: '0.5px'
                }}>
                  {selectedChapter.text || '暂无正文，点击"生成"按钮开始创作'}
                </div>
              )}
              {activeTab === 'outline' && (
                <div style={{ 
                  whiteSpace: 'pre-wrap', 
                  lineHeight: 1.8,
                  background: '#fafafa',
                  padding: 20,
                  borderRadius: 8,
                  fontSize: 14
                }}>
                  {selectedChapter.outline || '暂无大纲'}
                </div>
              )}
              {activeTab === 'summary' && (
                <div style={{ 
                  whiteSpace: 'pre-wrap', 
                  lineHeight: 1.8,
                  background: '#fafafa',
                  padding: 20,
                  borderRadius: 8,
                  fontSize: 14
                }}>
                  {selectedChapter.summary || '暂无摘要'}
                </div>
              )}
            </Card>
          ) : (
            <div style={{ textAlign: 'center', padding: 100, background: '#fff', borderRadius: 8 }}>
              <BookOutlined style={{ fontSize: 64, color: '#ccc' }} />
              <div style={{ marginTop: 16, fontSize: 18, color: '#999' }}>
                <p>从左侧选择章节开始阅读</p>
                <p style={{ fontSize: 14, color: '#ccc' }}>点击章节卡片查看正文</p>
              </div>
            </div>
          )}
        </Content>
      </Layout>

      {/* 新建角色弹窗 */}
      <Modal
        title="新建角色"
        open={createCharModalOpen}
        onCancel={() => { setCreateCharModalOpen(false); createCharForm.resetFields() }}
        footer={null}
        destroyOnClose
      >
        <Form form={createCharForm} layout="vertical" onFinish={handleCreateCharacter}>
          <Form.Item name="name" label="角色名称" rules={[{ required: true, message: '请输入角色名称' }]}>
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item name="role_type" label="角色类型" initialValue="supporting">
            <Select>
              <Select.Option value="protagonist">主角</Select.Option>
              <Select.Option value="supporting">配角</Select.Option>
              <Select.Option value="antagonist">反派</Select.Option>
              <Select.Option value="minor">路人</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="profile" label="角色简介">
            <Input.TextArea rows={3} placeholder="请输入角色简介" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setCreateCharModalOpen(false); createCharForm.resetFields() }}>取消</Button>
              <Button type="primary" htmlType="submit" loading={createCharLoading}>创建</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑故事设定弹窗 */}
      <Modal
        title="编辑故事设定"
        open={editBibleModalOpen}
        onCancel={() => setEditBibleModalOpen(false)}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form form={editBibleForm} layout="vertical" onFinish={handleUpdateBible}>
          <Form.Item name="title" label="标题">
            <Input placeholder="请输入故事标题" />
          </Form.Item>
          <Form.Item name="genre" label="类型">
            <Input placeholder="如：都市异能、玄幻、悬疑等" />
          </Form.Item>
          <Form.Item name="theme" label="主题">
            <Input.TextArea rows={2} placeholder="请输入故事主题" />
          </Form.Item>
          <Form.Item name="tone" label="基调">
            <Input.TextArea rows={2} placeholder="请输入故事基调" />
          </Form.Item>
          <Form.Item name="synopsis" label="详细概述">
            <Input.TextArea rows={4} placeholder="请输入故事详细概述" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setEditBibleModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={editBibleLoading}>保存</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

export default WorkspacePage
