import { useState } from 'react'
import { Card, Form, Input, Button, message, Tabs, Switch, Divider, Typography, Space } from 'antd'
import { SaveOutlined, RollbackOutlined } from '@ant-design/icons'

const { Title, Text } = Typography
const { TextArea } = Input

// 默认 Prompts
const DEFAULT_PROMPTS = {
  planner: `你是一个专业的小说策划师。你的任务是：
1. 根据用户提供的原始 Prompt，设计完整的故事大纲
2. 创建故事圣经（Story Bible），包括世界观、角色设定、主题等
3. 规划章节结构，确保情节连贯、节奏合理

请输出结构化的 JSON 格式内容。`,

  writer: `你是一个专业的小说写作助手。你的任务是根据章节大纲和上下文，
创作引人入胜的小说章节。注意保持文笔流畅，情节紧凑，人物鲜活。

【重要】输出要求：
1. 只输出小说正文，不要输出任何思考过程、注释或元信息
2. 不要在正文中包含"<think>"、"## 大纲"等标记
3. 正文章节以章节标题开头
4. 章节长度建议在 2000-4000 字之间`,

  reviewer: `你是一个专业的小说编辑和批评家。
你的任务是审查小说章节并给出结构化的审查结果。

请审查以下方面：
- 一致性：角色、情节、世界观是否前后一致
- 节奏：情节推进是否合理，有无拖沓
- 钩子：开头是否有吸引力，能否让读者继续阅读

请输出 JSON 格式的审查结果。`,

  memory: `你是一个小说世界观专家。你的任务是：
1. 从章节内容中提取和更新角色状态
2. 管理伏笔记录
3. 维护故事的连续性

请确保提取的信息准确、结构化。`,

  orchestrator: `你是一个写作编排器。你的任务是：
1. 协调多个 Agent 的工作流程
2. 管理任务队列
3. 确保多项目并行处理时的隔离性

请遵循项目配置中的规划参数。`
}

const AgentPromptsPage = () => {
  const [customPrompts, setCustomPrompts] = useState(() => {
    const saved = localStorage.getItem('agent_prompts')
    return saved ? JSON.parse(saved) : DEFAULT_PROMPTS
  })
  const [useCustomPrompts, setUseCustomPrompts] = useState(
    () => localStorage.getItem('use_custom_prompts') === 'true'
  )
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('planner')

  // 根据开关状态决定使用哪个prompt
  const currentPrompts = useCustomPrompts ? customPrompts : DEFAULT_PROMPTS

  const handleSave = () => {
    setSaving(true)
    localStorage.setItem('agent_prompts', JSON.stringify(customPrompts))
    localStorage.setItem('use_custom_prompts', String(useCustomPrompts))
    setTimeout(() => {
      setSaving(false)
      message.success('Prompt 配置已保存')
    }, 500)
  }

  const handleReset = () => {
    setCustomPrompts(DEFAULT_PROMPTS)
    message.info('已恢复默认配置')
  }

  const updatePrompt = (agent: string, value: string) => {
    // 如果当前使用默认prompts，切换到自定义模式
    if (!useCustomPrompts) {
      setUseCustomPrompts(true)
    }
    setCustomPrompts((prev: typeof customPrompts) => ({ ...prev, [agent]: value }))
  }

  const agentInfo: Record<string, { title: string; desc: string; color: string }> = {
    planner: { 
      title: 'Planner (策划师)', 
      desc: '负责生成 Story Bible、规划章节结构、设计世界观和角色',
      color: '#1890ff'
    },
    writer: { 
      title: 'Writer (写作师)', 
      desc: '根据大纲和上下文生成小说正文',
      color: '#52c41a'
    },
    reviewer: { 
      title: 'Reviewer (审查师)', 
      desc: '审查章节质量，检查一致性、节奏、钩子',
      color: '#faad14'
    },
    memory: { 
      title: 'Memory (记忆师)', 
      desc: '管理角色状态、伏笔记录、故事连续性',
      color: '#722ed1'
    },
    orchestrator: { 
      title: 'Orchestrator (编排器)', 
      desc: '协调工作流程、管理任务队列、多项目隔离',
      color: '#eb2f96'
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={3}>Agent Prompt 配置</Title>
          <Text type="secondary">自定义每个 AI Agent 的系统提示词</Text>
        </div>
        <Space>
          <Switch 
            checked={useCustomPrompts} 
            onChange={setUseCustomPrompts}
            checkedChildren="自定义"
            unCheckedChildren="默认"
          />
          <Button icon={<RollbackOutlined />} onClick={handleReset}>
            恢复默认
          </Button>
          <Button 
            type="primary" 
            icon={<SaveOutlined />} 
            onClick={handleSave}
            loading={saving}
          >
            保存配置
          </Button>
        </Space>
      </div>

      <Tabs 
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key)}
        items={Object.entries(agentInfo).map(([key, info]) => ({
        key,
        label: <span style={{ color: info.color }}>{info.title}</span>,
        children: (
          <Card 
            title={info.title} 
            extra={<Text type="secondary">{info.desc}</Text>}
            style={{ borderColor: info.color }}
          >
            <Form layout="vertical">
              <Form.Item 
                label="系统提示词"
                help="定义 Agent 的角色定位和行为规则"
              >
                <TextArea
                  rows={12}
                  value={currentPrompts[key]}
                  onChange={e => updatePrompt(key, e.target.value)}
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
              <Divider />
              <Text type="secondary" style={{ fontSize: 12 }}>
                字数: {currentPrompts[key].length} | 
                建议: 100-500 字 | 
                包含 JSON 输出格式要求可提高稳定性
              </Text>
            </Form>
          </Card>
        )
      }))} />

      <Card style={{ marginTop: 24, background: '#fafafa' }}>
        <Title level={5}>使用说明</Title>
        <ul style={{ color: '#666' }}>
          <li><strong>Planner</strong>: 项目初始化时调用，生成故事大纲和设定</li>
          <li><strong>Writer</strong>: 每次生成/续写章节时调用</li>
          <li><strong>Reviewer</strong>: 章节审查时调用，可设置审查维度</li>
          <li><strong>Memory</strong>: 上下文构建时调用，影响生成内容的一致性</li>
          <li><strong>Orchestrator</strong>: 工作流编排使用，当前端配置</li>
        </ul>
        <Text type="warning">
          ⚠️ 修改 Prompt 可能影响生成质量，请谨慎调整
        </Text>
      </Card>
    </div>
  )
}

export default AgentPromptsPage
