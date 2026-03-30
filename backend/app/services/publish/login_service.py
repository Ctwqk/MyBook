"""
浏览器自动化登录服务
处理各平台的二维码登录、验证码登录等复杂登录流程
"""
import asyncio
import base64
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LoginMethod(Enum):
    """登录方式"""
    PASSWORD = "password"          # 密码登录
    SMS_CODE = "sms_code"          # 短信验证码
    QR_CODE = "qr_code"           # 二维码扫码
    COOKIE = "cookie"             # Cookie导入


@dataclass
class LoginSession:
    """登录会话"""
    session_id: str
    platform: str
    method: LoginMethod
    status: str  # waiting, scanning, confirmed, success, failed
    qr_code_data: Optional[str] = None  # Base64二维码
    qr_code_url: Optional[str] = None    # 二维码URL
    cookies: Optional[dict] = None
    token: Optional[str] = None
    error_message: Optional[str] = None


class BrowserLoginService:
    """
    浏览器自动化登录服务
    
    使用 Playwright 实现各平台的自动化登录
    支持：
    - 密码登录
    - 短信验证码登录
    - 二维码扫码登录
    - Cookie导入
    """
    
    def __init__(self):
        self._sessions: dict[str, LoginSession] = {}
        self._playwright = None
        self._browser = None
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
            except ImportError:
                logger.warning("Playwright not installed, using fallback")
                self._browser = None
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
    
    async def start_qr_login(self, platform: str) -> LoginSession:
        """
        开始二维码登录流程
        
        Args:
            platform: 平台名称
            
        Returns:
            LoginSession: 登录会话
        """
        session_id = f"{platform}_{int(time.time())}"
        session = LoginSession(
            session_id=session_id,
            platform=platform,
            method=LoginMethod.QR_CODE,
            status="waiting"
        )
        self._sessions[session_id] = session
        
        await self._ensure_browser()
        
        if self._browser is None:
            # 降级处理：返回错误
            session.status = "failed"
            session.error_message = "Playwright not available"
            return session
        
        try:
            if platform == "qidian":
                await self._start_qidian_qr_login(session)
            elif platform == "jjwxc":
                await self._start_jjwxc_qr_login(session)
            elif platform == "fanqie":
                await self._start_fanqie_qr_login(session)
            else:
                session.status = "failed"
                session.error_message = f"Unknown platform: {platform}"
        except Exception as e:
            logger.error(f"QR login failed: {e}")
            session.status = "failed"
            session.error_message = str(e)
        
        return session
    
    async def _start_qidian_qr_login(self, session: LoginSession):
        """起点二维码登录"""
        page = await self._browser.new_page()
        
        try:
            # 访问登录页面
            await page.goto("https://passport.qidian.com/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 点击二维码登录标签
            qr_tab = page.locator(".qrcode-tab, [data-type='qrcode'], .scan-login")
            if await qr_tab.is_visible():
                await qr_tab.click()
            
            # 等待二维码加载
            await page.wait_for_timeout(2000)
            
            # 获取二维码图片
            qr_img = page.locator(".qrcode-img img, .qrcode img, [class*='qrcode'] img")
            if await qr_img.is_visible():
                qr_src = await qr_img.get_attribute("src")
                if qr_src:
                    session.qr_code_url = qr_src
                    # 如果是data URL，直接使用
                    if qr_src.startswith("data:"):
                        session.qr_code_data = qr_src
                    else:
                        session.qr_code_url = f"https://passport.qidian.com{qr_src}"
            
            # 如果没找到img，尝试获取整个二维码容器
            if not session.qr_code_url:
                qr_container = page.locator(".qrcode, .scan-code")
                if await qr_container.is_visible():
                    # 获取页面URL作为二维码链接
                    session.qr_code_url = "https://passport.qidian.com/qrcode"
            
            session.status = "scanning"
            
            # 监听登录成功
            async def check_login():
                for _ in range(120):  # 最多等2分钟
                    await page.wait_for_timeout(1000)
                    # 检查是否跳转到首页或用户中心
                    if "qidian.com" in page.url and "passport" not in page.url:
                        cookies = await page.context.cookies()
                        session.cookies = {c["name"]: c["value"] for c in cookies}
                        session.status = "success"
                        return True
                    # 检查是否有错误提示
                    error_elem = page.locator(".error-tip, .fail-tip")
                    if await error_elem.is_visible():
                        session.error_message = await error_elem.text_content()
                        session.status = "failed"
                        return True
                session.status = "timeout"
                return False
            
            await check_login()
            
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
        finally:
            await page.close()
    
    async def _start_jjwxc_qr_login(self, session: LoginSession):
        """晋江二维码登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://www.jjwxc.net/login.php", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 晋江可能没有二维码登录，这里尝试密码登录
            session.status = "waiting"
            session.error_message = "晋江文学城不支持二维码登录，请使用密码登录"
            
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
        finally:
            await page.close()
    
    async def _start_fanqie_qr_login(self, session: LoginSession):
        """番茄小说二维码登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://i.fanqiecdn.com/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 番茄小说可能有扫码登录
            qr_tab = page.locator("[class*='scan'], [class*='qr']")
            if await qr_tab.is_visible():
                await qr_tab.click()
            
            await page.wait_for_timeout(2000)
            
            # 获取二维码
            qr_img = page.locator("[class*='qrcode'] img, [class*='scan'] img")
            if await qr_img.is_visible():
                qr_src = await qr_img.get_attribute("src")
                if qr_src:
                    session.qr_code_url = qr_src
            
            session.status = "scanning"
            
            # 等待登录成功
            for _ in range(120):
                await page.wait_for_timeout(1000)
                if "fanqie" in page.url and "login" not in page.url:
                    cookies = await page.context.cookies()
                    session.cookies = {c["name"]: c["value"] for c in cookies}
                    session.status = "success"
                    break
            
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
        finally:
            await page.close()
    
    async def check_session_status(self, session_id: str) -> LoginSession:
        """
        检查登录会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            LoginSession: 更新后的会话
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        
        # 如果是扫描中状态，尝试刷新状态
        if session.status == "scanning" and session.platform == "qidian":
            await self._check_qidian_login(session)
        
        return session
    
    async def _check_qidian_login(self, session: LoginSession):
        """检查起点登录状态"""
        if self._browser is None:
            return
        
        try:
            page = await self._browser.new_page()
            # 设置已有的cookies
            if session.cookies:
                for name, value in session.cookies.items():
                    await page.context.add_cookies([{
                        "name": name,
                        "value": value,
                        "domain": ".qidian.com",
                        "path": "/"
                    }])
            
            await page.goto("https://www.qidian.com", timeout=10000)
            await page.wait_for_load_state("networkidle")
            
            # 检查是否已登录
            if "qidian.com" in page.url and "passport" not in page.url:
                # 已登录，获取完整cookies
                cookies = await page.context.cookies()
                session.cookies = {c["name"]: c["value"] for c in cookies}
                session.status = "success"
            
            await page.close()
        except Exception as e:
            logger.warning(f"Check login status failed: {e}")
    
    async def login_with_password(self, platform: str, username: str, password: str) -> dict[str, Any]:
        """
        密码登录
        
        Args:
            platform: 平台
            username: 用户名
            password: 密码
            
        Returns:
            dict: 登录结果
        """
        await self._ensure_browser()
        
        if self._browser is None:
            return {
                "success": False,
                "error_code": "BROWSER_NOT_AVAILABLE",
                "error_message": "浏览器自动化不可用"
            }
        
        if platform == "qidian":
            return await self._qidian_password_login(username, password)
        elif platform == "jjwxc":
            return await self._jjwxc_password_login(username, password)
        elif platform == "fanqie":
            return await self._fanqie_password_login(username, password)
        else:
            return {
                "success": False,
                "error_code": "UNKNOWN_PLATFORM",
                "error_message": f"未知平台: {platform}"
            }
    
    async def _qidian_password_login(self, username: str, password: str) -> dict[str, Any]:
        """起点密码登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://passport.qidian.com/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 填写用户名密码
            await page.fill("input[name='userName'], #userName", username)
            await page.fill("input[name='password'], #password", password)
            
            # 点击登录
            await page.click("button[type='submit'], .login-btn")
            
            # 等待响应
            await page.wait_for_timeout(3000)
            
            # 检查登录结果
            if "qidian.com" in page.url and "passport" not in page.url:
                cookies = await page.context.cookies()
                return {
                    "success": True,
                    "cookies": {c["name"]: c["value"] for c in cookies},
                    "message": "登录成功"
                }
            else:
                # 检查错误信息
                error_elem = page.locator(".error-tip, .tip-error")
                error_msg = await error_elem.text_content() if await error_elem.is_visible() else "登录失败"
                return {
                    "success": False,
                    "error_code": "LOGIN_FAILED",
                    "error_message": error_msg
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_code": "LOGIN_ERROR",
                "error_message": str(e)
            }
        finally:
            await page.close()
    
    async def _jjwxc_password_login(self, username: str, password: str) -> dict[str, Any]:
        """晋江密码登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://www.jjwxc.net/login.php", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 判断登录类型
            if "@" in username:
                await page.fill("input[name='loginemail']", username)
            else:
                await page.fill("input[name='loginname']", username)
            
            await page.fill("input[name='loginpwd']", password)
            
            # 勾选记住
            remember = page.locator("input[name='remember']")
            if await remember.is_visible():
                await remember.check()
            
            await page.click("button[type='submit'], input[type='submit']")
            
            await page.wait_for_timeout(3000)
            
            if "jjwxc.net" in page.url and "login" not in page.url:
                cookies = await page.context.cookies()
                return {
                    "success": True,
                    "cookies": {c["name"]: c["value"] for c in cookies},
                    "message": "登录成功"
                }
            else:
                return {
                    "success": False,
                    "error_code": "LOGIN_FAILED",
                    "error_message": "登录失败，请检查用户名和密码"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_code": "LOGIN_ERROR",
                "error_message": str(e)
            }
        finally:
            await page.close()
    
    async def _fanqie_password_login(self, username: str, password: str) -> dict[str, Any]:
        """番茄密码登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://i.fanqiecdn.com/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 选择密码登录
            password_tab = page.locator("[data-type='password'], .password-tab")
            if await password_tab.is_visible():
                await password_tab.click()
            
            await page.wait_for_timeout(500)
            
            # 填写手机号和密码
            await page.fill("input[type='tel'], input[placeholder*='手机']", username)
            await page.fill("input[type='password']", password)
            
            await page.click("button[type='submit']")
            
            await page.wait_for_timeout(3000)
            
            if "fanqie" in page.url and "login" not in page.url:
                cookies = await page.context.cookies()
                return {
                    "success": True,
                    "cookies": {c["name"]: c["value"] for c in cookies},
                    "message": "登录成功"
                }
            else:
                return {
                    "success": False,
                    "error_code": "LOGIN_FAILED",
                    "error_message": "登录失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_code": "LOGIN_ERROR",
                "error_message": str(e)
            }
        finally:
            await page.close()
    
    async def request_sms_code(self, platform: str, phone: str) -> dict[str, Any]:
        """
        请求短信验证码
        
        Args:
            platform: 平台
            phone: 手机号
            
        Returns:
            dict: 请求结果
        """
        await self._ensure_browser()
        
        if self._browser is None:
            return {
                "success": False,
                "error_message": "浏览器不可用"
            }
        
        if platform == "fanqie":
            return await self._fanqie_sms_login(phone)
        else:
            return {
                "success": False,
                "error_message": f"{platform} 不支持短信登录"
            }
    
    async def _fanqie_sms_login(self, phone: str) -> dict[str, Any]:
        """番茄短信登录"""
        page = await self._browser.new_page()
        
        try:
            await page.goto("https://i.fanqiecdn.com/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 选择短信登录
            sms_tab = page.locator("[data-type='sms'], .sms-tab")
            if await sms_tab.is_visible():
                await sms_tab.click()
            
            await page.wait_for_timeout(500)
            
            # 填写手机号
            await page.fill("input[type='tel'], input[placeholder*='手机']", phone)
            
            # 点击获取验证码
            send_btn = page.locator(".send-code, button:has-text('获取验证码')")
            if await send_btn.is_visible():
                await send_btn.click()
            
            await page.wait_for_timeout(1000)
            
            return {
                "success": True,
                "message": "验证码已发送",
                "session_id": f"fanqie_sms_{int(time.time())}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e)
            }
        finally:
            await page.close()
    
    async def verify_sms_code(self, session_id: str, code: str) -> dict[str, Any]:
        """
        验证短信验证码
        
        Args:
            session_id: 会话ID
            code: 验证码
            
        Returns:
            dict: 验证结果
        """
        # 这里需要保存page引用来填写验证码
        # 简化处理，返回需要前端操作
        return {
            "success": False,
            "error_message": "请在弹出的浏览器窗口中输入验证码"
        }
    
    async def import_cookies(self, platform: str, cookies: dict) -> dict[str, Any]:
        """
        导入Cookie登录
        
        Args:
            platform: 平台
            cookies: Cookie字典
            
        Returns:
            dict: 验证结果
        """
        await self._ensure_browser()
        
        if self._browser is None:
            return {
                "success": False,
                "error_message": "浏览器不可用"
            }
        
        page = await self._browser.new_page()
        
        try:
            # 设置cookies
            domain = {
                "qidian": ".qidian.com",
                "jjwxc": ".jjwxc.net",
                "fanqie": ".fanqiecdn.com"
            }.get(platform, "")
            
            if not domain:
                return {"success": False, "error_message": "未知平台"}
            
            cookie_list = [
                {"name": name, "value": value, "domain": domain, "path": "/"}
                for name, value in cookies.items()
            ]
            await page.context.add_cookies(cookie_list)
            
            # 访问平台首页验证
            urls = {
                "qidian": "https://www.qidian.com",
                "jjwxc": "https://www.jjwxc.net",
                "fanqie": "https://fanqienovel.com"
            }
            
            await page.goto(urls.get(platform, ""), timeout=10000)
            await page.wait_for_load_state("networkidle")
            
            # 检查是否登录成功
            if "login" not in page.url.lower():
                return {
                    "success": True,
                    "cookies": cookies,
                    "message": "Cookie有效，登录成功"
                }
            else:
                return {
                    "success": False,
                    "error_message": "Cookie已过期，请重新获取"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e)
            }
        finally:
            await page.close()


# 全局实例
_login_service: Optional[BrowserLoginService] = None


def get_login_service() -> BrowserLoginService:
    """获取登录服务实例"""
    global _login_service
    if _login_service is None:
        _login_service = BrowserLoginService()
    return _login_service


__all__ = [
    "BrowserLoginService",
    "LoginSession",
    "LoginMethod",
    "get_login_service",
]
