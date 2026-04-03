import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Button, Card, Space, Spin, message, Modal, Form, Input, InputNumber, Select, Collapse, Typography, Tag, Dropdown, type MenuProps } from 'antd'
import { PlusOutlined, EditOutlined, BookOutlined, TeamOutlined, MoreOutlined, ReloadOutlined, ThunderboltOutlined, FileTextOutlined } from '@ant-design/icons'
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
  
  // 创建角色
  const [createCharModalOpen, setCreateCharModalOpen] = useState(false)
  const [createCharForm] = Form.useForm()
  const [createCharLoading, setCreateCharLoading] = useState(false)
  
  // 编辑故事设定
  const [editBibleModalOpen, setEditBibleModalOpen] = useState(false)
  const [editBibleForm] = Form.useForm()
  const [editBibleLoading, setEditBibleLoading] = useState(false)
  
  // 续写章节
  const [continueModalOpen, setContinueModalOpen] = useState(false)
  const [continueForm] = Form.useForm()
  const [continueLoading, setContinueLoading] = useState(false)
  
  // 重写章节
  const [rewriteModalOpen, setRewriteModalOpen] = useState(false)
  const [rewriteForm] = Form.useForm()
  const [rewriteLoading, setRewriteLoading] = useState(false)
  
  // 修补章节
  const [patchModalOpen, setPatchModalOpen] = useState(false)
  const [patchForm] = Form.useForm()
  const [patchLoading, setPatchLoading] = useState(false)
  
  // 修订大纲
  const [reviseModalOpen, setReviseModalOpen] = useState(false)
  const [reviseForm] = Form.useForm()
  const [reviseLoading, setReviseLoading] = useState(false)

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

  // 生成章节
  const handleGenerateChapter = async (chapterId: number) => {
    try {
      message.loading({ content: '正在生成章节...', key: 'generate' })
      await chapterApi.generate(Number(projectId), chapterId)
      message.success({ content: '章节生成完成', key: 'generate' })
      loadChapters()
      // 刷新选中章节
      const updated = chapters.find(c => c.id === chapterId)
      if (updated) {
        const chapterRes = await chapterApi.get(Number(projectId), chapterId)
        setSelectedChapter(chapterRes.data)
      }
    } catch (err: any) {
      message.error({ content: err.response?.data?.detail || '生成失败', key: 'generate' })
    }
  }

  // 续写章节
  const handleContinueChapter = async () => {
    try {
      setContinueLoading(true)
      const values = await continueForm.validateFields()
      message.loading({ content: '正在续写...', key: 'continue' })
      await chapterApi.continue(Number(projectId), selectedChapter.id, {
        target_word_count: values.target_word_count || 3000
      })
      message.success({ content: '续写完成', key: 'continue' })
      setContinueModalOpen(false)
      continueForm.resetFields()
      // 刷新章节
      const updated = await chapterApi.get(Number(projectId), selectedChapter.id)
      setSelectedChapter(updated.data)
      loadChapters()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '续写失败')
    } finally {
      setContinueLoading(false)
    }
  }

  // 重写章节
  const handleRewriteChapter = async () => {
    try {
      setRewriteLoading(true)
      const values = await rewriteForm.validateFields()
      message.loading({ content: '正在重写...', key: 'rewrite' })
      await chapterApi.rewrite(Number(projectId), selectedChapter.id, {
        rewrite_instructions: values.instructions
      })
      message.success({ content: '重写完成', key: 'rewrite' })
      setRewriteModalOpen(false)
      rewriteForm.resetFields()
      // 刷新章节
      const updated = await chapterApi.get(Number(projectId), selectedChapter.id)
      setSelectedChapter(updated.data)
      loadChapters()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '重写失败')
    } finally {
      setRewriteLoading(false)
    }
  }

  // 修补章节
  const handlePatchChapter = async () => {
    try {
      setPatchLoading(true)
      const values = await patchForm.validateFields()
      message.loading({ content: '正在修补...', key: 'patch' })
      await chapterApi.patch(Number(projectId), selectedChapter.id, {
        segment_id: values.segment_id,
        segment_content: values.segment_content,
        patch_instructions: values.patch_instructions
      })
      message.success({ content: '修补完成', key: 'patch' })
      setPatchModalOpen(false)
      patchForm.resetFields()
      // 刷新章节
      const updated = await chapterApi.get(Number(projectId), selectedChapter.id)
      setSelectedChapter(updated.data)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '修补失败')
    } finally {
      setPatchLoading(false)
    }
  }

  // 修订大纲
  const handleReviseOutline = async () => {
    try {
      setReviseLoading(true)
      const values = await reviseForm.validateFields()
      message.loading({ content: '正在修订大纲...', key: 'revise' })
      await projectApi.reviseOutline(Number(projectId), selectedChapter.id, values.notes)
      message.success({ content: '大纲修订完成', key: 'revise' })
      setReviseModalOpen(false)
      reviseForm.resetFields()
      loadChapters()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '修订失败')
    } finally {
      setReviseLoading(false)
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
      target_audience: storyBible?.target_audience || '',
      world_overview: storyBible?.world_overview || '',
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

  const getRoleLabel = (roleType: string) => {
    return roleLabels[roleType] || roleType || '未知'
  }

  // 生成/续写/重写下拉菜单
  const generateDropdownItems = (chapterId: number): MenuProps => ({
    items: [
      {
        key: 'generate',
        label: '生成正文',
        icon: <ThunderboltOutlined />,
        onClick: () => handleGenerateChapter(chapterId)
      },
      {
        key: 'continue',
        label: '续写章节',
        icon: <ReloadOutlined />,
        onClick: () => {
          setSelectedChapter(chapters.find(c => c.id === chapterId))
          setContinueModalOpen(true)
        }
      },
      {
        key: 'rewrite',
        label: '重写章节',
        icon: <FileTextOutlined />,
        onClick: () => {
          setSelectedChapter(chapters.find(c => c.id === chapterId))
          setRewriteModalOpen(true)
        }
      },
      { type: 'divider' as const },
      {
        key: 'revise',
        label: '修订大纲',
        icon: <EditOutlined />,
        onClick: () => {
          setSelectedChapter(chapters.find(c => c.id === chapterId))
          reviseForm.setFieldsValue({ outline: chapters.find(c => c.id === chapterId)?.outline || '' })
          setReviseModalOpen(true)
        }
      },
      {
        key: 'patch',
        label: '修补段落',
        icon: <EditOutlined />,
        onClick: () => {
          setSelectedChapter(chapters.find(c => c.id === chapterId))
          setPatchModalOpen(true)
        }
      },
    ]
  })

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
          <Button onClick={() => navigate(`/projects/${projectId}/memory`)}>记忆库</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/publish`)}>发布</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/arc`)}>Arc管理</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/orchestrator`)}>编排器</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/feedback`)}>读者反馈</Button>
          <Button onClick={() => navigate(`/projects/${projectId}/platforms`)}>平台账号</Button>
        </Space>
      </Layout.Header>

      <Layout>
        <Sider 
          width={320} 
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
                        第{chapter.chapter_no}章 {chapter.title && `- ${chapter.title}`}
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
                    <Space size={2}>
                      {chapter.status === 'outline' ? (
                        <Dropdown menu={generateDropdownItems(chapter.id)} trigger={['click']}>
                          <Button size="small" type="primary" icon={<MoreOutlined />} />
                        </Dropdown>
                      ) : (
                        <>
                          <Button size="small" type="primary" onClick={(e) => { e.stopPropagation(); handleGenerateChapter(chapter.id) }} style={{ minWidth: 52 }}>生成</Button>
                          <Dropdown menu={generateDropdownItems(chapter.id)} trigger={['click']}>
                            <Button size="small" icon={<MoreOutlined />} />
                          </Dropdown>
                        </>
                      )}
                    </Space>
                  </div>
                </Card>
              )) : (
                <Text type="secondary" style={{ padding: '8px 0', display: 'block' }}>
                  暂无章节，请先使用"引导"功能生成章节
                </Text>
              )}
            </Panel>
            
            {/* 故事设定 */}
            <Panel 
              header={<span><BookOutlined /> 故事设定</span>} 
              key="story"
              extra={<Button type="link" size="small" icon={<EditOutlined />} onClick={handleEditBible}>编辑</Button>}
            >
              {storyBible ? (
                <div style={{ fontSize: 13 }}>
                  <div style={{ marginBottom: 6 }}><Text strong>类型：</Text>{storyBible.genre || '待填充'}</div>
                  <div style={{ marginBottom: 6 }}><Text strong>主题：</Text>{storyBible.theme || '待填充'}</div>
                  <div style={{ marginBottom: 6 }}><Text strong>基调：</Text>{storyBible.tone || '待填充'}</div>
                  <div style={{ marginBottom: 6 }}><Text strong>目标读者：</Text>{storyBible.target_audience || '待填充'}</div>
                  {storyBible.synopsis && (
                    <div style={{ marginTop: 8 }}>
                      <Text strong>概述：</Text>
                      <div style={{ color: '#666', marginTop: 2, maxHeight: 60, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {storyBible.synopsis.slice(0, 80)}...
                      </div>
                    </div>
                  )}
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <Text strong>{char.name}</Text>
                      <Tag color={char.role_type === 'protagonist' ? 'blue' : 'default'} style={{ marginLeft: 8, fontSize: 10 }}>
                        {getRoleLabel(char.role_type)}
                      </Tag>
                    </div>
                  </div>
                  {char.profile && (
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      {char.profile.slice(0, 60)}...
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
                    <Text strong style={{ fontSize: 16 }}>
                      第{selectedChapter.chapter_no}章 {selectedChapter.title && `- ${selectedChapter.title}`}
                    </Text>
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
              extra={
                <Space>
                  <Button type="primary" onClick={() => handleGenerateChapter(selectedChapter.id)}>生成</Button>
                  <Dropdown menu={generateDropdownItems(selectedChapter.id)} trigger={['click']}>
                    <Button icon={<MoreOutlined />}>更多</Button>
                  </Dropdown>
                </Space>
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
          <Form.Item name="personality" label="性格特点">
            <Input.TextArea rows={2} placeholder="请输入性格特点" />
          </Form.Item>
          <Form.Item name="motivation" label="角色动机">
            <Input.TextArea rows={2} placeholder="请输入角色动机" />
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
        width={700}
        destroyOnClose
      >
        <Form form={editBibleForm} layout="vertical" onFinish={handleUpdateBible} scrollToFirstError>
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
          <Form.Item name="target_audience" label="目标读者">
            <Input placeholder="如：18-35岁男性读者" />
          </Form.Item>
          <Form.Item name="synopsis" label="详细概述">
            <Input.TextArea rows={4} placeholder="请输入故事详细概述" />
          </Form.Item>
          <Form.Item name="world_overview" label="世界观概述">
            <Input.TextArea rows={3} placeholder="请输入世界观概述" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setEditBibleModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={editBibleLoading}>保存</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 续写章节弹窗 */}
      <Modal
        title="续写章节"
        open={continueModalOpen}
        onCancel={() => { setContinueModalOpen(false); continueForm.resetFields() }}
        footer={[
          <Button key="cancel" onClick={() => { setContinueModalOpen(false); continueForm.resetFields() }}>取消</Button>,
          <Button key="submit" type="primary" loading={continueLoading} onClick={handleContinueChapter}>开始续写</Button>
        ]}
      >
        <Form form={continueForm} layout="vertical">
          <Form.Item name="target_word_count" label="目标续写字数" extra="续写到指定的字数">
            <InputNumber min={500} max={20000} style={{ width: '100%' }} placeholder="3000" />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            当前章节字数: {selectedChapter?.word_count || 0} 字
          </Text>
        </Form>
      </Modal>

      {/* 重写章节弹窗 */}
      <Modal
        title="重写章节"
        open={rewriteModalOpen}
        onCancel={() => { setRewriteModalOpen(false); rewriteForm.resetFields() }}
        footer={[
          <Button key="cancel" onClick={() => { setRewriteModalOpen(false); rewriteForm.resetFields() }}>取消</Button>,
          <Button key="submit" type="primary" loading={rewriteLoading} onClick={handleRewriteChapter}>开始重写</Button>
        ]}
      >
        <Form form={rewriteForm} layout="vertical">
          <Form.Item name="instructions" label="重写指令" rules={[{ required: true, message: '请输入重写指令' }]}>
            <Input.TextArea 
              rows={4} 
              placeholder="请描述需要如何重写此章节，例如：&#10;- 增强主角的心理描写&#10;- 加快节奏&#10;- 改变结局走向..." 
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修补章节弹窗 */}
      <Modal
        title="修补章节"
        open={patchModalOpen}
        onCancel={() => { setPatchModalOpen(false); patchForm.resetFields() }}
        footer={[
          <Button key="cancel" onClick={() => { setPatchModalOpen(false); patchForm.resetFields() }}>取消</Button>,
          <Button key="submit" type="primary" loading={patchLoading} onClick={handlePatchChapter}>开始修补</Button>
        ]}
        width={800}
      >
        <Form form={patchForm} layout="vertical">
          <Form.Item name="segment_id" label="段落ID" rules={[{ required: true, message: '请输入段落ID' }]}>
            <Input placeholder="请输入需要修补的段落ID" />
          </Form.Item>
          <Form.Item name="segment_content" label="原始段落内容">
            <Input.TextArea rows={3} placeholder="请输入原始段落内容（可选）" />
          </Form.Item>
          <Form.Item name="patch_instructions" label="修补指令" rules={[{ required: true, message: '请输入修补指令' }]}>
            <Input.TextArea 
              rows={4} 
              placeholder="请描述需要如何修补，例如：&#10;- 修复逻辑矛盾&#10;- 润色语句&#10;- 增强细节描写..." 
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修订大纲弹窗 */}
      <Modal
        title="修订章节大纲"
        open={reviseModalOpen}
        onCancel={() => { setReviseModalOpen(false); reviseForm.resetFields() }}
        footer={[
          <Button key="cancel" onClick={() => { setReviseModalOpen(false); reviseForm.resetFields() }}>取消</Button>,
          <Button key="submit" type="primary" loading={reviseLoading} onClick={handleReviseOutline}>提交修订</Button>
        ]}
        width={800}
      >
        <Form form={reviseForm} layout="vertical">
          <Form.Item name="outline" label="当前大纲">
            <Input.TextArea rows={4} placeholder="当前大纲内容" />
          </Form.Item>
          <Form.Item name="notes" label="修订说明" rules={[{ required: true, message: '请输入修订说明' }]}>
            <Input.TextArea 
              rows={4} 
              placeholder="请描述需要如何修订大纲，例如：&#10;- 增加一个新的情节点&#10;- 调整章节节奏&#10;- 修改主角的目标..." 
            />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

export default WorkspacePage
