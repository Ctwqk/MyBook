"""
平台登录 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.publish.login_service import (
    BrowserLoginService,
    get_login_service,
    LoginMethod,
    LoginSession
)
from app.services.publish.adapters import list_platforms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["platform"])


class PasswordLoginRequest(BaseModel):
    """密码登录请求"""
    platform: str
    username: str
    password: str


class SMSCodeRequest(BaseModel):
    """短信验证码请求"""
    platform: str
    phone: str


class SMSVerifyRequest(BaseModel):
    """短信验证请求"""
    session_id: str
    code: str


class CookieImportRequest(BaseModel):
    """Cookie导入请求"""
    platform: str
    cookies: dict


class QRCodeResponse(BaseModel):
    """二维码登录响应"""
    session_id: str
    platform: str
    method: str
    status: str
    qr_code_url: Optional[str] = None
    qr_code_data: Optional[str] = None
    error_message: Optional[str] = None


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    session_id: str
    platform: str
    status: str
    cookies: Optional[dict] = None
    error_message: Optional[str] = None


class PlatformInfoResponse(BaseModel):
    """平台信息响应"""
    platform: str
    name: str
    description: str
    features: list[str]
    login_methods: list[str]


@router.get("/platforms", response_model=dict)
async def get_available_platforms():
    """获取可用平台列表"""
    platforms = list_platforms()
    return {
        "platforms": platforms,
        "total": len(platforms)
    }


@router.get("/platforms/{platform}", response_model=PlatformInfoResponse)
async def get_platform_info(platform: str):
    """获取平台详情"""
    platforms = list_platforms()
    if platform not in platforms:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    info = platforms[platform]
    
    # 确定支持的登录方式
    login_methods = ["password"]
    if platform == "fanqie":
        login_methods.append("sms_code")
    if platform in ["qidian", "fanqie"]:
        login_methods.append("qr_code")
    
    return PlatformInfoResponse(
        platform=platform,
        name=info.get("name", platform),
        description=info.get("description", ""),
        features=info.get("features", []),
        login_methods=login_methods
    )


@router.post("/login/qr", response_model=QRCodeResponse)
async def start_qr_login(platform: str, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    开始二维码登录流程
    
    返回二维码URL和session_id，前端需要定期轮询检查状态
    """
    try:
        session = await login_service.start_qr_login(platform)
        
        return QRCodeResponse(
            session_id=session.session_id,
            platform=session.platform,
            method=session.method.value,
            status=session.status,
            qr_code_url=session.qr_code_url,
            qr_code_data=session.qr_code_data,
            error_message=session.error_message
        )
    except Exception as e:
        logger.error(f"QR login failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/login/qr/{session_id}", response_model=LoginStatusResponse)
async def check_qr_login_status(session_id: str, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    检查二维码登录状态
    
    前端应每2-3秒轮询一次
    """
    try:
        session = await login_service.check_session_status(session_id)
        
        return LoginStatusResponse(
            session_id=session.session_id,
            platform=session.platform,
            status=session.status,
            cookies=session.cookies,
            error_message=session.error_message
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Check login status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/password")
async def password_login(request: PasswordLoginRequest, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    密码登录
    
    使用浏览器自动化完成密码登录
    """
    try:
        result = await login_service.login_with_password(
            platform=request.platform,
            username=request.username,
            password=request.password
        )
        
        return result
    except Exception as e:
        logger.error(f"Password login failed: {e}")
        return {
            "success": False,
            "error_code": "LOGIN_ERROR",
            "error_message": str(e)
        }


@router.post("/login/sms/send")
async def send_sms_code(request: SMSCodeRequest, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    发送短信验证码
    """
    try:
        result = await login_service.request_sms_code(
            platform=request.platform,
            phone=request.phone
        )
        
        return result
    except Exception as e:
        logger.error(f"Send SMS failed: {e}")
        return {
            "success": False,
            "error_message": str(e)
        }


@router.post("/login/sms/verify")
async def verify_sms_code(request: SMSVerifyRequest, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    验证短信验证码
    """
    try:
        result = await login_service.verify_sms_code(
            session_id=request.session_id,
            code=request.code
        )
        
        return result
    except Exception as e:
        logger.error(f"Verify SMS failed: {e}")
        return {
            "success": False,
            "error_message": str(e)
        }


@router.post("/login/cookie")
async def import_cookies(request: CookieImportRequest, login_service: BrowserLoginService = Depends(get_login_service)):
    """
    导入Cookie登录
    
    用户从浏览器开发者工具复制Cookie
    """
    try:
        result = await login_service.import_cookies(
            platform=request.platform,
            cookies=request.cookies
        )
        
        return result
    except Exception as e:
        logger.error(f"Cookie import failed: {e}")
        return {
            "success": False,
            "error_message": str(e)
        }


@router.post("/logout")
async def logout(platform: str, login_service: BrowserLoginService = Depends(get_login_service)):
    """退出登录"""
    await login_service.close()
    return {"success": True, "message": "已退出登录"}
