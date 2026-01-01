#!/usr/bin/env python3
"""
Token生成脚本工具
用于开发和测试环境生成测试用的token
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.token_service import TokenService, UserInfo
from utils.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成测试用的加密token')
    
    # 添加命令行参数
    parser.add_argument('--user-id', required=True, help='用户ID')
    parser.add_argument('--user-name', required=True, help='用户姓名')
    parser.add_argument('--branch-no', required=True, help='部门编号')
    parser.add_argument('--branch-name', required=True, help='部门名称')
    parser.add_argument('--role-id-list', required=True, help='角色ID列表，用逗号分隔')
    parser.add_argument('--secret-key', help='JWT签名密钥（可选，默认使用环境变量或默认值）')
    parser.add_argument('--expire-hours', type=int, default=24, help='token过期时间（小时），默认24小时')
    
    args = parser.parse_args()
    
    try:
        # 解析角色ID列表
        role_id_list = [role_id.strip() for role_id in args.role_id_list.split(',') if role_id.strip()]
        
        # 创建用户信息
        user_info = UserInfo(
            user_id=args.user_id,
            user_name=args.user_name,
            branch_no=args.branch_no,
            branch_name=args.branch_name,
            role_id_list=role_id_list,
            access_time=datetime.utcnow()
        )
        
        # 创建token服务
        token_service = TokenService(
            secret_key=args.secret_key,
            token_expire_hours=args.expire_hours
        )
        
        # 生成token
        token = token_service.generate_token(user_info)
        
        # 输出结果
        print("=" * 60)
        print("Token生成成功！")
        print("=" * 60)
        print(f"用户ID: {user_info.user_id}")
        print(f"用户姓名: {user_info.user_name}")
        print(f"部门编号: {user_info.branch_no}")
        print(f"部门名称: {user_info.branch_name}")
        print(f"角色ID列表: {', '.join(user_info.role_id_list)}")
        print(f"访问时间: {user_info.access_time}")
        print(f"过期时间: {args.expire_hours}小时")
        print("=" * 60)
        print("生成的Token:")
        print(token)
        print("=" * 60)
        
        # 验证token（测试解析）
        print("验证Token...")
        try:
            decoded_info = token_service.decode_token(token)
            is_valid = token_service.validate_token(decoded_info)
            
            print(f"Token验证结果: {'有效' if is_valid else '无效'}")
            print(f"解析出的用户信息: {decoded_info}")
            
            # 显示JWT payload信息
            payload = token_service.get_token_payload(token)
            print(f"JWT过期时间: {datetime.fromtimestamp(payload['exp'])}")
            print(f"JWT签发时间: {datetime.fromtimestamp(payload['iat'])}")
            print(f"JWT签发者: {payload.get('iss', 'N/A')}")
            
        except Exception as e:
            print(f"Token验证失败: {e}")
            logger.error(f"Token验证失败: {e}")
            sys.exit(1)
        
        logger.info(f"为用户 {args.user_id} 生成token成功")
        
    except Exception as e:
        print(f"生成token失败: {e}")
        logger.error(f"生成token失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()