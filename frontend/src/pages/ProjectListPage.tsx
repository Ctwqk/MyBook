import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, InputNumber, message, Space, Tag } from 'antd'
import { PlusOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '../api'
import { useProjectStore } from '../store/projectStore'

const { Option } = Select
const { TextArea } = Input

const ProjectListPage = () => {
  const navigate = useNavigate()
  const { projects, setProjects, addProject, loading, setLoading } = useProjectStore()
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [settingsModalVisible, setSettingsModalVisible] = useState(false)
  const [editingProject, setEditingProject] = useState<any>(null)
  const [form] = Form.useForm()
  const [settingsForm] = Form.useForm()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const res = await projectApi.list()
      setProjects(res.data.items)
    } catch (err) {
      message.error('加载项目失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values: any) => {
    try {
      const res = await projectApi.create(values)
      addProject(res.data)
      setCreateModalVisible(false)
      form.resetFields()
      message.success('创建成功')
      loadProjects()
    } catch (err) {
      message.error('创建失败')
    }
  }

  const handleBootstrap = async (projectId: number) => {
    try {
      await projectApi.bootstrap(projectId)
      message.success('项目引导完成')
      navigate(`/projects/${projectId}`)
    } catch (err) {
      message.error('引导失败')
    }
  }

  const handleOpenSettings = (project: any) => {
    setEditingProject(project)
    settingsForm.setFieldsValue({
      raw_prompt: project.raw_prompt || '',
      target_chapters: project.target_chapters || 50,
      chapter_length: project.chapter_length || 3000,
      target_length: project.target_length || 150000,
    })
    setSettingsModalVisible(true)
  }

  const handleUpdateSettings = async (values: any) => {
    try {
      await projectApi.update(editingProject.id, values)
      message.success('设置更新成功')
      setSettingsModalVisible(false)
      loadProjects()
    } catch (err) {
      message.error('更新失败')
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      planning: 'processing',
      writing: 'blue',
      reviewing: 'orange',
      published: 'success',
      archived: 'default',
    }
    return colors[status] || 'default'
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'genre', key: 'genre' },
    { title: '风格', dataIndex: 'style', key: 'style' },
    { title: '目标章节', dataIndex: 'target_chapters', key: 'target_chapters', render: (v: number) => v || '-' },
    { title: '章节字数', dataIndex: 'chapter_length', key: 'chapter_length', render: (v: number) => v ? `${v.toLocaleString()}字` : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
    )},
    { title: '操作', key: 'action', width: 200, render: (_: any, record: any) => (
      <Space>
        <Button type="link" onClick={() => navigate(`/projects/${record.id}`)}>打开</Button>
        <Button type="link" icon={<SettingOutlined />} onClick={() => handleOpenSettings(record)}>设置</Button>
        {record.status === 'draft' && (
          <Button type="link" onClick={() => handleBootstrap(record.id)}>引导</Button>
        )}
      </Space>
    )},
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>我的项目</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          新建项目
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        loading={loading}
      />

      {/* 创建项目弹窗 */}
      <Modal
        title="新建项目"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form 
          form={form} 
          onFinish={handleCreate} 
          layout="vertical"
          initialValues={{
            target_chapters: 50,
            chapter_length: 3000,
            target_length: 150000
          }}
        >
          <h3>基本信息</h3>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="输入小说标题" />
          </Form.Item>
          <Form.Item name="genre" label="类型">
            <Select placeholder="选择小说类型" allowClear>
              <Option value="都市异能">都市异能</Option>
              <Option value="玄幻">玄幻</Option>
              <Option value="仙侠">仙侠</Option>
              <Option value="科幻">科幻</Option>
              <Option value="悬疑">悬疑</Option>
              <Option value="都市">都市</Option>
              <Option value="历史">历史</Option>
            </Select>
          </Form.Item>
          <Form.Item name="style" label="风格">
            <Select placeholder="选择写作风格" allowClear>
              <Option value="热血">热血</Option>
              <Option value="轻松">轻松</Option>
              <Option value="暗黑">暗黑</Option>
              <Option value="治愈">治愈</Option>
              <Option value="幽默">幽默</Option>
              <Option value="写实">写实</Option>
            </Select>
          </Form.Item>

          <h3>AI Prompt</h3>
          <Form.Item name="raw_prompt" label="原始 Prompt" extra="描述你想要的小说内容">
            <TextArea 
              rows={4} 
              placeholder="例如：一个人类文明在星际探索中发现了外星文明的遗迹..." 
            />
          </Form.Item>

          <h3>写作规划</h3>
          <Form.Item name="target_chapters" label="目标章节数" extra="预计的总章节数量">
            <InputNumber min={1} max={500} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="chapter_length" label="每章节字数" extra="每个章节的目标字数">
            <InputNumber min={500} max={20000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="target_length" label="目标总字数">
            <InputNumber min={0} max={10000000} style={{ width: '100%' }} />
          </Form.Item>

          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Button onClick={() => setCreateModalVisible(false)} style={{ marginRight: 8 }}>
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              创建项目
            </Button>
          </div>
        </Form>
      </Modal>

      {/* 项目设置弹窗 */}
      <Modal
        title={`项目设置: ${editingProject?.title}`}
        open={settingsModalVisible}
        onCancel={() => setSettingsModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form 
          form={settingsForm} 
          onFinish={handleUpdateSettings} 
          layout="vertical"
        >
          <h3>AI Prompt</h3>
          <Form.Item name="raw_prompt" label="原始 Prompt">
            <TextArea 
              rows={6} 
              placeholder="描述你想要的小说内容..." 
            />
          </Form.Item>

          <h3>写作规划</h3>
          <Form.Item name="target_chapters" label="目标章节数">
            <InputNumber min={1} max={500} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="chapter_length" label="每章节字数">
            <InputNumber min={500} max={20000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="target_length" label="目标总字数">
            <InputNumber min={0} max={10000000} style={{ width: '100%' }} />
          </Form.Item>

          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Button onClick={() => setSettingsModalVisible(false)} style={{ marginRight: 8 }}>
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              保存设置
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectListPage
