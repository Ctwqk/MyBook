import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Row, Col, List, Tag, Spin, Input, Button, Space } from 'antd'
import { memoryApi } from '../api'

const { Search } = Input

const MemoryPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [storyBible, setStoryBible] = useState<any>(null)
  const [foreshadows, setForeshadows] = useState<any[]>([])
  const [searchResults, setSearchResults] = useState<any[]>([])

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
      setForeshadows(foreshadowRes.data)
    } catch (err) {
      console.error('加载失败', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (query: string) => {
    if (!query) return
    try {
      const res = await memoryApi.search(Number(projectId), { query, limit: 20 })
      setSearchResults(res.data.results)
    } catch (err) {
      console.error('搜索失败', err)
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
                <hr />
                <p><strong>概述:</strong></p>
                <div style={{ whiteSpace: 'pre-wrap' }}>{storyBible.synopsis || '待填充'}</div>
                <hr />
                <p><strong>世界观:</strong></p>
                <div style={{ whiteSpace: 'pre-wrap' }}>{storyBible.world_overview || '待填充'}</div>
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
            <p style={{ color: '#999' }}>点击构建按钮生成当前上下文</p>
            <Button
              onClick={async () => {
                try {
                  const res = await memoryApi.buildContextPack(Number(projectId), {
                    include_story_bible: true,
                    include_character_states: true,
                    include_recent_chapters: 3,
                    include_foreshadows: true,
                  })
                  console.log('Context Pack:', res.data)
                  alert('上下文包已生成，请查看控制台')
                } catch (err) {
                  console.error('构建失败', err)
                }
              }}
            >
              构建上下文包
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default MemoryPage
