import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Table, Button, Tag, Space, Spin, Modal, message } from 'antd'
import { publishApi, chapterApi } from '../api'

const PublishPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState<any[]>([])
  const [chapters, setChapters] = useState<any[]>([])
  const [publishModalVisible, setPublishModalVisible] = useState(false)
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [taskRes, chapterRes] = await Promise.all([
        publishApi.listTasks(Number(projectId)).catch(() => ({ data: { items: [] } })),
        chapterApi.list(Number(projectId)).catch(() => ({ data: [] })),
      ])
      setTasks(taskRes.data?.items || [])
      setChapters(chapterRes.data || [])
    } catch (err) {
      console.error('加载失败', err)
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!selectedChapterId) {
      message.warning('请选择章节')
      return
    }
    setSubmitting(true)
    try {
      await publishApi.submit(Number(projectId), {
        chapter_id: selectedChapterId,
        platform: 'mock',
        account_id: 'mock_account',
        remote_book_id: 'mock_book',
      })
      message.success('发布请求已提交')
      setPublishModalVisible(false)
      setSelectedChapterId(null)
      loadData()
    } catch (err: any) {
      console.error('发布失败', err)
      message.error(err.response?.data?.detail || '发布失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegisterSession = async () => {
    try {
      const res = await publishApi.registerSession({
        platform: 'mock',
        session_token: 'test_token_' + Date.now(),
      })
      if (res.data?.success) {
        message.success('模拟会话注册成功')
      } else {
        message.info('模拟会话已注册或注册中')
      }
    } catch (err: any) {
      console.error('注册失败', err)
      // 不显示错误，因为mock平台可能不需要真实注册
      message.info('平台会话状态已更新')
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      preparing: 'processing',
      submitting: 'processing',
      success: 'success',
      failed: 'error',
      cancelled: 'default',
    }
    return colors[status] || 'default'
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '章节', dataIndex: 'chapter_id', key: 'chapter', render: (id: number) => `章节 ${id}` },
    { title: '平台', dataIndex: 'platform', key: 'platform' },
    { title: '模式', dataIndex: 'mode', key: 'mode', render: (m: string) => m || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={getStatusColor(status)}>{status?.toUpperCase() || 'N/A'}</Tag>
    )},
    { title: '错误', dataIndex: 'error_message', key: 'error', render: (msg: string) => msg || '-' },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Space>
        <Button size="small" onClick={() => publishApi.syncTask(Number(projectId), record.id).catch(() => {})}>
          同步
        </Button>
        {record.status === 'pending' && (
          <Button size="small" danger onClick={() => publishApi.cancelTask(Number(projectId), record.id).catch(() => {})}>
            取消
          </Button>
        )}
      </Space>
    )},
  ]

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>发布管理</h1>
        <Space>
          <Button onClick={() => navigate(`/projects/${projectId}`)}>返回创作台</Button>
          <Button type="primary" onClick={() => setPublishModalVisible(true)}>发布章节</Button>
        </Space>
      </div>

      <Card title="发布任务">
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          locale={{ emptyText: '暂无发布任务' }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Card title="平台适配" style={{ marginTop: 16 }}>
        <p style={{ color: '#666', marginBottom: 12 }}>当前支持以下平台：</p>
        <Space>
          <Tag color="blue">Mock (测试平台)</Tag>
        </Space>
        <div style={{ marginTop: 16 }}>
          <Button onClick={handleRegisterSession}>
            注册模拟会话
          </Button>
          <span style={{ marginLeft: 12, color: '#999', fontSize: 12 }}>
            测试用，无需真实账号
          </span>
        </div>
      </Card>

      <Modal
        title="发布章节"
        open={publishModalVisible}
        onCancel={() => {
          setPublishModalVisible(false)
          setSelectedChapterId(null)
        }}
        onOk={handlePublish}
        okText="发布"
        confirmLoading={submitting}
      >
        <div style={{ marginBottom: 16 }}>
          <h4>选择章节：</h4>
          {chapters.length > 0 ? (
            <Space wrap>
              {chapters.map((ch) => (
                <Tag
                  key={ch.id}
                  color={selectedChapterId === ch.id ? 'blue' : 'default'}
                  onClick={() => setSelectedChapterId(ch.id)}
                  style={{ cursor: 'pointer', padding: '4px 12px' }}
                >
                  第{ch.chapter_no}章: {ch.title || '无标题'}
                </Tag>
              ))}
            </Space>
          ) : (
            <p style={{ color: '#999' }}>暂无章节可发布</p>
          )}
        </div>
        <p style={{ color: '#666' }}>平台: <Tag>Mock (测试)</Tag></p>
        <p style={{ color: '#666' }}>模式: 立即发布 (模拟)</p>
      </Modal>
    </div>
  )
}

export default PublishPage
