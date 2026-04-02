import { Link } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import { SettingOutlined } from '@ant-design/icons'

const { Header: AntHeader } = Layout

const Header = () => {
  const menuItems = [
    { key: 'projects', label: <Link to="/projects">项目</Link> },
    { 
      key: 'settings', 
      label: <Link to="/settings/prompts"><SettingOutlined /> Prompt 设置</Link> 
    },
  ]

  return (
    <AntHeader style={{ display: 'flex', alignItems: 'center', position: 'fixed', top: 0, width: '100%', zIndex: 1000 }}>
      <div style={{ color: 'white', fontSize: 20, fontWeight: 'bold', marginRight: 40 }}>
        MyBook
      </div>
      <Menu
        theme="dark"
        mode="horizontal"
        items={menuItems}
        style={{ flex: 1 }}
      />
    </AntHeader>
  )
}

export default Header
