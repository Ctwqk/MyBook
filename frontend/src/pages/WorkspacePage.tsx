import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Button, Card, List, Space, Spin, message, Modal, Form, Input, Select, Divider, Collapse, Typography, Tag } from 'antd'
import { PlusOutlined, EditOutlined, MenuFoldOutlined, MenuUnfoldOutlined, BookOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons'
import { projectApi, chapterApi, memoryApi } from '../api'
import { useProjectStore } from '../store/projectStore'

const { Sider, Content } = Layout
const { Panel } = Collapse
const { Text } = Typography

const WorkspacePage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setCurrentProject } = useProjectStore()
  const [loading, setLoading] = useState(true)
  const [chapters, setChapters] = useState<any[]>([])
  const [storyBible, setStoryBible] = useState<any>(null)
  const [characters, setCharacters] = useState<any[]>([])
  const [selectedChapter, setSelectedChapter] = useState<any>(null)
  const [chapterSidebarCollapsed, setChapterSidebarCollapsed] = useState(false)
  const [rightSidebarTab, setRightSidebarTab] = useState<'outline' | 'content' | 'summary'>('content')
  
  // 新建角色弹窗
  const [createCharModalOpen, setCreateCharModalOpen] = useState(false)
  const [createCharForm] = Form.useForm()
  const [createCharLoading, setCreateCharLoading] = useState(false)
  
  // 编辑故事设定弹窗
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
      message.info(`审查完成，评分: ${res.data.verdict.score}`)
    } catch (err) {
      message.error('审查失败')
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

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 顶部导航栏 */}
      <Layout.Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <BookOutlined style={{ fontSize: 24, color: '#fff' }} />
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>{currentProject?.title || '项目'}</span>
          <Tag color={currentProject?.genre === '科幻' ? 'blue' : 'green'}>{currentProject?.genre || '未分类'}</Tag>
        </div>
        <Space>
          <Button type="primary" onClick={() => navigate(`/projects/${projectId}/memory`)}>记忆库</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/publish`)}>发布</Button>
        </Space>
      </Layout.Header>

      <Layout.Content style={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
        {/* 左侧章节列表 - 可折叠 */}
        <Sider 
          width={320} 
          collapsedWidth={0}
          collapsed={chapterSidebarCollapsed}
          style={{ 
            background: '#fff', 
            borderRight: '1px solid #e8e8e8',
            overflow: 'auto'
          }}
        >
          <div style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Text strong style={{ fontSize: 16 }}>📖 章节列表</Text>
              <Button 
                type="text" 
                icon={<MenuFoldOutlined />} 
                onClick={() => setChapterSidebarCollapsed(true)}
              />
            </div>
            
            <List
              dataSource={chapters}
              renderItem={(chapter) => (
                <Card 
                  size="small" 
                  hoverable
                  onClick={() => setSelectedChapter(chapter)}
                  style={{ 
                    marginBottom: 8, 
                    cursor: 'pointer',
                    borderColor: selectedChapter?.id === chapter.id ? '#1890ff' : '#e8e8e8',
                    background: selectedChapter?.id === chapter.id ? '#e6f7ff' : '#fff'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <Text strong style={{ fontSize: 14 }}>
                        第{chapter.chapter_no}章: {chapter.title?.replace(/^章节\d+：/, '') || '无标题'}
                      </Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color={getStatusColor(chapter.status)} style={{ marginRight: 4 }}>
                          {chapter.status === 'outline' ? '大纲' : chapter.status === 'draft' ? '草稿' : chapter.status}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {chapter.word_count || 0} 字
                        </Text>
                      </div>
                      {chapter.outline && (
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {chapter.outline.slice(0, 60)}...
                          </Text>
                        </div>
                      )}
                    </div>
                  </div>
                  <Space style={{ marginTop: 8 }}>
                    <Button size="small" type="primary" onClick={(e) => { e.stopPropagation(); handleGenerateChapter(chapter.id) }}>
                      生成
                    </Button>
                    <Button size="small" onClick={(e) => { e.stopPropagation(); handleReviewChapter(chapter.id) }}>
                      审查
                    </Button>
                  </Space>
                </Card>
              )}
              locale={{ emptyText: '暂无章节' }}
            />
          </div>
        </Sider>

        {/* 主内容区 */}
        <Content style={{ flex: 1, padding: 24, overflow: 'auto' }}>
          {selectedChapter ? (
            <div style={{ display: 'flex', gap: 24, height: '100%' }}>
              {/* 左侧：章节信息 */}
              <div style={{ width: 320, flexShrink: 0 }}>
                <Card 
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>📋 章节信息</span>
                      {!chapterSidebarCollapsed && (
                        <Button 
                          type="text" 
                          icon={<MenuUnfoldOutlined />} 
                          onClick={() => setChapterSidebarCollapsed(false)}
                        />
                      )}
                    </div>
                  }
                >
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>标题：</Text>
                    <div>{selectedChapter.title || `第${selectedChapter.chapter_no}章`}</div>
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>状态：</Text>
                    <Tag color={getStatusColor(selectedChapter.status)} style={{ marginLeft: 8 }}>
                      {selectedChapter.status}
                    </Tag>
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>字数：</Text>
                    <span style={{ marginLeft: 8 }}>{selectedChapter.word_count || 0}</span>
                  </div>
                  
                  <Divider>大纲</Divider>
                  <div style={{ 
                    background: '#fafafa', 
                    padding: 12, 
                    borderRadius: 4,
                    maxHeight: 200,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    fontSize: 13,
                    lineHeight: 1.6
                  }}>
                    {selectedChapter.outline || '暂无大纲'}
                  </div>
                </Card>
              </div>

              {/* 右侧：正文 */}
              <div style={{ flex: 1 }}>
                <Card 
                  title={
                    <div style={{ display: 'flex', gap: 16 }}>
                      <Button 
                        type={rightSidebarTab === 'content' ? 'primary' : 'default'}
                        onClick={() => setRightSidebarTab('content')}
                      >
                        📝 正文
                      </Button>
                      <Button 
                        type={rightSidebarTab === 'summary' ? 'primary' : 'default'}
                        onClick={() => setRightSidebarTab('summary')}
                      >
                        📌 摘要
                      </Button>
                      <Button 
                        type={rightSidebarTab === 'outline' ? 'primary' : 'default'}
                        onClick={() => setRightSidebarTab('outline')}
                      >
                        📋 大纲
                      </Button>
                    </div>
                  }
                  style={{ height: '100%' }}
                  bodyStyle={{ height: 'calc(100% - 60px)', overflow: 'auto' }}
                >
                  {rightSidebarTab === 'content' && (
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      lineHeight: 1.8, 
                      fontSize: 15,
                      padding: '0 8px'
                    }}>
                      {selectedChapter.text || '暂无正文，点击"生成"按钮开始创作'}
                    </div>
                  )}
                  {rightSidebarTab === 'summary' && (
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      lineHeight: 1.8,
                      background: '#fafafa',
                      padding: 16,
                      borderRadius: 4
                    }}>
                      {selectedChapter.summary || '暂无摘要'}
                    </div>
                  )}
                  {rightSidebarTab === 'outline' && (
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      lineHeight: 1.8,
                      background: '#fafafa',
                      padding: 16,
                      borderRadius: 4
                    }}>
                      {selectedChapter.outline || '暂无大纲'}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 100, background: '#fff', borderRadius: 8 }}>
              <FileTextOutlined style={{ fontSize: 64, color: '#ccc' }} />
              <div style={{ marginTop: 16, fontSize: 18, color: '#999' }}>
                {chapterSidebarCollapsed ? (
                  <Button type="primary" icon={<MenuUnfoldOutlined />} onClick={() => setChapterSidebarCollapsed(false)}>
                    打开章节列表
                  </Button>
                ) : (
                  <>
                    <p>从左侧选择一个章节开始</p>
                    <p style={{ fontSize: 14, color: '#ccc' }}>点击章节卡片查看和编辑</p>
                  </>
                )}
              </div>
            </div>
          )}
        </Content>

        {/* 右侧边栏：故事设定 */}
        <Sider width={280} style={{ background: '#fff', borderLeft: '1px solid #e8e8e8', overflow: 'auto' }}>
          <Collapse defaultActiveKey={['story', 'characters']} ghost>
            <Panel 
              header={<span><BookOutlined /> 故事设定</span>} 
              key="story"
              extra={<Button type="link" size="small" icon={<EditOutlined />} onClick={handleEditBible}>编辑</Button>}
            >
              {storyBible ? (
                <div>
                  <div style={{ marginBottom: 8 }}><Text strong>类型：</Text>{storyBible.genre}</div>
                  <div style={{ marginBottom: 8 }}><Text strong>主题：</Text>{storyBible.theme || '待填充'}</div>
                  <div style={{ marginBottom: 8 }}><Text strong>基调：</Text>{storyBible.tone || '待填充'}</div>
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>概述：</Text>
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      {storyBible.synopsis?.slice(0, 150) || '待填充'}...
                    </div>
                  </div>
                </div>
              ) : (
                <Text type="secondary">暂无故事设定</Text>
              )}
            </Panel>
            
            <Panel 
              header={<span><TeamOutlined /> 角色 ({characters.length})</span>}
              key="characters"
              extra={
                <Button type="link" size="small" icon={<PlusOutlined />} onClick={() => setCreateCharModalOpen(true)}>
                  新建
                </Button>
              }
            >
              {characters.length > 0 ? (
                characters.map((char: any) => (
                  <Card key={char.id} size="small" style={{ marginBottom: 8 }}>
                    <Text strong>{char.name}</Text>
                    <Tag color={char.role_type === 'protagonist' ? 'blue' : 'default'} style={{ marginLeft: 8, fontSize: 10 }}>
                      {char.role_type === 'protagonist' ? '主角' : char.role_type}
                    </Tag>
                    {char.profile && (
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {char.profile.slice(0, 50)}...
                      </div>
                    )}
                  </Card>
                ))
              ) : (
                <Text type="secondary">暂无角色</Text>
              )}
            </Panel>
          </Collapse>
        </Sider>
      </Layout.Content>

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
          <Form.Item name="personality" label="性格特点">
            <Input.TextArea rows={2} placeholder="请输入性格特点" />
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
          <Divider>基本信息</Divider>
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
          <Divider>故事概述</Divider>
          <Form.Item name="logline" label="一句话简介">
            <Input.TextArea rows={2} placeholder="用一句话概括整个故事" />
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
