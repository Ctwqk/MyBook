import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Tabs, Button, Card, List, Space, Spin, message, Modal, Form, Input, Select, Divider } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { projectApi, chapterApi, memoryApi } from '../api'
import { useProjectStore } from '../store/projectStore'

const { Sider, Content } = Layout

const WorkspacePage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setCurrentProject } = useProjectStore()
  const [loading, setLoading] = useState(true)
  const [chapters, setChapters] = useState<any[]>([])
  const [storyBible, setStoryBible] = useState<any>(null)
  const [characters, setCharacters] = useState<any[]>([])
  const [selectedChapter, setSelectedChapter] = useState<any>(null)
  
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
      console.log('Loading story bible for project:', projectId)
      const res = await memoryApi.getStoryBible(Number(projectId))
      console.log('Story bible loaded:', res.data)
      setStoryBible(res.data)
      console.log('Story bible state set:', res.data)
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

  // 创建角色
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

  // 编辑故事设定
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

  const getStatusTag = (status: string) => {
    const colors: Record<string, string> = {
      outline: 'default',
      draft: 'processing',
      writing: 'blue',
      reviewing: 'orange',
      approved: 'success',
    }
    return <span style={{ color: colors[status] || '#999' }}>{status.toUpperCase()}</span>
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout className="workspace-layout">
      <Sider width={280} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
        <Tabs
          defaultActiveKey="story"
          items={[
            {
              key: 'story',
              label: '故事设定',
              children: (
                <div style={{ padding: 16 }}>
                  <Button 
                    type="link" 
                    icon={<EditOutlined />} 
                    onClick={handleEditBible}
                    style={{ float: 'right', padding: 0 }}
                  >
                    编辑
                  </Button>
                  <div style={{ clear: 'both' }} />
                  {storyBible ? (
                    <Card size="small">
                      {storyBible.title && <p><strong>标题:</strong> {storyBible.title}</p>}
                      {storyBible.genre && <p><strong>类型:</strong> {storyBible.genre}</p>}
                      <p><strong>主题:</strong> {storyBible.theme || '待填充'}</p>
                      <p><strong>基调:</strong> {storyBible.tone || '待填充'}</p>
                      <p><strong>概述:</strong> {storyBible.synopsis?.slice(0, 100) || '待填充'}...</p>
                    </Card>
                  ) : (
                    <p style={{ color: '#999' }}>暂无故事设定</p>
                  )}
                </div>
              ),
            },
            {
              key: 'characters',
              label: `角色 (${characters.length})`,
              children: (
                <div style={{ padding: 16 }}>
                  <Button 
                    type="primary" 
                    icon={<PlusOutlined />} 
                    onClick={() => setCreateCharModalOpen(true)}
                    style={{ marginBottom: 12, width: '100%' }}
                  >
                    新建角色
                  </Button>
                  {characters.length > 0 ? (
                    characters.map((char: any) => (
                      <Card key={char.id} size="small" style={{ marginBottom: 8 }}>
                        <p><strong>{char.name}</strong> ({char.role_type})</p>
                        {char.profile && <p style={{ fontSize: 12, color: '#666' }}>{char.profile?.slice(0, 50)}...</p>}
                      </Card>
                    ))
                  ) : (
                    <p style={{ color: '#999' }}>暂无角色</p>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Sider>

      <Content className="workspace-center">
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>{currentProject?.title || '项目'}</h2>
          <Space>
            <Button onClick={() => navigate(`/projects/${projectId}/memory`)}>记忆库</Button>
            <Button onClick={() => navigate(`/projects/${projectId}/publish`)}>发布</Button>
          </Space>
        </div>

        <List
          header={<div>章节列表</div>}
          dataSource={chapters}
          renderItem={(chapter) => (
            <List.Item
              onClick={() => setSelectedChapter(chapter)}
              style={{ cursor: 'pointer', background: selectedChapter?.id === chapter.id ? '#f0f0f0' : undefined }}
              actions={[
                getStatusTag(chapter.status),
                <Button size="small" onClick={() => handleGenerateChapter(chapter.id)}>
                  生成
                </Button>,
                <Button size="small" onClick={() => handleReviewChapter(chapter.id)}>
                  审查
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={`第${chapter.chapter_no}章: ${chapter.title || '无标题'}`}
                description={chapter.outline?.slice(0, 100) || '暂无大纲'}
              />
            </List.Item>
          )}
          locale={{ emptyText: '暂无章节，请先规划章节大纲' }}
        />
      </Content>

      <Sider width={400} style={{ background: '#fff', borderLeft: '1px solid #f0f0f0' }}>
        <Tabs
          defaultActiveKey="content"
          items={[
            {
              key: 'content',
              label: '正文',
              children: (
                <div style={{ padding: 16 }}>
                  {selectedChapter ? (
                    <div>
                      <h3>{selectedChapter.title || `第${selectedChapter.chapter_no}章`}</h3>
                      <div style={{ whiteSpace: 'pre-wrap' }}>
                        {selectedChapter.text || '暂无正文'}
                      </div>
                    </div>
                  ) : (
                    <p style={{ color: '#999' }}>请选择章节查看正文</p>
                  )}
                </div>
              ),
            },
            {
              key: 'summary',
              label: '摘要',
              children: (
                <div style={{ padding: 16 }}>
                  {selectedChapter?.summary || '暂无摘要'}
                </div>
              ),
            },
          ]}
        />
      </Sider>

      {/* 新建角色弹窗 */}
      <Modal
        title="新建角色"
        open={createCharModalOpen}
        onCancel={() => { setCreateCharModalOpen(false); createCharForm.resetFields() }}
        footer={null}
        destroyOnClose
      >
        <Form
          form={createCharForm}
          layout="vertical"
          onFinish={handleCreateCharacter}
        >
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
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
          
          <Form.Item name="motivation" label="角色动机">
            <Input.TextArea rows={2} placeholder="请输入角色动机" />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setCreateCharModalOpen(false); createCharForm.resetFields() }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={createCharLoading}>
                创建
              </Button>
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
        <Form
          form={editBibleForm}
          layout="vertical"
          onFinish={handleUpdateBible}
        >
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
              <Button onClick={() => setEditBibleModalOpen(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={editBibleLoading}>
                保存
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

export default WorkspacePage
