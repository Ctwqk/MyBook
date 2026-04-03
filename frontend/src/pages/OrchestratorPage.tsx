import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Card, Button, Space, Spin, message, Table, Tag, Tabs, Modal, Input, Alert, Row, Col, Statistic, Typography, Divider, Steps, Badge } from 'antd'
import { ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, CheckCircleOutlined, ExclamationCircleOutlined, SettingOutlined, HistoryOutlined } from '@ant-design/icons'
import { orchestratorApi } from '../api'

const { Header, Content } = Layout
const { Text, Title, Paragraph } = Typography
const { TabPane } = Tabs
const { TextArea } = Input

type Mode = 'supervised' | 'checkpoint' | 'blackbox'

const modeConfig: Record<Mode, { label: string; color: string; description: string }> = {
  supervised: { 
    label: '监督模式', 
    color: 'blue',
    description: '每一步都需要人工确认，完整控制写作流程'
  },
  checkpoint: { 
    label: '检查点模式', 
    color: 'orange',
    description: '在关键节点暂停，其余自动执行'
  },
  blackbox: { 
    label: '黑盒模式', 
    color: 'purple',
    description: '全自动化执行，仅记录结果'
  }
}

const OrchestratorPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  
  // 模式状态
  const [currentMode, setCurrentMode] = useState<Mode>('supervised')
  const [modeLoading, setModeLoading] = useState(false)
  
  // 待处理决策
  const [decisions, setDecisions] = useState<any[]>([])
  const [decisionsLoading, setDecisionsLoading] = useState(false)
  
  // 决策详情弹窗
  const [decisionModalOpen, setDecisionModalOpen] = useState(false)
  const [selectedDecision, setSelectedDecision] = useState<any>(null)
  const [approveNotes, setApproveNotes] = useState('')

  useEffect(() => {
    if (projectId) {
      loadOverview()
    }
  }, [projectId])

  const loadOverview = async () => {
    try {
      setLoading(true)
      await Promise.all([
        loadMode(),
        loadDecisions()
      ])
    } catch (err) {
      console.error('加载概览失败', err)
    } finally {
      setLoading(false)
    }
  }

  const loadMode = async () => {
    try {
      const res = await orchestratorApi.getMode(Number(projectId))
      if (res.data?.mode) {
        setCurrentMode(res.data.mode)
      }
    } catch (err) {
      console.error('加载模式失败', err)
    }
  }

  const loadDecisions = async () => {
    try {
      setDecisionsLoading(true)
      const res = await orchestratorApi.getPendingDecisions(Number(projectId))
      setDecisions(res.data || [])
    } catch (err) {
      console.error('加载决策失败', err)
    } finally {
      setDecisionsLoading(false)
    }
  }

  const handleModeChange = async (mode: Mode) => {
    try {
      setModeLoading(true)
      message.loading({ content: '正在切换模式...', key: 'mode' })
      await orchestratorApi.setMode(Number(projectId), mode)
      message.success({ content: '模式切换成功', key: 'mode' })
      setCurrentMode(mode)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '模式切换失败')
    } finally {
      setModeLoading(false)
    }
  }

  const handleApprove = async (decisionId: string, approved: boolean) => {
    try {
      message.loading({ content: approved ? '正在批准...' : '正在拒绝...', key: 'approve' })
      await orchestratorApi.approveTask(decisionId, { 
        approved, 
        notes: approveNotes 
      })
      message.success({ content: approved ? '已批准' : '已拒绝', key: 'approve' })
      setDecisionModalOpen(false)
      setSelectedDecision(null)
      setApproveNotes('')
      loadDecisions()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    }
  }

  const showDecisionDetail = (decision: any) => {
    setSelectedDecision(decision)
    setDecisionModalOpen(true)
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'warning',
      approved: 'success',
      rejected: 'error',
      processing: 'processing'
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '待处理',
      approved: '已批准',
      rejected: '已拒绝',
      processing: '处理中'
    }
    return labels[status] || status
  }

  const getTaskTypeTag = (type: string) => {
    const colors: Record<string, string> = {
      outline: 'blue',
      generate: 'green',
      review: 'orange',
      patch: 'purple',
      rewrite: 'cyan',
      replan: 'red'
    }
    return <Tag color={colors[type] || 'default'}>{type}</Tag>
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      {/* 顶部导航 */}
      <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/projects/${projectId}`)} style={{ color: '#fff' }} />
          <Title level={4} style={{ color: '#fff', margin: 0 }}>任务编排器</Title>
        </Space>
      </Header>

      <Content style={{ padding: 24 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 概览 */}
          <TabPane tab={<span><SettingOutlined /> 模式设置</span>} key="overview">
            <Row gutter={16}>
              <Col span={8}>
                <Card 
                  title="当前运行模式" 
                  extra={<Tag color={modeConfig[currentMode].color}>{modeConfig[currentMode].label}</Tag>}
                >
                  <Paragraph>{modeConfig[currentMode].description}</Paragraph>
                  <Divider />
                  <Space>
                    <Button 
                      type={currentMode === 'supervised' ? 'primary' : 'default'}
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleModeChange('supervised')}
                      loading={modeLoading}
                    >
                      监督模式
                    </Button>
                    <Button 
                      type={currentMode === 'checkpoint' ? 'primary' : 'default'}
                      icon={<PauseCircleOutlined />}
                      onClick={() => handleModeChange('checkpoint')}
                      loading={modeLoading}
                    >
                      检查点模式
                    </Button>
                    <Button 
                      type={currentMode === 'blackbox' ? 'primary' : 'default'}
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleModeChange('blackbox')}
                      loading={modeLoading}
                    >
                      黑盒模式
                    </Button>
                  </Space>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="模式说明">
                  <Steps direction="vertical" size="small" current={currentMode === 'supervised' ? 0 : currentMode === 'checkpoint' ? 1 : 2}>
                    <Steps.Step 
                      title="监督模式" 
                      description="人工确认每一步操作" 
                      icon={<CheckCircleOutlined />}
                      status={currentMode === 'supervised' ? 'process' : 'wait'}
                    />
                    <Steps.Step 
                      title="检查点模式" 
                      description="关键节点暂停审查" 
                      icon={<PauseCircleOutlined />}
                      status={currentMode === 'checkpoint' ? 'process' : currentMode === 'supervised' ? 'finish' : 'wait'}
                    />
                    <Steps.Step 
                      title="黑盒模式" 
                      description="全自动化执行" 
                      icon={<PlayCircleOutlined />}
                      status={currentMode === 'blackbox' ? 'process' : 'wait'}
                    />
                  </Steps>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="统计">
                  <Statistic title="待处理决策" value={decisions.filter(d => d.status === 'pending').length} />
                  <Divider />
                  <Statistic title="今日已处理" value={decisions.filter(d => d.status !== 'pending').length} />
                </Card>
              </Col>
            </Row>

            {/* 待处理决策列表 */}
            <Card title="待处理决策" style={{ marginTop: 24 }}>
              {decisions.length > 0 ? (
                <Table
                  dataSource={decisions.filter(d => d.status === 'pending')}
                  rowKey="id"
                  loading={decisionsLoading}
                  columns={[
                    { 
                      title: '任务ID', 
                      dataIndex: 'task_id', 
                      width: 200,
                      render: (id: string) => <Text code>{id?.slice(0, 20)}...</Text>
                    },
                    { 
                      title: '类型', 
                      dataIndex: 'task_type', 
                      width: 100,
                      render: (type: string) => getTaskTypeTag(type)
                    },
                    { 
                      title: '章节', 
                      dataIndex: 'chapter_id', 
                      width: 80,
                      render: (id: number) => id ? `第${id}章` : '-'
                    },
                    { 
                      title: '描述', 
                      dataIndex: 'description',
                      ellipsis: true
                    },
                    { 
                      title: '状态', 
                      dataIndex: 'status', 
                      width: 100,
                      render: (status: string) => (
                        <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>
                      )
                    },
                    {
                      title: '操作',
                      width: 150,
                      render: (_, record) => (
                        <Space>
                          <Button size="small" type="link" onClick={() => showDecisionDetail(record)}>
                            详情
                          </Button>
                        </Space>
                      )
                    }
                  ]}
                />
              ) : (
                <Alert message="暂无待处理决策" description="所有任务都已处理完成" type="success" showIcon />
              )}
            </Card>
          </TabPane>

          {/* 历史记录 */}
          <TabPane tab={<span><HistoryOutlined /> 处理历史</span>} key="history">
            <Table
              dataSource={decisions.filter(d => d.status !== 'pending')}
              rowKey="id"
              loading={decisionsLoading}
              columns={[
                { 
                  title: '任务ID', 
                  dataIndex: 'task_id', 
                  width: 200,
                  render: (id: string) => <Text code>{id?.slice(0, 20)}...</Text>
                },
                { 
                  title: '类型', 
                  dataIndex: 'task_type', 
                  width: 100,
                  render: (type: string) => getTaskTypeTag(type)
                },
                { 
                  title: '决策', 
                  dataIndex: 'status', 
                  width: 100,
                  render: (status: string) => (
                    <Badge status={status === 'approved' ? 'success' : 'error'} text={getStatusLabel(status)} />
                  )
                },
                { 
                  title: '处理时间', 
                  dataIndex: 'updated_at',
                  width: 180
                },
                {
                  title: '备注',
                  dataIndex: 'notes',
                  ellipsis: true
                },
                {
                  title: '操作',
                  width: 100,
                  render: (_, record) => (
                    <Button size="small" type="link" onClick={() => showDecisionDetail(record)}>
                      查看
                    </Button>
                  )
                }
              ]}
            />
          </TabPane>

          {/* 模式详情 */}
          <TabPane tab={<span><SettingOutlined /> 模式详情</span>} key="detail">
            <Row gutter={24}>
              <Col span={8}>
                <Card 
                  title="监督模式" 
                  extra={<Tag color={currentMode === 'supervised' ? 'blue' : 'default'}>
                    {currentMode === 'supervised' ? '当前' : '切换'}
                  </Tag>}
                >
                  <Paragraph>
                    <b>监督模式</b>提供对写作过程的完全控制。
                  </Paragraph>
                  <ul>
                    <li>每一步操作都需要人工确认</li>
                    <li>可以随时中断或修改流程</li>
                    <li>适合重要章节的精细控制</li>
                    <li>最高的质量保证</li>
                  </ul>
                  <Button 
                    type={currentMode === 'supervised' ? 'default' : 'primary'}
                    onClick={() => handleModeChange('supervised')}
                    disabled={currentMode === 'supervised'}
                  >
                    切换到监督模式
                  </Button>
                </Card>
              </Col>
              <Col span={8}>
                <Card 
                  title="检查点模式" 
                  extra={<Tag color={currentMode === 'checkpoint' ? 'orange' : 'default'}>
                    {currentMode === 'checkpoint' ? '当前' : '切换'}
                  </Tag>}
                >
                  <Paragraph>
                    <b>检查点模式</b>在关键节点暂停审查。
                  </Paragraph>
                  <ul>
                    <li>在关键节点自动暂停</li>
                    <li>审查完成后自动继续</li>
                    <li>平衡效率与控制</li>
                    <li>适合常规写作任务</li>
                  </ul>
                  <Button 
                    type={currentMode === 'checkpoint' ? 'default' : 'primary'}
                    onClick={() => handleModeChange('checkpoint')}
                    disabled={currentMode === 'checkpoint'}
                  >
                    切换到检查点模式
                  </Button>
                </Card>
              </Col>
              <Col span={8}>
                <Card 
                  title="黑盒模式" 
                  extra={<Tag color={currentMode === 'blackbox' ? 'purple' : 'default'}>
                    {currentMode === 'blackbox' ? '当前' : '切换'}
                  </Tag>}
                >
                  <Paragraph>
                    <b>黑盒模式</b>全自动化执行所有操作。
                  </Paragraph>
                  <ul>
                    <li>完全自动化执行</li>
                    <li>最快的工作效率</li>
                    <li>仅记录执行结果</li>
                    <li>适合批量处理任务</li>
                  </ul>
                  <Button 
                    type={currentMode === 'blackbox' ? 'default' : 'primary'}
                    onClick={() => handleModeChange('blackbox')}
                    disabled={currentMode === 'blackbox'}
                  >
                    切换到黑盒模式
                  </Button>
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Content>

      {/* 决策详情弹窗 */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
            <span>决策详情</span>
          </Space>
        }
        open={decisionModalOpen}
        onCancel={() => setDecisionModalOpen(false)}
        footer={[
          <Button key="reject" danger onClick={() => selectedDecision && handleApprove(selectedDecision.task_id, false)}>
            拒绝
          </Button>,
          <Button key="approve" type="primary" onClick={() => selectedDecision && handleApprove(selectedDecision.task_id, true)}>
            批准
          </Button>
        ]}
        width={700}
      >
        {selectedDecision && (
          <div>
            <Row gutter={16}>
              <Col span={12}>
                <Text type="secondary">任务ID</Text>
                <div><Text code>{selectedDecision.task_id}</Text></div>
              </Col>
              <Col span={12}>
                <Text type="secondary">任务类型</Text>
                <div>{getTaskTypeTag(selectedDecision.task_type)}</div>
              </Col>
            </Row>
            <Divider />
            <Row gutter={16}>
              <Col span={12}>
                <Text type="secondary">章节ID</Text>
                <div>{selectedDecision.chapter_id ? `第${selectedDecision.chapter_id}章` : '-'}</div>
              </Col>
              <Col span={12}>
                <Text type="secondary">状态</Text>
                <div>
                  <Tag color={getStatusColor(selectedDecision.status)}>
                    {getStatusLabel(selectedDecision.status)}
                  </Tag>
                </div>
              </Col>
            </Row>
            <Divider />
            <div>
              <Text type="secondary">描述</Text>
              <Paragraph>{selectedDecision.description || '无描述'}</Paragraph>
            </div>
            {selectedDecision.context && (
              <>
                <Divider />
                <div>
                  <Text type="secondary">上下文</Text>
                  <Card size="small" style={{ marginTop: 8 }}>
                    <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>
                      {JSON.stringify(selectedDecision.context, null, 2)}
                    </pre>
                  </Card>
                </div>
              </>
            )}
            <Divider />
            <div>
              <Text type="secondary">备注（可选）</Text>
              <TextArea 
                rows={3} 
                placeholder="输入备注信息..." 
                value={approveNotes}
                onChange={(e) => setApproveNotes(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </div>
          </div>
        )}
      </Modal>
    </Layout>
  )
}

export default OrchestratorPage
