import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Card, Button, Space, Spin, message, Tag, Tabs, Modal, Form, Input, Alert, Row, Col, Statistic, Typography, Steps, QRCode, List } from 'antd'
import { ArrowLeftOutlined, LoginOutlined, LogoutOutlined, QrcodeOutlined, KeyOutlined, MobileOutlined, TrophyOutlined, GlobalOutlined } from '@ant-design/icons'
import { publishApi } from '../api'

const { Header, Content } = Layout
const { Text, Title, Paragraph } = Typography
const { TabPane } = Tabs
const { TextArea } = Input

// 平台列表
const platforms = [
  { id: 'qidian', name: '起点中文网', icon: '📚', color: '#c20c0c' },
  { id: 'zongheng', name: '纵横中文网', icon: '🌐', color: '#1a73e8' },
  { id: 'chuangshi', name: '创世中文网', icon: '✨', color: '#f57c00' },
  { id: 'qidianm', name: '起点女生网', icon: '🌸', color: '#e91e63' },
  { id: 'jinjiang', name: '晋江文学城', icon: '🌺', color: '#9c27b0' },
]

const PlatformAccountsPage = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('accounts')
  
  // 平台账号列表
  const [accounts, setAccounts] = useState<any[]>([])
  
  // 登录弹窗状态
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [loginType, setLoginType] = useState<'qr' | 'password' | 'sms' | 'cookie'>('qr')
  const [selectedPlatform, setSelectedPlatform] = useState<string>('')
  const [loginForm] = Form.useForm()
  const [loginLoading, setLoginLoading] = useState(false)
  
  // 二维码登录状态
  const [qrSessionId, setQrSessionId] = useState<string>('')
  const [qrStatus, setQrStatus] = useState<'pending' | 'scanned' | 'confirmed' | 'expired'>('pending')

  useEffect(() => {
    if (projectId) {
      loadAccounts()
    }
  }, [projectId])

  const loadAccounts = async () => {
    try {
      setLoading(true)
      // 模拟账号列表数据
      setAccounts([
        { id: '1', platform: 'qidian', platform_name: '起点中文网', status: 'active', last_login: '2024-01-15 10:30:00' },
        { id: '2', platform: 'chuangshi', platform_name: '创世中文网', status: 'active', last_login: '2024-01-14 15:20:00' },
      ])
    } catch (err) {
      console.error('加载账号失败', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (values: any) => {
    try {
      setLoginLoading(true)
      
      if (loginType === 'qr') {
        // 二维码登录
        message.loading({ content: '正在生成二维码...', key: 'qr' })
        const sessionId = `session_${Date.now()}`
        setQrSessionId(sessionId)
        setQrStatus('pending')
        message.success({ content: '二维码已生成，请在30秒内扫描', key: 'qr' })
        
        // 模拟轮询二维码状态
        let attempts = 0
        const pollInterval = setInterval(async () => {
          attempts++
          if (attempts > 30) {
            setQrStatus('expired')
            clearInterval(pollInterval)
            return
          }
          
          if (qrStatus === 'pending' && attempts > 5) {
            setQrStatus('scanned')
          }
          if (qrStatus === 'scanned' && attempts > 10) {
            setQrStatus('confirmed')
            clearInterval(pollInterval)
            message.success('登录成功')
            setLoginModalOpen(false)
            loadAccounts()
          }
        }, 1000)
        
      } else if (loginType === 'password') {
        // 密码登录
        await publishApi.loginWithPassword({
          platform: selectedPlatform,
          username: values.username,
          password: values.password
        })
        message.success('登录成功')
        setLoginModalOpen(false)
        loadAccounts()
        
      } else if (loginType === 'sms') {
        // 短信登录
        if (values.action === 'send') {
          await publishApi.sendSmsCode({
            platform: selectedPlatform,
            phone: values.phone
          })
          message.success('验证码已发送')
        } else {
          await publishApi.verifySmsCode({
            platform: selectedPlatform,
            phone: values.phone,
            code: values.code
          })
          message.success('登录成功')
          setLoginModalOpen(false)
          loadAccounts()
        }
        
      } else if (loginType === 'cookie') {
        // Cookie登录
        await publishApi.loginWithCookie({
          platform: selectedPlatform,
          cookies: values.cookies
        })
        message.success('登录成功')
        setLoginModalOpen(false)
        loadAccounts()
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '登录失败')
    } finally {
      setLoginLoading(false)
    }
  }

  const handleLogout = async (accountId: string) => {
    try {
      await publishApi.logout(accountId)
      message.success('已退出登录')
      loadAccounts()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '退出失败')
    }
  }

  const openLoginModal = (platform: string) => {
    setSelectedPlatform(platform)
    setLoginModalOpen(true)
    setLoginType('qr')
    loginForm.resetFields()
  }

  const getPlatformInfo = (platformId: string) => {
    return platforms.find(p => p.id === platformId) || { name: platformId, icon: '🌐', color: '#666' }
  }

  const getStatusTag = (status: string) => {
    return <Tag color={status === 'active' ? 'success' : 'error'}>{status === 'active' ? '在线' : '离线'}</Tag>
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      {/* 顶部导航 */}
      <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/projects/${projectId}/publish`)} style={{ color: '#fff' }} />
          <Title level={4} style={{ color: '#fff', margin: 0 }}>平台账号管理</Title>
        </Space>
      </Header>

      <Content style={{ padding: 24 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 账号管理 */}
          <TabPane tab={<span><KeyOutlined /> 账号列表</span>} key="accounts">
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic title="已绑定平台" value={accounts.length} prefix={<GlobalOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="在线账号" value={accounts.filter(a => a.status === 'active').length} prefix={<TrophyOutlined />} valueStyle={{ color: '#3f8600' }} />
                </Card>
              </Col>
            </Row>

            {/* 账号列表 */}
            <Card title="已登录账号" style={{ marginTop: 24 }}>
              {accounts.length > 0 ? (
                <List
                  dataSource={accounts}
                  renderItem={(item: any) => {
                    const platform = getPlatformInfo(item.platform)
                    return (
                      <List.Item
                        actions={[
                          <Button key="logout" danger icon={<LogoutOutlined />} onClick={() => handleLogout(item.id)}>
                            退出
                          </Button>
                        ]}
                      >
                        <List.Item.Meta
                          avatar={<div style={{ fontSize: 32 }}>{platform.icon}</div>}
                          title={
                            <Space>
                              <Text strong>{platform.name}</Text>
                              {getStatusTag(item.status)}
                            </Space>
                          }
                          description={`最后登录: ${item.last_login}`}
                        />
                      </List.Item>
                    )
                  }}
                />
              ) : (
                <Alert message="暂无已登录账号" description="请从下方选择平台进行登录" type="info" showIcon />
              )}
            </Card>

            {/* 平台列表 */}
            <Card title="可登录平台" style={{ marginTop: 24 }}>
              <Row gutter={[16, 16]}>
                {platforms.map((platform) => (
                  <Col span={8} key={platform.id}>
                    <Card 
                      hoverable
                      onClick={() => openLoginModal(platform.id)}
                      style={{ borderColor: platform.color, borderWidth: 2 }}
                    >
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 48 }}>{platform.icon}</div>
                        <Title level={5} style={{ marginTop: 8 }}>{platform.name}</Title>
                        <Button type="primary" icon={<LoginOutlined />} style={{ background: platform.color, borderColor: platform.color }}>
                          登录
                        </Button>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </TabPane>

          {/* 登录方式 */}
          <TabPane tab={<span><LoginOutlined /> 登录方式</span>} key="methods">
            <Row gutter={24}>
              <Col span={6}>
                <Card 
                  title={<Space><QrcodeOutlined /> 二维码登录</Space>}
                  extra={<Tag>推荐</Tag>}
                  hoverable
                  onClick={() => { setLoginType('qr'); setLoginModalOpen(true) }}
                >
                  <Paragraph>使用平台App扫描二维码登录</Paragraph>
                  <ul>
                    <li>安全便捷</li>
                    <li>无需输入密码</li>
                    <li>支持所有平台</li>
                  </ul>
                </Card>
              </Col>
              <Col span={6}>
                <Card 
                  title={<Space><KeyOutlined /> 密码登录</Space>}
                  hoverable
                  onClick={() => { setLoginType('password'); setLoginModalOpen(true) }}
                >
                  <Paragraph>使用用户名密码登录</Paragraph>
                  <ul>
                    <li>传统登录方式</li>
                    <li>需要验证码</li>
                    <li>支持记忆密码</li>
                  </ul>
                </Card>
              </Col>
              <Col span={6}>
                <Card 
                  title={<Space><MobileOutlined /> 短信登录</Space>}
                  hoverable
                  onClick={() => { setLoginType('sms'); setLoginModalOpen(true) }}
                >
                  <Paragraph>使用手机号验证码登录</Paragraph>
                  <ul>
                    <li>无需注册</li>
                    <li>接收短信验证码</li>
                    <li>适合海外用户</li>
                  </ul>
                </Card>
              </Col>
              <Col span={6}>
                <Card 
                  title={<Space><GlobalOutlined /> Cookie登录</Space>}
                  hoverable
                  onClick={() => { setLoginType('cookie'); setLoginModalOpen(true) }}
                >
                  <Paragraph>导入浏览器Cookie登录</Paragraph>
                  <ul>
                    <li>保持会话状态</li>
                    <li>适合已登录用户</li>
                    <li>需要手动导出Cookie</li>
                  </ul>
                </Card>
              </Col>
            </Row>
          </TabPane>

          {/* 帮助 */}
          <TabPane tab={<span><GlobalOutlined /> 使用帮助</span>} key="help">
            <Card title="登录方式说明">
              <Steps direction="vertical" current={0}>
                <Steps.Step 
                  title="二维码登录（推荐）"
                  description={
                    <div>
                      <Paragraph>1. 选择要登录的平台</Paragraph>
                      <Paragraph>2. 点击"生成二维码"</Paragraph>
                      <Paragraph>3. 打开对应平台的App，扫描二维码</Paragraph>
                      <Paragraph>4. 在App中确认登录</Paragraph>
                      <Alert message="二维码有效期为30秒，请尽快扫描" type="info" />
                    </div>
                  }
                />
                <Steps.Step 
                  title="密码登录"
                  description="输入平台账号的用户名和密码完成登录"
                />
                <Steps.Step 
                  title="短信登录"
                  description="输入手机号，接收并填写验证码完成登录"
                />
                <Steps.Step 
                  title="Cookie登录"
                  description={
                    <div>
                      <Paragraph>1. 在浏览器中登录平台</Paragraph>
                      <Paragraph>2. 打开开发者工具 (F12)</Paragraph>
                      <Paragraph>3. 复制 Network 标签中的 Cookie</Paragraph>
                      <Paragraph>4. 粘贴到文本框中提交</Paragraph>
                    </div>
                  }
                />
              </Steps>
            </Card>
          </TabPane>
        </Tabs>
      </Content>

      {/* 登录弹窗 */}
      <Modal
        title={
          <Space>
            <span>{getPlatformInfo(selectedPlatform).icon}</span>
            <span>登录 {getPlatformInfo(selectedPlatform).name}</span>
          </Space>
        }
        open={loginModalOpen}
        onCancel={() => setLoginModalOpen(false)}
        footer={null}
        width={loginType === 'qr' ? 400 : 500}
      >
        {/* 登录方式切换 */}
        <div style={{ marginBottom: 24 }}>
          <Space wrap>
            <Button 
              type={loginType === 'qr' ? 'primary' : 'default'} 
              icon={<QrcodeOutlined />}
              onClick={() => setLoginType('qr')}
            >
              二维码
            </Button>
            <Button 
              type={loginType === 'password' ? 'primary' : 'default'} 
              icon={<KeyOutlined />}
              onClick={() => setLoginType('password')}
            >
              密码
            </Button>
            <Button 
              type={loginType === 'sms' ? 'primary' : 'default'} 
              icon={<MobileOutlined />}
              onClick={() => setLoginType('sms')}
            >
              短信
            </Button>
            <Button 
              type={loginType === 'cookie' ? 'primary' : 'default'} 
              icon={<GlobalOutlined />}
              onClick={() => setLoginType('cookie')}
            >
              Cookie
            </Button>
          </Space>
        </div>

        {/* 二维码登录 */}
        {loginType === 'qr' && (
          <div style={{ textAlign: 'center' }}>
            {qrStatus === 'pending' && (
              <>
                <QRCode value={`https://mybook.app/login?session=${qrSessionId}`} size={200} />
                <Paragraph type="secondary" style={{ marginTop: 16 }}>
                  请使用{gotPlatformInfo(selectedPlatform).name}App扫描二维码
                </Paragraph>
              </>
            )}
            {qrStatus === 'scanned' && (
              <>
                <QRCode value={`https://mybook.app/login?session=${qrSessionId}`} size={200} status="expired" />
                <Alert message="二维码已扫描，请在App中确认登录" type="warning" showIcon />
              </>
            )}
            {qrStatus === 'confirmed' && (
              <>
                <div style={{ fontSize: 64 }}>✅</div>
                <Paragraph>登录成功！</Paragraph>
              </>
            )}
            {qrStatus === 'expired' && (
              <>
                <QRCode value="" size={200} status="expired" />
                <Button type="primary" onClick={() => setQrStatus('pending')} style={{ marginTop: 16 }}>
                  重新生成二维码
                </Button>
              </>
            )}
          </div>
        )}

        {/* 密码登录 */}
        {loginType === 'password' && (
          <Form form={loginForm} layout="vertical" onFinish={handleLogin}>
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input placeholder="请输入用户名或邮箱" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password placeholder="请输入密码" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setLoginModalOpen(false)}>取消</Button>
                <Button type="primary" htmlType="submit" loading={loginLoading} icon={<LoginOutlined />}>
                  登录
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}

        {/* 短信登录 */}
        {loginType === 'sms' && (
          <Form form={loginForm} layout="vertical" onFinish={handleLogin}>
            <Form.Item name="phone" label="手机号" rules={[{ required: true, message: '请输入手机号' }]}>
              <Input placeholder="请输入手机号" />
            </Form.Item>
            <Form.Item name="code" label="验证码" rules={[{ required: true, message: '请输入验证码' }]}>
              <Space.Compact style={{ width: '100%' }}>
                <Input placeholder="请输入验证码" />
                <Button htmlType="button" onClick={() => handleLogin({ action: 'send', phone: loginForm.getFieldValue('phone') })}>
                  发送验证码
                </Button>
              </Space.Compact>
            </Form.Item>
            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setLoginModalOpen(false)}>取消</Button>
                <Button type="primary" htmlType="submit" loading={loginLoading} icon={<LoginOutlined />}>
                  登录
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}

        {/* Cookie登录 */}
        {loginType === 'cookie' && (
          <Form form={loginForm} layout="vertical" onFinish={handleLogin}>
            <Form.Item name="cookies" label="Cookie内容" rules={[{ required: true, message: '请输入Cookie' }]}>
              <TextArea rows={6} placeholder="请粘贴从浏览器导出的Cookie..." />
            </Form.Item>
            <Alert message="请确保Cookie未过期，否则登录可能失败" type="warning" showIcon />
            <Form.Item style={{ marginBottom: 0, marginTop: 16, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setLoginModalOpen(false)}>取消</Button>
                <Button type="primary" htmlType="submit" loading={loginLoading} icon={<LoginOutlined />}>
                  登录
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}
      </Modal>
    </Layout>
  )
}

// 修复：添加缺失的函数
const gotPlatformInfo = (platformId: string) => {
  const platform = platforms.find(p => p.id === platformId)
  return platform || { name: platformId, icon: '🌐', color: '#666' }
}

export default PlatformAccountsPage
