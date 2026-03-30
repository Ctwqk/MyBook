import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '../api'
import { useProjectStore } from '../store/projectStore'

const { Option } = Select

const ProjectListPage = () => {
  const navigate = useNavigate()
  const { projects, setProjects, addProject, loading, setLoading } = useProjectStore()
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()

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
      setModalVisible(false)
      form.resetFields()
      message.success('创建成功')
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
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
    )},
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Space>
        <Button type="link" onClick={() => navigate(`/projects/${record.id}`)}>打开</Button>
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
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新建项目
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title="新建项目"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="genre" label="类型">
            <Select>
              <Option value="都市异能">都市异能</Option>
              <Option value="玄幻">玄幻</Option>
              <Option value="仙侠">仙侠</Option>
              <Option value="科幻">科幻</Option>
              <Option value="悬疑">悬疑</Option>
            </Select>
          </Form.Item>
          <Form.Item name="style" label="风格">
            <Select>
              <Option value="热血">热血</Option>
              <Option value="轻松">轻松</Option>
              <Option value="暗黑">暗黑</Option>
              <Option value="治愈">治愈</Option>
            </Select>
          </Form.Item>
          <Form.Item name="premise" label="剧情简述">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectListPage
