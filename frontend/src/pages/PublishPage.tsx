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

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [taskRes, chapterRes] = await Promise.all([
        publishApi.listTasks(Number(projectId)),
        chapterApi.list(Number(projectId)),
      ])
      setTasks(taskRes.data.items)
      setChapters(chapterRes.data)
    } catch (err) {
      console.error('加载失败', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!selectedChapterId) {
      message.warning('请选择章节')
      return
    }
    try {
      await publishApi.submit(Number(projectId), {
        chapter_id: selectedChapterId,
        platform: 'mock',
        account_id: 'mock_account',
        remote_book_id: 'mock_book',
      })
      message.success('发布请求已提交')
      setPublishModalVisible(false)
      loadData()
    } catch (err) {
      message.error('发布失败')
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
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: '章节', dataIndex: 'chapter_id', key: 'chapter' },
    { title: '平台', dataIndex: 'platform', key: 'platform' },
    { title: '模式', dataIndex: 'mode', key: 'mode' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
    )},
    { title: '错误', dataIndex: 'error_message', key: 'error', render: (msg: string) => msg || '-' },
    { title: '时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Space>
        <Button size="small" onClick={() => publishApi.syncTask(Number(projectId), record.id)}>
          同步
        </Button>
        {record.status === 'pending' && (
          <Button size="small" danger onClick={() => publishApi.cancelTask(Number(projectId), record.id)}>
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
        />
      </Card>

      <Card title="平台适配" style={{ marginTop: 16 }}>
        <p style={{ color: '#999' }}>当前支持以下平台：</p>
        <Space>
          <Tag>Mock (测试)</Tag>
        </Space>
        <div style={{ marginTop: 16 }}>
          <Button
            onClick={async () => {
              try {
                await publishApi.registerSession({
                  platform: 'mock',
                  session_token: 'test_token_123',
                })
                message.success('模拟会话注册成功')
              } catch (err) {
                message.error('注册失败')
              }
            }}
          >
            注册模拟会话
          </Button>
        </div>
      </Card>

      <Modal
        title="发布章节"
        open={publishModalVisible}
        onCancel={() => setPublishModalVisible(false)}
        onOk={handlePublish}
      >
        <div style={{ marginBottom: 16 }}>
          <h4>选择章节：</h4>
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
        </div>
        <p style={{ color: '#999' }}>平台: Mock (测试)</p>
        <p style={{ color: '#999' }}>模式: 立即发布 (模拟)</p>
      </Modal>
    </div>
  )
}

export default PublishPage
