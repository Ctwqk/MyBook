/**
 * 平台账号管理页面
 * 用于管理各网文平台的登录账号
 */
import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock,
  ExternalLink,
  BookOpen
} from 'lucide-react';
import { PlatformLogin } from '../components/PlatformLogin';
import styles from './PlatformAccounts.module.css';

interface PlatformInfo {
  platform: string;
  name: string;
  description: string;
  features: string[];
  login_methods: string[];
}

interface Account {
  platform: string;
  platform_name: string;
  status: 'active' | 'expired' | 'unknown';
  last_login: string;
  book_count?: number;
  cookies?: Record<string, string>;
}

const API_BASE = '/api';

// 获取平台列表
async function fetchPlatforms(): Promise<PlatformInfo[]> {
  const res = await fetch(`${API_BASE}/platform/platforms`);
  const data = await res.json();
  return Object.entries(data.platforms || {}).map(([key, info]: [string, any]) => ({
    platform: key,
    name: info.name,
    description: info.description,
    features: info.features || [],
    login_methods: info.features?.length ? ['password', 'qr_code'] : ['password']
  }));
}

// 获取已保存的账号
async function fetchAccounts(): Promise<Account[]> {
  const saved = localStorage.getItem('platform_accounts');
  return saved ? JSON.parse(saved) : [];
}

// 保存账号
function saveAccounts(accounts: Account[]) {
  localStorage.setItem('platform_accounts', JSON.stringify(accounts));
}

export const PlatformAccounts: React.FC = () => {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [loginModal, setLoginModal] = useState<{
    show: boolean;
    platform: string;
    platformName: string;
  }>({ show: false, platform: '', platformName: '' });

  // 加载数据
  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [platformList, savedAccounts] = await Promise.all([
          fetchPlatforms(),
          fetchAccounts()
        ]);
        setPlatforms(platformList);
        setAccounts(savedAccounts);
      } catch (e) {
        console.error('Load failed:', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // 登录成功回调
  const handleLoginSuccess = async (platform: string, cookies: Record<string, string>) => {
    const platformInfo = platforms.find(p => p.platform === platform);
    
    const newAccount: Account = {
      platform,
      platform_name: platformInfo?.name || platform,
      status: 'active',
      last_login: new Date().toISOString(),
      cookies
    };

    // 移除旧账号，添加新账号
    const updated = accounts.filter(a => a.platform !== platform);
    updated.push(newAccount);
    
    setAccounts(updated);
    saveAccounts(updated);
    setLoginModal({ show: false, platform: '', platformName: '' });
  };

  // 删除账号
  const handleDelete = (platform: string) => {
    const updated = accounts.filter(a => a.platform !== platform);
    setAccounts(updated);
    saveAccounts(updated);
  };

  // 获取平台图标/颜色
  const getPlatformColor = (platform: string): string => {
    const colors: Record<string, string> = {
      qidian: '#c71585',    // 起点 - 紫红色
      jjwxc: '#ff6600',      // 晋江 - 橙色
      fanqie: '#07c160',     // 番茄 - 绿色
    };
    return colors[platform] || '#666';
  };

  // 获取平台链接
  const getPlatformUrl = (platform: string): string => {
    const urls: Record<string, string> = {
      qidian: 'https://creator.qidian.com',
      jjwxc: 'https://www.jjwxc.net/mine.php',
      fanqie: 'https://author.fanqienovel.com',
    };
    return urls[platform] || '#';
  };

  // 检查账号是否已登录
  const getAccount = (platform: string): Account | undefined => {
    return accounts.find(a => a.platform === platform);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <RefreshCw className={styles.spin} size={24} />
          <span>加载中...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>平台账号管理</h1>
        <p className={styles.subtitle}>管理您的网文发布平台账号</p>
      </div>

      <div className={styles.grid}>
        {platforms.filter(p => p.platform !== 'mock').map((platform) => {
          const account = getAccount(platform.platform);
          const isLoggedIn = account?.status === 'active';

          return (
            <div key={platform.platform} className={styles.card}>
              <div className={styles.cardHeader}>
                <div 
                  className={styles.platformBadge}
                  style={{ backgroundColor: getPlatformColor(platform.platform) }}
                >
                  {platform.name}
                </div>
                {isLoggedIn ? (
                  <span className={styles.loggedIn}>
                    <CheckCircle size={14} />
                    已登录
                  </span>
                ) : (
                  <span className={styles.notLogged}>
                    <XCircle size={14} />
                    未登录
                  </span>
                )}
              </div>

              <div className={styles.cardBody}>
                <p className={styles.description}>{platform.description}</p>
                
                {isLoggedIn && (
                  <div className={styles.accountInfo}>
                    <div className={styles.infoRow}>
                      <Clock size={14} />
                      <span>上次登录: {new Date(account.last_login).toLocaleString()}</span>
                    </div>
                    {account.book_count !== undefined && (
                      <div className={styles.infoRow}>
                        <BookOpen size={14} />
                        <span>书籍数: {account.book_count}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className={styles.cardFooter}>
                {isLoggedIn ? (
                  <>
                    <a 
                      href={getPlatformUrl(platform.platform)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.actionBtn + ' ' + styles.primary}
                    >
                      <ExternalLink size={14} />
                      作者后台
                    </a>
                    <button 
                      className={styles.actionBtn + ' ' + styles.danger}
                      onClick={() => handleDelete(platform.platform)}
                    >
                      <Trash2 size={14} />
                      删除
                    </button>
                  </>
                ) : (
                  <button 
                    className={styles.actionBtn + ' ' + styles.primary}
                    onClick={() => setLoginModal({
                      show: true,
                      platform: platform.platform,
                      platformName: platform.name
                    })}
                  >
                    <Plus size={14} />
                    登录
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 登录弹窗 */}
      {loginModal.show && (
        <PlatformLogin
          platform={loginModal.platform}
          platformName={loginModal.platformName}
          onClose={() => setLoginModal({ show: false, platform: '', platformName: '' })}
          onSuccess={(cookies) => handleLoginSuccess(loginModal.platform, cookies)}
        />
      )}
    </div>
  );
};

export default PlatformAccounts;
