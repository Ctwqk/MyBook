import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Card, Button, Space, Spin, message, Table, Tag, Progress, Modal, Descriptions, Typography, Alert, Row, Col, Statistic } from 'antd'
import { ArrowLeftOutlined, ThunderboltOutlined, ExperimentOutlined, CompressOutlined, ExpandOutlined } from '@ant-design/icons'
import { arcApi } from '../api'

const { Header, Content } = Layout
const { Text, Title } = Typography

// 分档配置
const tierConfig: Record<string, { label: string; color: string; ratio: string }> = {
  short: { label: '短篇', color: 'green', ratio: '≤50章' },
  medium: { label: '中篇', color: 'cyan', ratio: '51-100章' },
  long: { label: '长篇', color: 'blue', ratio: '101-200章' },
  ultra_long: { label: '超长篇', color: 'purple', ratio: '>200章' },
}

// 置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'error'
}

const ArcPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  
  const [loading, setLoading] = useState(true)
  const [tierInfo, setTierInfo] = useState<any>(null)
  const [arcs, setArcs] = useState<any[]>([])
  const [previewData, setPreviewData] = useState<any[]>([])
  const [selectedArc, setSelectedArc] = useState<any>(null)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [activating, setActivating] = useState<number | null>(null)
  const [adjusting, setAdjusting] = useState<{ arcNo: number; action: string } | null>(null)

  useEffect(() => {
    if (projectId) {
      loadData()
    }
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // 分别请求，设置合理的超时处理
      const tierPromise = arcApi.getProjectTier(Number(projectId))
        .catch(() => ({ data: null }));
      const arcsPromise = arcApi.getProjectArcs(Number(projectId))
        .catch(() => ({ data: [] }));
      const previewPromise = arcApi.previewArcs(Number(projectId))
        .catch(() => ({ data: [] }));
      
      // 添加超时控制，避免长时间等待
      const timeoutPromise = new Promise((resolve) => {
        setTimeout(() => resolve({ data: [] }), 10000); // 10秒超时
      });
      
      const [tierRes, arcsRes]: [any, any] = await Promise.all([
        Promise.race([tierPromise, timeoutPromise]).then((r: any) => r?.data ? r : { data: null }),
        Promise.race([arcsPromise, timeoutPromise]).then((r: any) => r?.data ? r : { data: [] }),
      ]);
      
      // 预览数据单独加载
      const previewData = await Promise.race([previewPromise, timeoutPromise]).then((r: any) => r?.data || []);
      
      setTierInfo(tierRes?.data)
      setArcs(arcsRes?.data || [])
      setPreviewData(previewData)
    } catch (err) {
      message.error('加载Arc信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleActivateArc = async (arcNo: number) => {
    try {
      setActivating(arcNo)
      message.loading({ content: '正在激活Arc...', key: 'activate' })
      await arcApi.activateArc(Number(projectId), arcNo)
      message.success({ content: 'Arc激活成功', key: 'activate' })
      loadData()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '激活失败')
    } finally {
      setActivating(null)
    }
  }

  const handleAdjustArc = async (arcNo: number, adjustment: 'expand' | 'compress' | 'keep') => {
    try {
      setAdjusting({ arcNo, action: adjustment })
      message.loading({ content: `正在${adjustment === 'expand' ? '扩张' : adjustment === 'compress' ? '压缩' : '保持'}Arc...`, key: 'adjust' })
      await arcApi.adjustArc(Number(projectId), arcNo, adjustment)
      message.success({ content: '调整完成', key: 'adjust' })
      setDetailModalOpen(false)
      loadData()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '调整失败')
    } finally {
      setAdjusting(null)
    }
  }

  const showArcDetail = (arc: any) => {
    setSelectedArc(arc)
    setDetailModalOpen(true)
  }

  const showPreview = () => {
    setPreviewModalOpen(true)
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  const tierInfoDisplay = tierInfo ? tierConfig[tierInfo.tier] : null

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      {/* 顶部导航 */}
      <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/projects/${projectId}`)} style={{ color: '#fff' }} />
          <Title level={4} style={{ color: '#fff', margin: 0 }}>Arc 管理</Title>
        </Space>
      </Header>

      <Content style={{ padding: 24 }}>
        {/* 项目分档信息 */}
        {tierInfoDisplay && (
          <Card style={{ marginBottom: 24 }}>
            <Row gutter={24} align="middle">
              <Col>
                <Statistic 
                  title="项目分档" 
                  value={tierInfoDisplay.label} 
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: tierInfoDisplay.color }}
                />
              </Col>
              <Col>
                <Statistic title="章节范围" value={tierInfoDisplay.ratio} />
              </Col>
              <Col>
                <Statistic title="目标比例" value={tierInfo?.ratio || 'N/A'} suffix="%" />
              </Col>
              <Col>
                <Statistic title="软下限倍数" value={tierInfo?.soft_min_mult || 'N/A'} />
              </Col>
              <Col>
                <Statistic title="软上限倍数" value={tierInfo?.soft_max_mult || 'N/A'} />
              </Col>
            </Row>
          </Card>
        )}

        {/* Arc列表 */}
        <Card 
          title={
            <Space>
              <span>已激活的 Arc</span>
              <Tag>{arcs.length}</Tag>
            </Space>
          }
          extra={
            <Button type="primary" icon={<ExperimentOutlined />} onClick={showPreview}>
              预览 Arc 规划
            </Button>
          }
        >
          {arcs.length > 0 ? (
            <Table
              dataSource={arcs}
              rowKey="id"
              pagination={false}
              onRow={(record) => ({
                onClick: () => showArcDetail(record),
                style: { cursor: 'pointer' }
              })}
              columns={[
                {
                  title: 'Arc编号',
                  dataIndex: 'arc_no',
                  width: 100,
                  render: (no: number) => <Tag color="blue">Arc {no}</Tag>
                },
                {
                  title: '基础目标',
                  dataIndex: 'base_target_size',
                  width: 120,
                  render: (val: number) => val ? `${val}章` : '-'
                },
                {
                  title: '解析目标',
                  dataIndex: 'resolved_target_size',
                  width: 120,
                  render: (val: number) => val ? `${val}章` : '-'
                },
                {
                  title: '软范围',
                  width: 200,
                  render: (_, record) => (
                    <span>
                      {record.resolved_soft_min || 0} - {record.resolved_soft_max || 0} 章
                    </span>
                  )
                },
                {
                  title: '详细范围',
                  dataIndex: 'resolved_detailed_band_size',
                  width: 120,
                  render: (val: number) => val ? `${val}章` : '-'
                },
                {
                  title: '冻结区',
                  dataIndex: 'resolved_frozen_zone_size',
                  width: 100,
                  render: (val: number) => val ? `${val}章` : '-'
                },
                {
                  title: '预估进度',
                  width: 200,
                  render: (_, record) => {
                    const projected = record.current_projected_size || 0
                    const target = record.resolved_target_size || 1
                    const percent = Math.min(100, Math.round((projected / target) * 100))
                    return (
                      <Progress 
                        percent={percent} 
                        size="small"
                        status={percent >= 100 ? 'success' : 'active'}
                        format={() => `${projected}/${target}章`}
                      />
                    )
                  }
                },
                {
                  title: '置信度',
                  dataIndex: 'current_confidence',
                  width: 100,
                  render: (val: number) => val ? (
                    <Tag color={getConfidenceColor(val)}>{Math.round(val * 100)}%</Tag>
                  ) : '-'
                },
                {
                  title: '状态',
                  dataIndex: 'envelope_status',
                  width: 100,
                  render: (status: string) => {
                    const statusMap: Record<string, { color: string; text: string }> = {
                      pending: { color: 'default', text: '待激活' },
                      provisional: { color: 'processing', text: '预演中' },
                      active: { color: 'success', text: '激活' },
                      frozen: { color: 'warning', text: '冻结' },
                    }
                    const s = statusMap[status] || { color: 'default', text: status }
                    return <Tag color={s.color}>{s.text}</Tag>
                  }
                },
              ]}
            />
          ) : (
            <Alert
              message="暂无已激活的 Arc"
              description="请先在项目设置中规划 Arc，然后点击「预览 Arc 规划」查看预估结果，再逐个激活。"
              type="info"
              showIcon
            />
          )}
        </Card>

        {/* 使用说明 */}
        <Card title="使用指南" style={{ marginTop: 24 }}>
          <Row gutter={[24, 16]}>
            <Col span={8}>
              <Card size="small" title="1. 规划 Arc" extra={<ExperimentOutlined />}>
                在项目设置中规划故事的主要情节线（Arc），系统会自动计算每个Arc的目标章节数。
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="2. 预览规划" extra={<ExpandOutlined />}>
                点击「预览 Arc 规划」查看预估的章节分配，了解各Arc在当前分档下的软硬范围。
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="3. 激活 Arc" extra={<ThunderboltOutlined />}>
                确认规划后，逐个激活 Arc，系统会执行三层计算并锁定目标范围。
              </Card>
            </Col>
          </Row>
          <Row gutter={[24, 16]} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Card size="small" title="扩张/压缩信号" extra={<ExpandOutlined />}>
                当 AI 检测到情节发展需要更多/更少章节时，会发送扩张或压缩信号，可手动调整目标范围。
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="三层计算机制" extra={<CompressOutlined />}>
                <Text>
                  <b>Layer 1:</b> 百分比 + 上下限 | 
                  <b>Layer 2:</b> 分档调整 | 
                  <b>Layer 3:</b> Provisional 预演
                </Text>
              </Card>
            </Col>
          </Row>
        </Card>
      </Content>

      {/* Arc详情弹窗 */}
      <Modal
        title={<Space><Tag color="blue">Arc {selectedArc?.arc_no}</Tag> 详细信息</Space>}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>关闭</Button>,
          <Button 
            key="expand" 
            icon={<ExpandOutlined />}
            onClick={() => handleAdjustArc(selectedArc?.arc_no, 'expand')}
            loading={adjusting?.arcNo === selectedArc?.arc_no && adjusting?.action === 'expand'}
          >
            扩张(+15%)
          </Button>,
          <Button 
            key="compress" 
            icon={<CompressOutlined />}
            onClick={() => handleAdjustArc(selectedArc?.arc_no, 'compress')}
            loading={adjusting?.arcNo === selectedArc?.arc_no && adjusting?.action === 'compress'}
          >
            压缩(-15%)
          </Button>,
          selectedArc?.envelope_status === 'active' && (
            <Button 
              key="keep"
              onClick={() => handleAdjustArc(selectedArc?.arc_no, 'keep')}
              loading={adjusting?.arcNo === selectedArc?.arc_no && adjusting?.action === 'keep'}
            >
              保持不变
            </Button>
          ),
        ]}
        width={700}
      >
        {selectedArc && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="基础目标">{selectedArc.base_target_size} 章</Descriptions.Item>
            <Descriptions.Item label="基础比例">{selectedArc.base_ratio || '-'}%</Descriptions.Item>
            <Descriptions.Item label="解析目标" span={2}>{selectedArc.resolved_target_size} 章</Descriptions.Item>
            <Descriptions.Item label="软范围">{selectedArc.resolved_soft_min} - {selectedArc.resolved_soft_max} 章</Descriptions.Item>
            <Descriptions.Item label="详细范围">{selectedArc.resolved_detailed_band_size} 章</Descriptions.Item>
            <Descriptions.Item label="冻结区">{selectedArc.resolved_frozen_zone_size} 章</Descriptions.Item>
            <Descriptions.Item label="预估进度">{selectedArc.current_projected_size} 章</Descriptions.Item>
            <Descriptions.Item label="置信度">
              <Tag color={getConfidenceColor(selectedArc.current_confidence)}>
                {Math.round(selectedArc.current_confidence * 100)}%
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="来源策略分档">{selectedArc.source_policy_tier}</Descriptions.Item>
            <Descriptions.Item label="计算时总章节">{selectedArc.total_chapters_at_calculation}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 预览弹窗 */}
      <Modal
        title="Arc 规划预览"
        open={previewModalOpen}
        onCancel={() => setPreviewModalOpen(false)}
        footer={null}
        width={900}
      >
        <Table
          dataSource={previewData}
          rowKey="arc_no"
          pagination={false}
          columns={[
            {
              title: 'Arc',
              dataIndex: 'arc_no',
              width: 80,
              render: (no: number) => <Tag color="blue">Arc {no}</Tag>
            },
            {
              title: '分档',
              dataIndex: 'tier',
              width: 100,
              render: (tier: string) => tierConfig[tier]?.label || tier
            },
            {
              title: '基础目标',
              dataIndex: 'base_target',
              width: 100,
              render: (val: number) => val ? `${val}章` : '-'
            },
            {
              title: '解析目标',
              dataIndex: 'resolved_target',
              width: 100,
              render: (val: number) => val ? `${val}章` : '-'
            },
            {
              title: '软范围',
              dataIndex: 'soft_range',
              width: 150,
              render: (range: string) => range || '-'
            },
            {
              title: '详细范围',
              dataIndex: 'detailed_band',
              width: 100,
              render: (val: number) => val ? `${val}章` : '-'
            },
            {
              title: '冻结区',
              dataIndex: 'frozen_zone',
              width: 100,
              render: (val: number) => val ? `${val}章` : '-'
            },
            {
              title: '建议',
              dataIndex: 'recommendation',
              width: 120,
              render: (rec: string) => rec ? <Tag>{rec}</Tag> : '-'
            },
            {
              title: '置信度',
              dataIndex: 'confidence',
              width: 100,
              render: (val: number) => val ? (
                <Progress 
                  percent={Math.round(val * 100)} 
                  size="small"
                  status={val >= 0.8 ? 'success' : val >= 0.6 ? 'normal' : 'exception'}
                />
              ) : '-'
            },
            {
              title: '操作',
              width: 100,
              render: (_, record) => (
                <Button 
                  size="small" 
                  type="primary"
                  loading={activating === record.arc_no}
                  onClick={() => handleActivateArc(record.arc_no)}
                >
                  激活
                </Button>
              )
            },
          ]}
        />
      </Modal>
    </Layout>
  )
}

export default ArcPage
