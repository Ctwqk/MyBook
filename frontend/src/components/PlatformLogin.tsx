/**
 * 平台登录弹窗组件
 * 支持：密码登录、二维码登录、短信验证码登录、Cookie导入
 */
import React, { useState, useEffect, useCallback } from 'react';
import { X, QrCode, Key, MessageSquare, Cookie, RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react';
import styles from './PlatformLogin.module.css';

// API 函数
const api = {
  async getPlatforms() {
    const res = await fetch('/api/platform/platforms');
    return res.json();
  },

  async startQRLogin(platform: string) {
    const res = await fetch(`/api/platform/login/qr?platform=${platform}`, { method: 'POST' });
    return res.json();
  },

  async checkQRStatus(sessionId: string) {
    const res = await fetch(`/api/platform/login/qr/${sessionId}`);
    return res.json();
  },

  async passwordLogin(platform: string, username: string, password: string) {
    const res = await fetch('/api/platform/login/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, username, password })
    });
    return res.json();
  },

  async sendSMS(platform: string, phone: string) {
    const res = await fetch('/api/platform/login/sms/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, phone })
    });
    return res.json();
  },

  async importCookies(platform: string, cookies: Record<string, string>) {
    const res = await fetch('/api/platform/login/cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, cookies })
    });
    return res.json();
  }
};

type LoginTab = 'password' | 'qrcode' | 'sms' | 'cookie';
type QRStatus = 'waiting' | 'scanning' | 'success' | 'failed' | 'timeout';

interface PlatformLoginProps {
  platform: string;
  platformName: string;
  onClose: () => void;
  onSuccess: (cookies: Record<string, string>) => void;
}

export const PlatformLogin: React.FC<PlatformLoginProps> = ({
  platform,
  platformName,
  onClose,
  onSuccess
}) => {
  const [activeTab, setActiveTab] = useState<LoginTab>('password');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 密码登录
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // 二维码登录
  const [qrSessionId, setQrSessionId] = useState<string | null>(null);
  const [qrStatus, setQrStatus] = useState<QRStatus>('waiting');
  const [qrUrl, setQrUrl] = useState<string | null>(null);

  // 短信登录
  const [phone, setPhone] = useState('');
  const [smsCode, setSmsCode] = useState('');
  // const [smsSessionId] = useState<string | null>(null);
  const [smsSent, setSmsSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Cookie导入
  const [cookieInput, setCookieInput] = useState('');

  // 启动二维码登录
  const startQRLogin = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startQRLogin(platform);
      if (result.qr_code_url || result.qr_code_data) {
        setQrSessionId(result.session_id);
        setQrUrl(result.qr_code_url || result.qr_code_data);
        setQrStatus('scanning');
      } else {
        setError(result.error_message || '获取二维码失败');
      }
    } catch (e) {
      setError('网络错误');
    } finally {
      setLoading(false);
    }
  }, [platform]);

  // 轮询二维码状态
  useEffect(() => {
    if (!qrSessionId || qrStatus !== 'scanning') return;

    const interval = setInterval(async () => {
      try {
        const result = await api.checkQRStatus(qrSessionId);
        setQrStatus(result.status);
        
        if (result.status === 'success' && result.cookies) {
          clearInterval(interval);
          onSuccess(result.cookies);
        } else if (result.status === 'failed' || result.status === 'timeout') {
          clearInterval(interval);
          setError(result.error_message || '登录超时');
        }
      } catch (e) {
        console.error('Check status failed:', e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [qrSessionId, qrStatus, onSuccess]);

  // 发送短信验证码
  const sendSMS = async () => {
    if (!phone || phone.length !== 11) {
      setError('请输入正确的手机号');
      return;
    }
    setLoading(true);
    try {
      const result = await api.sendSMS(platform, phone);
      if (result.success) {
        setSmsSent(true);
        // setSmsSessionId(result.session_id);
        setCountdown(60);
      } else {
        setError(result.error_message || '发送失败');
      }
    } catch (e) {
      setError('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 倒计时
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  // 密码登录
  const handlePasswordLogin = async () => {
    if (!username || !password) {
      setError('请填写用户名和密码');
      return;
    }
    setLoginLoading(true);
    setError(null);
    try {
      const result = await api.passwordLogin(platform, username, password);
      if (result.success) {
        onSuccess(result.cookies);
      } else {
        setError(result.error_message || '登录失败');
      }
    } catch (e) {
      setError('网络错误');
    } finally {
      setLoginLoading(false);
    }
  };

  // Cookie导入
  const handleCookieImport = async () => {
    try {
      // 尝试解析Cookie字符串
      const cookies: Record<string, string> = {};
      const lines = cookieInput.trim().split('\n');
      for (const line of lines) {
        const [name, ...valueParts] = line.split('=');
        if (name && valueParts.length > 0) {
          cookies[name.trim()] = valueParts.join('=').trim();
        }
      }
      
      if (Object.keys(cookies).length === 0) {
        setError('请输入有效的Cookie');
        return;
      }

      setLoading(true);
      const result = await api.importCookies(platform, cookies);
      if (result.success) {
        onSuccess(cookies);
      } else {
        setError(result.error_message || 'Cookie无效');
      }
    } catch (e) {
      setError('Cookie解析失败');
    } finally {
      setLoading(false);
    }
  };

  // 渲染状态图标
  const renderStatusIcon = () => {
    switch (qrStatus) {
      case 'success':
        return <CheckCircle className={styles.successIcon} size={48} />;
      case 'failed':
      case 'timeout':
        return <XCircle className={styles.errorIcon} size={48} />;
      case 'scanning':
        return <Clock className={styles.scanningIcon} size={48} />;
      default:
        return null;
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2>登录 {platformName}</h2>
          <button className={styles.closeBtn} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* 标签切换 */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'password' ? styles.active : ''}`}
            onClick={() => { setActiveTab('password'); setError(null); }}
          >
            <Key size={16} />
            密码登录
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'qrcode' ? styles.active : ''}`}
            onClick={() => { setActiveTab('qrcode'); setError(null); startQRLogin(); }}
          >
            <QrCode size={16} />
            二维码
          </button>
          {platform === 'fanqie' && (
            <button
              className={`${styles.tab} ${activeTab === 'sms' ? styles.active : ''}`}
              onClick={() => { setActiveTab('sms'); setError(null); }}
            >
              <MessageSquare size={16} />
              短信登录
            </button>
          )}
          <button
            className={`${styles.tab} ${activeTab === 'cookie' ? styles.active : ''}`}
            onClick={() => { setActiveTab('cookie'); setError(null); }}
          >
            <Cookie size={16} />
            Cookie
          </button>
        </div>

        {/* 密码登录 */}
        {activeTab === 'password' && (
          <div className={styles.content}>
            <div className={styles.formGroup}>
              <label>用户名 / 手机号 / 邮箱</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入"
              />
            </div>
            <div className={styles.formGroup}>
              <label>密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
              />
            </div>
            <button
              className={styles.submitBtn}
              onClick={handlePasswordLogin}
              disabled={loginLoading}
            >
              {loginLoading ? '登录中...' : '登录'}
            </button>
          </div>
        )}

        {/* 二维码登录 */}
        {activeTab === 'qrcode' && (
          <div className={styles.content}>
            <div className={styles.qrContainer}>
              {qrStatus === 'scanning' && qrUrl && (
                <div className={styles.qrWrapper}>
                  <img src={qrUrl} alt="登录二维码" className={styles.qrImage} />
                  <div className={styles.qrOverlay}>
                    <RefreshCw className={styles.scanIcon} size={32} />
                    <span>请使用{platformName}扫描二维码</span>
                  </div>
                </div>
              )}
              {renderStatusIcon()}
              {qrStatus === 'scanning' && (
                <p className={styles.hint}>请在2分钟内完成扫码</p>
              )}
            </div>
            <button className={styles.refreshBtn} onClick={startQRLogin}>
              <RefreshCw size={16} />
              刷新二维码
            </button>
          </div>
        )}

        {/* 短信登录 */}
        {activeTab === 'sms' && (
          <div className={styles.content}>
            <div className={styles.formGroup}>
              <label>手机号</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="请输入手机号"
                maxLength={11}
              />
            </div>
            {smsSent && (
              <div className={styles.formGroup}>
                <label>验证码</label>
                <div className={styles.smsInput}>
                  <input
                    type="text"
                    value={smsCode}
                    onChange={(e) => setSmsCode(e.target.value)}
                    placeholder="请输入验证码"
                    maxLength={6}
                  />
                  <span className={styles.countdown}>
                    {countdown > 0 ? `${countdown}s` : ''}
                  </span>
                </div>
              </div>
            )}
            <button
              className={styles.submitBtn}
              onClick={smsSent ? () => {} : sendSMS}
              disabled={loading || (smsSent && !smsCode)}
            >
              {smsSent ? '验证登录' : (countdown > 0 ? `重新发送(${countdown}s)` : '获取验证码')}
            </button>
          </div>
        )}

        {/* Cookie导入 */}
        {activeTab === 'cookie' && (
          <div className={styles.content}>
            <div className={styles.cookieGuide}>
              <h4>如何获取Cookie?</h4>
              <ol>
                <li>登录 {platformName} 官网</li>
                <li>按 F12 打开开发者工具</li>
                <li>切换到 Network (网络) 标签</li>
                <li>刷新页面，点击任意请求</li>
                <li>在 Request Headers 中找到 Cookie</li>
                <li>复制完整 Cookie 值粘贴到下方</li>
              </ol>
            </div>
            <div className={styles.formGroup}>
              <label>Cookie</label>
              <textarea
                value={cookieInput}
                onChange={(e) => setCookieInput(e.target.value)}
                placeholder="name1=value1; name2=value2; ..."
                rows={5}
              />
            </div>
            <button
              className={styles.submitBtn}
              onClick={handleCookieImport}
              disabled={loading || !cookieInput}
            >
              {loading ? '验证中...' : '导入并登录'}
            </button>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className={styles.error}>
            <XCircle size={16} />
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlatformLogin;
