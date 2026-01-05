"""
Token处理服务 - 使用PyJWT实现
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ValidationError
import os

from utils.logger import logger


class UserInfo(BaseModel):
    """用户信息模型"""
    user_id: str
    user_name: str
    branch_no: str  # 部门编号，对应entity.code
    branch_name: str  # 部门名称
    role_id_list: List[str]  # 角色ID列表，对应entity.code
    access_time: datetime


class TokenService:
    """Token处理服务 - 基于PyJWT"""
    
    def __init__(self, secret_key: Optional[str] = None, token_expire_hours: int = 24):
        """
        初始化Token服务
        
        Args:
            secret_key: JWT签名密钥，如果为None则从环境变量获取
            token_expire_hours: token过期时间（小时）
        """
        self.token_expire_hours = token_expire_hours
        self.algorithm = "HS256"
        
        # 获取密钥
        if secret_key is None:
            secret_key = os.getenv("TOKEN_SECRET_KEY", "default_secret_key_for_development")
        
        self.secret_key = secret_key
    
    def generate_token(self, user_info: UserInfo) -> str:
        """
        生成JWT token
        
        Args:
            user_info: 用户信息
            
        Returns:
            JWT token字符串
        """
        try:
            # 创建JWT payload
            now = datetime.now()
            payload = {
                # 标准claims
                "iat": now,  # issued at
                "exp": now + timedelta(hours=self.token_expire_hours),  # expiration time
                "iss": "taosha-platform",  # issuer
                
                # 自定义claims
                "user_id": user_info.user_id,
                "user_name": user_info.user_name,
                "branch_no": user_info.branch_no,
                "branch_name": user_info.branch_name,
                "role_id_list": user_info.role_id_list,
                "access_time": user_info.access_time.isoformat()
            }
            
            # 生成JWT token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.debug(f"生成JWT token成功，用户: {user_info.user_id}")
            return token
            
        except Exception as e:
            logger.error(f"生成JWT token失败: {e}")
            raise
    
    def decode_token(self, token: str) -> UserInfo:
        """
        解析JWT token
        
        Args:
            token: JWT token字符串
            
        Returns:
            用户信息对象
            
        Raises:
            ValueError: token格式错误、过期或验证失败
            ValidationError: 用户信息验证失败
        """
        try:
            # 解码JWT token（自动验证签名和过期时间）
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "user_id", "user_name", "branch_no", "role_id_list"]
                }
            )
            
            # 转换access_time
            access_time = datetime.fromisoformat(payload['access_time'])
            
            # 创建UserInfo对象
            user_info = UserInfo(
                user_id=payload['user_id'],
                user_name=payload['user_name'],
                branch_no=payload['branch_no'],
                branch_name=payload['branch_name'],
                role_id_list=payload['role_id_list'],
                access_time=access_time
            )
            
            logger.debug(f"解析JWT token成功，用户: {user_info.user_id}")
            return user_info
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token已过期")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT token无效: {e}")
            raise ValueError("Invalid token")
        except (KeyError, ValueError) as e:
            logger.warning(f"JWT token格式错误: {e}")
            raise ValueError("Invalid token format")
        except ValidationError as e:
            logger.warning(f"用户信息验证失败: {e}")
            raise ValueError("Invalid user info in token")
        except Exception as e:
            logger.error(f"解析JWT token失败: {e}")
            raise ValueError("Token decoding failed")
    
    def validate_token(self, user_info: UserInfo) -> bool:
        """
        验证token是否有效
        
        注意：使用PyJWT时，decode_token已经自动验证了过期时间
        这个方法主要用于额外的业务逻辑验证
        
        Args:
            user_info: 从token解析出的用户信息
            
        Returns:
            是否有效
        """
        try:
            # PyJWT已经在decode时验证了过期时间
            # 这里可以添加额外的业务逻辑验证
            
            # 检查必要字段
            if not user_info.user_id or not user_info.user_name:
                return False
            
            # 检查角色列表
            if not user_info.role_id_list:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证token失败: {e}")
            return False
    
    def is_token_expired(self, access_time: datetime) -> bool:
        """
        检查token是否过期
        
        注意：使用PyJWT时，通常不需要手动检查过期时间，
        因为decode_token会自动验证。这个方法保留用于兼容性。
        
        Args:
            access_time: token中的访问时间
            
        Returns:
            是否过期
        """
        try:
            expire_time = access_time + timedelta(hours=self.token_expire_hours)
            is_expired = datetime.now() > expire_time
            
            if is_expired:
                logger.debug(f"token已过期，访问时间: {access_time}, 过期时间: {expire_time}")
            
            return is_expired
            
        except Exception as e:
            logger.error(f"检查token过期状态失败: {e}")
            return True  # 出错时认为已过期
    
    def refresh_token(self, old_token: str) -> str:
        """
        刷新token（更新访问时间和过期时间）
        
        Args:
            old_token: 旧的token
            
        Returns:
            新的token
        """
        try:
            # 解析旧token（会验证签名，但忽略过期时间）
            payload = jwt.decode(
                old_token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # 忽略过期时间验证
            )
            
            # 创建用户信息
            user_info = UserInfo(
                user_id=payload['user_id'],
                user_name=payload['user_name'],
                branch_no=payload['branch_no'],
                branch_name=payload['branch_name'],
                role_id_list=payload['role_id_list'],
                access_time=datetime.now()  # 更新访问时间
            )
            
            # 生成新token
            return self.generate_token(user_info)
            
        except Exception as e:
            logger.error(f"刷新token失败: {e}")
            raise
    
    def get_token_payload(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """
        获取token的payload（不创建UserInfo对象）
        
        Args:
            token: JWT token
            verify: 是否验证token（包括过期时间）
            
        Returns:
            token的payload字典
        """
        try:
            options = {} if verify else {"verify_exp": False, "verify_signature": False}
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options=options
            )
            
            return payload
            
        except Exception as e:
            logger.error(f"获取token payload失败: {e}")
            raise


# 全局token服务实例
_token_service = None


def get_token_service() -> TokenService:
    """获取全局token服务实例"""
    global _token_service
    if _token_service is None:
        _token_service = TokenService()
    return _token_service