import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Row, Col, List, Tag, Spin, Input, Button, Space, Modal, message } from 'antd'
import { memoryApi } from '../api'

const { Search } = Input

const MemoryPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [storyBible, setStoryBible] = useState<any>(null)
  const [foreshadows, setForeshadows] = useState<any[]>([])
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [contextPackVisible, setContextPackVisible] = useState(false)
  const [contextPackLoading, setContextPackLoading] = useState(false)
  const [contextPackData, setContextPackData] = useState<any>(null)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [bibleRes, foreshadowRes] = await Promise.all([
        memoryApi.getStoryBible(Number(projectId)),
        memoryApi.getForeshadows(Number(projectId)),
      ])
      setStoryBible(bibleRes.data)
      setForeshadows(foreshadowRes.data || [])
    } catch (err) {
      console.error('加载失败', err)
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (query: string) => {
    if (!query) return
    try {
      const res = await memoryApi.search(Number(projectId), { query, limit: 20 })
      setSearchResults(res.data.results || [])
    } catch (err) {
      console.error('搜索失败', err)
      message.error('搜索失败')
    }
  }

  const handleBuildContextPack = async () => {
    setContextPackLoading(true)
    setContextPackVisible(true)
    try {
      const res = await memoryApi.buildContextPack(Number(projectId), {
        include_story_bible: true,
        include_character_states: true,
        include_recent_chapters: 3,
        include_foreshadows: true,
      })
      setContextPackData(res.data)
      message.success('上下文包构建成功')
    } catch (err: any) {
      console.error('构建上下文包失败', err)
      message.error(err.response?.data?.detail || '构建上下文包失败')
      setContextPackVisible(false)
    } finally {
      setContextPackLoading(false)
    }
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>记忆库</h1>
        <Button onClick={() => navigate(`/projects/${projectId}`)}>返回创作台</Button>
      </div>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="故事设定">
            {storyBible ? (
              <div>
                <p><strong>主题:</strong> {storyBible.theme || '待填充'}</p>
                <p><strong>基调:</strong> {storyBible.tone || '待填充'}</p>
                <p><strong>目标读者:</strong> {storyBible.target_audience || '待填充'}</p>
                <hr style={{ margin: '12px 0', borderColor: '#f0f0f0' }} />
                <p><strong>概述:</strong></p>
                <div style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 4 }}>
                  {storyBible.synopsis || '待填充'}
                </div>
                <hr style={{ margin: '12px 0', borderColor: '#f0f0f0' }} />
                <p><strong>世界观:</strong></p>
                <div style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 4 }}>
                  {storyBible.world_overview || '待填充'}
                </div>
              </div>
            ) : (
              <p style={{ color: '#999' }}>暂无故事设定</p>
            )}
          </Card>

          <Card title="伏笔" style={{ marginTop: 16 }}>
            <List
              dataSource={foreshadows}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={item.content}
                    description={
                      <Space>
                        <Tag>{item.status}</Tag>
                        {item.planned_resolution && <span>计划: {item.planned_resolution}</span>}
                      </Space>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无伏笔' }}
            />
          </Card>
        </Col>

        <Col span={12}>
          <Card title="记忆搜索">
            <Search
              placeholder="搜索记忆..."
              allowClear
              onSearch={handleSearch}
              style={{ marginBottom: 16 }}
            />
            <List
              dataSource={searchResults}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={<Tag>{item.type}</Tag>}
                    description={item.content?.slice(0, 100)}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '输入关键词搜索记忆' }}
            />
          </Card>

          <Card title="上下文包预览" style={{ marginTop: 16 }}>
            <p style={{ color: '#666', marginBottom: 12 }}>点击构建按钮生成当前项目的上下文信息</p>
            <Button
              type="primary"
              onClick={handleBuildContextPack}
              loading={contextPackLoading}
            >
              构建上下文包
            </Button>
          </Card>
        </Col>
      </Row>

      {/* 上下文包预览弹窗 */}
      <Modal
        title="上下文包预览"
        open={contextPackVisible}
        onCancel={() => setContextPackVisible(false)}
        footer={
          <Button type="primary" onClick={() => setContextPackVisible(false)}>
            关闭
          </Button>
        }
        width={800}
      >
        {contextPackData ? (
          <div style={{ maxHeight: 500, overflow: 'auto' }}>
            <h3>格式化上下文</h3>
            <pre style={{ 
              whiteSpace: 'pre-wrap', 
              background: '#fafafa', 
              padding: 16, 
              borderRadius: 4,
              maxHeight: 400,
              overflow: 'auto'
            }}>
              {contextPackData.formatted_context || '暂无上下文'}
            </pre>
            
            {contextPackData.story_bible && (
              <>
                <h3 style={{ marginTop: 16 }}>故事设定</h3>
                <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(contextPackData.story_bible, null, 2)}
                </pre>
              </>
            )}
            
            {contextPackData.character_states && contextPackData.character_states.length > 0 && (
              <>
                <h3 style={{ marginTop: 16 }}>角色状态</h3>
                <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(contextPackData.character_states, null, 2)}
                </pre>
              </>
            )}
            
            {contextPackData.foreshadows && contextPackData.foreshadows.length > 0 && (
              <>
                <h3 style={{ marginTop: 16 }}>伏笔</h3>
                <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(contextPackData.foreshadows, null, 2)}
                </pre>
              </>
            )}
          </div>
        ) : (
          <Spin tip="正在构建上下文包..." />
        )}
      </Modal>
    </div>
  )
}

export default MemoryPage
