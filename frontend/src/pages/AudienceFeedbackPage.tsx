import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Card, Button, Space, Spin, message, Table, Tag, Tabs, Modal, Form, Input, Rate, Select, Alert, Row, Col, Statistic, Typography, Divider, List, Badge } from 'antd'
import { ArrowLeftOutlined, MessageOutlined, BarChartOutlined, BellOutlined, ThunderboltOutlined, ExperimentOutlined, WarningOutlined } from '@ant-design/icons'
import { audienceApi } from '../api'

const { Header, Content } = Layout
const { Text, Title, Paragraph } = Typography
const { TabPane } = Tabs

const AudienceFeedbackPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  
  // 反馈数据
  const [feedbacks, setFeedbacks] = useState<any[]>([])
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  
  // 分析数据
  const [analysis, setAnalysis] = useState<any>(null)
  
  // 告警数据
  const [alerts, setAlerts] = useState<any[]>([])
  
  // 信号数据
  const [signals, setSignals] = useState<any>(null)
  
  // Writer提示包
  const [hintPack, setHintPack] = useState<any>(null)
  
  // 提交反馈弹窗
  const [submitModalOpen, setSubmitModalOpen] = useState(false)
  const [submitForm] = Form.useForm()
  const [submitLoading, setSubmitLoading] = useState(false)
  
  // 评论摄入弹窗
  const [commentModalOpen, setCommentModalOpen] = useState(false)
  const [commentForm] = Form.useForm()
  const [batchMode, setBatchMode] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadOverview()
    }
  }, [projectId])

  const loadOverview = async () => {
    try {
      setLoading(true)
      await Promise.all([
        loadFeedbacks(),
        loadAnalysis(),
        loadAlerts()
      ])
    } catch (err) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const loadFeedbacks = async () => {
    try {
      setFeedbackLoading(true)
      const res = await audienceApi.getFeedback(Number(projectId))
      setFeedbacks(res.data || [])
    } catch (err) {
      console.error('加载反馈失败', err)
    } finally {
      setFeedbackLoading(false)
    }
  }

  const loadAnalysis = async () => {
    try {
      const res = await audienceApi.getAnalysis(Number(projectId))
      setAnalysis(res.data)
    } catch (err) {
      console.error('加载分析失败', err)
    }
  }

  const loadAlerts = async () => {
    try {
      const res = await audienceApi.getAlerts(Number(projectId))
      setAlerts(res.data || [])
    } catch (err) {
      console.error('加载告警失败', err)
    }
  }

  const loadSignals = async () => {
    try {
      const [arcRes, pacingRes, actionsRes] = await Promise.all([
        audienceApi.getArcDirectorSignals(Number(projectId)).catch(() => ({ data: null })),
        audienceApi.getPacingSignals(Number(projectId)).catch(() => ({ data: null })),
        audienceApi.getActionSuggestions(Number(projectId)).catch(() => ({ data: null }))
      ])
      setSignals({
        arc_director: arcRes.data,
        pacing: pacingRes.data,
        actions: actionsRes.data
      })
    } catch (err) {
      message.error('加载信号失败')
    }
  }

  const loadHintPack = async () => {
    try {
      const res = await audienceApi.getHintPack(Number(projectId))
      setHintPack(res.data)
    } catch (err) {
      message.error('加载提示包失败')
    }
  }

  const handleSubmitFeedback = async (values: any) => {
    try {
      setSubmitLoading(true)
      await audienceApi.submitFeedback(Number(projectId), {
        feedback_type: values.feedback_type,
        content: values.content,
        rating: values.rating,
        chapter_id: values.chapter_id
      })
      message.success('反馈提交成功')
      setSubmitModalOpen(false)
      submitForm.resetFields()
      loadFeedbacks()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '提交失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handleIngestComment = async (values: any) => {
    try {
      setSubmitLoading(true)
      const data = {
        project_id: Number(projectId),
        content: values.content,
        source: values.source,
        chapter_no: values.chapter_no
      }
      
      if (batchMode) {
        const comments = values.content.split('\n').filter((c: string) => c.trim())
        await audienceApi.ingestCommentsBatch(comments.map((c: string) => ({
          ...data,
          content: c.trim()
        })))
        message.success(`成功摄入 ${comments.length} 条评论`)
      } else {
        await audienceApi.ingestComment(data)
        message.success('评论摄入成功')
      }
      
      setCommentModalOpen(false)
      commentForm.resetFields()
      loadFeedbacks()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '摄入失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handleAnalyze = async () => {
    try {
      message.loading({ content: '正在分析评论...', key: 'analyze' })
      await audienceApi.analyzeComments(Number(projectId))
      message.success({ content: '分析完成', key: 'analyze' })
      loadAnalysis()
      loadSignals()
      loadHintPack()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '分析失败')
    }
  }

  const getAlertTypeTag = (type: string) => {
    const colors: Record<string, string> = {
      pacing: 'blue',
      coherence: 'purple',
      engagement: 'green',
      character: 'orange',
      plot: 'red'
    }
    return <Tag color={colors[type] || 'default'}>{type}</Tag>
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/projects/${projectId}`)} style={{ color: '#fff' }} />
          <Title level={4} style={{ color: '#fff', margin: 0 }}>读者反馈分析</Title>
        </Space>
        <Space style={{ marginLeft: 'auto' }}>
          <Button type="primary" icon={<ExperimentOutlined />} onClick={handleAnalyze}>
            重新分析
          </Button>
          <Button icon={<MessageOutlined />} onClick={() => setCommentModalOpen(true)}>
            摄入评论
          </Button>
        </Space>
      </Header>

      <Content style={{ padding: 24 }}>
        <Tabs activeKey={activeTab} onChange={(key) => {
          setActiveTab(key)
          if (key === 'signals') loadSignals()
          if (key === 'hints') loadHintPack()
        }}>
          <TabPane tab={<span><BarChartOutlined /> 分析概览</span>} key="overview">
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic title="总反馈数" value={feedbacks.length} prefix={<MessageOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic 
                    title="高置信度告警" 
                    value={alerts.filter(a => a.confidence >= 0.7).length} 
                    prefix={<BellOutlined />}
                    valueStyle={{ color: alerts.filter(a => a.confidence >= 0.7).length > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="平均评分" value={analysis?.average_rating?.toFixed(1) || 'N/A'} suffix="/ 5" />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="分析状态" value={analysis ? '已完成' : '待分析'} />
                </Card>
              </Col>
            </Row>

            <Card title="高置信度告警" style={{ marginTop: 24 }}>
              {alerts.length > 0 ? (
                <List
                  dataSource={alerts.filter(a => a.confidence >= 0.6)}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Badge status={item.confidence >= 0.8 ? 'error' : 'warning'} />}
                        title={
                          <Space>
                            {getAlertTypeTag(item.type)}
                            <Text strong>置信度: {Math.round(item.confidence * 100)}%</Text>
                          </Space>
                        }
                        description={item.description || item.message}
                      />
                      {item.suggestion && <Tag color="blue">{item.suggestion}</Tag>}
                    </List.Item>
                  )}
                />
              ) : (
                <Alert message="暂无告警" description="分析评论后将自动生成告警" type="info" showIcon />
              )}
            </Card>

            <Card title="最新反馈" style={{ marginTop: 24 }}>
              {feedbacks.length > 0 ? (
                <List
                  dataSource={feedbacks.slice(0, 5)}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Rate disabled defaultValue={item.rating || 0} style={{ fontSize: 12 }} />}
                        title={<Text>{item.feedback_type}</Text>}
                        description={item.content?.slice(0, 100)}
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Alert message="暂无反馈" description="摄入评论后将显示在这里" type="info" showIcon />
              )}
            </Card>
          </TabPane>

          <TabPane tab={<span><ThunderboltOutlined /> 创作信号</span>} key="signals">
            <Row gutter={16}>
              <Col span={8}>
                <Card 
                  title="Arc Director 信号" 
                  extra={<Tag color={signals?.arc_director?.status === 'expand' ? 'green' : signals?.arc_director?.status === 'compress' ? 'red' : 'default'}>
                    {signals?.arc_director?.status || 'N/A'}
                  </Tag>}
                >
                  {signals?.arc_director ? (
                    <div>
                      <Paragraph>{signals.arc_director.description}</Paragraph>
                      <Divider />
                      <Text type="secondary">置信度: {Math.round((signals.arc_director.confidence || 0) * 100)}%</Text>
                    </div>
                  ) : (
                    <Text type="secondary">暂无数据</Text>
                  )}
                </Card>
              </Col>
              <Col span={8}>
                <Card 
                  title="节奏信号" 
                  extra={<Tag color={signals?.pacing?.status === 'fast' ? 'orange' : signals?.pacing?.status === 'slow' ? 'blue' : 'default'}>
                    {signals?.pacing?.status || 'N/A'}
                  </Tag>}
                >
                  {signals?.pacing ? (
                    <div>
                      <Paragraph>{signals.pacing.description}</Paragraph>
                      <Divider />
                      <Text type="secondary">置信度: {Math.round((signals.pacing.confidence || 0) * 100)}%</Text>
                    </div>
                  ) : (
                    <Text type="secondary">暂无数据</Text>
                  )}
                </Card>
              </Col>
              <Col span={8}>
                <Card title="行为映射建议">
                  {signals?.actions ? (
                    <List
                      size="small"
                      dataSource={signals.actions.suggestions || []}
                      renderItem={(item: any) => (
                        <List.Item style={{ padding: '8px 0' }}>
                          <Space>
                            <Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'default'}>
                              {item.priority}
                            </Tag>
                            <Text>{item.action}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Text type="secondary">暂无数据</Text>
                  )}
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab={<span><WarningOutlined /> Writer提示包</span>} key="hints">
            <Card title="写作建议">
              {hintPack ? (
                <div>
                  {hintPack.improvements?.map((item: any, index: number) => (
                    <Card key={index} size="small" style={{ marginBottom: 16 }}>
                      <Space>
                        <Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'default'}>
                          {item.priority}
                        </Tag>
                        <Text strong>{item.area}</Text>
                      </Space>
                      <Paragraph style={{ marginTop: 8 }}>{item.suggestion}</Paragraph>
                    </Card>
                  ))}
                  
                  {hintPack.encouragements?.length > 0 && (
                    <>
                      <Divider>优点继续保持</Divider>
                      {hintPack.encouragements.map((item: any, index: number) => (
                        <Tag key={index} color="green" style={{ margin: 4 }}>{item}</Tag>
                      ))}
                    </>
                  )}
                </div>
              ) : (
                <Alert message="暂无提示包" description="分析评论后将生成Writer提示包" type="info" showIcon />
              )}
            </Card>
          </TabPane>

          <TabPane tab={<span><MessageOutlined /> 全部反馈</span>} key="feedbacks">
            <Button type="primary" onClick={() => setSubmitModalOpen(true)} style={{ marginBottom: 16 }}>
              提交反馈
            </Button>
            <Table
              dataSource={feedbacks}
              rowKey="id"
              loading={feedbackLoading}
              columns={[
                { title: '类型', dataIndex: 'feedback_type', width: 100 },
                { title: '内容', dataIndex: 'content', ellipsis: true },
                { title: '评分', dataIndex: 'rating', width: 80, render: (v) => <Rate disabled defaultValue={v || 0} style={{ fontSize: 12 }} /> },
                { title: '时间', dataIndex: 'created_at', width: 180 }
              ]}
            />
          </TabPane>
        </Tabs>
      </Content>

      <Modal
        title="提交反馈"
        open={submitModalOpen}
        onCancel={() => setSubmitModalOpen(false)}
        footer={null}
        width={600}
      >
        <Form form={submitForm} layout="vertical" onFinish={handleSubmitFeedback}>
          <Form.Item name="feedback_type" label="反馈类型" rules={[{ required: true, message: '请选择反馈类型' }]}>
            <Select>
              <Select.Option value="praise">赞美</Select.Option>
              <Select.Option value="suggestion">建议</Select.Option>
              <Select.Option value="complaint">投诉</Select.Option>
              <Select.Option value="question">问题</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="rating" label="评分">
            <Rate />
          </Form.Item>
          <Form.Item name="content" label="反馈内容" rules={[{ required: true, message: '请输入反馈内容' }]}>
            <Input.TextArea rows={4} placeholder="请输入您的反馈..." />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setSubmitModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={submitLoading}>提交</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="摄入评论"
        open={commentModalOpen}
        onCancel={() => setCommentModalOpen(false)}
        footer={null}
        width={700}
      >
        <Form form={commentForm} layout="vertical" onFinish={handleIngestComment}>
          <Form.Item>
            <Space>
              <Button type={batchMode ? 'default' : 'primary'} onClick={() => setBatchMode(false)}>单条摄入</Button>
              <Button type={batchMode ? 'primary' : 'default'} onClick={() => setBatchMode(true)}>批量摄入</Button>
            </Space>
          </Form.Item>
          <Form.Item name="source" label="来源" rules={[{ required: true, message: '请输入来源' }]}>
            <Input placeholder="如: 起点中文网评论区" />
          </Form.Item>
          <Form.Item name="content" label={batchMode ? '评论内容（每行一条）' : '评论内容'} rules={[{ required: true, message: '请输入评论内容' }]}>
            <Input.TextArea 
              rows={batchMode ? 10 : 4} 
              placeholder={batchMode ? "每行一条评论\n例:\n这本小说太好看了\n第三章有点水" : "请输入评论内容..."} 
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCommentModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={submitLoading}>
                {batchMode ? '批量摄入' : '摄入'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

export default AudienceFeedbackPage
