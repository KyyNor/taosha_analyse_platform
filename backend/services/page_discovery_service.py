"""
页面发现服务
从配置文件加载页面信息并同步到数据库
"""

import yaml
from typing import List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session

from models.permission_models import SystemPage
from repositories.permission_repository import PermissionRepository
from utils.logger import logger
import uuid


class PageInfo:
    """页面信息数据类"""
    
    def __init__(self, path: str, name: str, description: str = ""):
        self.path = path
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"PageInfo(path='{self.path}', name='{self.name}')"


class PageDiscoveryService:
    """页面发现服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
        self.config_path = Path(__file__).parent.parent / "config" / "pages.yaml"
    
    def load_pages_from_config(self) -> List[PageInfo]:
        """
        从配置文件加载页面信息
        
        Returns:
            List[PageInfo]: 页面信息列表
        """
        try:
            if not self.config_path.exists():
                logger.warning(f"页面配置文件不存在: {self.config_path}")
                return []
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'pages' not in config:
                logger.warning("页面配置文件格式错误：缺少pages节点")
                return []
            
            pages = []
            for page_data in config['pages']:
                if not isinstance(page_data, dict):
                    logger.warning(f"跳过无效的页面配置: {page_data}")
                    continue
                
                path = page_data.get('path')
                name = page_data.get('name')
                description = page_data.get('description', '')
                
                if not path or not name:
                    logger.warning(f"跳过不完整的页面配置: {page_data}")
                    continue
                
                pages.append(PageInfo(path=path, name=name, description=description))
            
            logger.info(f"从配置文件加载了 {len(pages)} 个页面")
            return pages
            
        except yaml.YAMLError as e:
            logger.error(f"解析页面配置文件失败: {e}")
            return []
        except Exception as e:
            logger.error(f"加载页面配置失败: {e}")
            return []
    
    def sync_pages_from_config(self) -> int:
        """
        从配置文件同步页面到数据库
        
        Returns:
            int: 同步的页面数量
        """
        try:
            pages_config = self.load_pages_from_config()
            if not pages_config:
                logger.warning("没有页面配置需要同步")
                return 0
            
            synced_count = 0
            updated_count = 0
            
            for page_info in pages_config:
                # 检查页面是否已存在
                existing_page = self.repo.get_page_by_path(page_info.path)
                
                if existing_page:
                    # 更新现有页面信息
                    if (existing_page.name != page_info.name or 
                        existing_page.description != page_info.description):
                        
                        existing_page.name = page_info.name
                        existing_page.description = page_info.description
                        self.repo.update_page(existing_page)
                        updated_count += 1
                        logger.debug(f"更新页面: {page_info.path}")
                else:
                    # 创建新页面
                    new_page = SystemPage(
                        id=str(uuid.uuid4()),
                        path=page_info.path,
                        name=page_info.name,
                        description=page_info.description
                    )
                    self.repo.create_page(new_page)
                    synced_count += 1
                    logger.debug(f"创建页面: {page_info.path}")
            
            logger.info(f"页面同步完成: 新增 {synced_count} 个，更新 {updated_count} 个")
            return synced_count + updated_count
            
        except Exception as e:
            logger.error(f"同步页面配置失败: {e}")
            raise
    
    def sync_pages_on_startup(self) -> None:
        """
        系统启动时同步页面信息
        
        这个方法应该在应用启动时调用
        """
        try:
            logger.info("开始系统启动时的页面同步...")
            count = self.sync_pages_from_config()
            logger.info(f"系统启动页面同步完成，处理了 {count} 个页面")
            
        except Exception as e:
            logger.error(f"系统启动页面同步失败: {e}")
            # 不抛出异常，避免影响系统启动
    
    def get_all_pages_from_config(self) -> List[Dict[str, Any]]:
        """
        获取配置文件中的所有页面信息（用于API返回）
        
        Returns:
            List[Dict]: 页面信息字典列表
        """
        try:
            pages_config = self.load_pages_from_config()
            return [
                {
                    "path": page.path,
                    "name": page.name,
                    "description": page.description
                }
                for page in pages_config
            ]
            
        except Exception as e:
            logger.error(f"获取配置页面信息失败: {e}")
            return []
    
    def validate_page_path(self, page_path: str) -> bool:
        """
        验证页面路径是否在配置中定义
        
        Args:
            page_path: 页面路径
            
        Returns:
            bool: 是否为有效的页面路径
        """
        try:
            pages_config = self.load_pages_from_config()
            valid_paths = {page.path for page in pages_config}
            return page_path in valid_paths
            
        except Exception as e:
            logger.error(f"验证页面路径失败: {e}")
            return False
    
    def get_page_info_by_path(self, page_path: str) -> PageInfo:
        """
        根据路径获取页面信息
        
        Args:
            page_path: 页面路径
            
        Returns:
            PageInfo: 页面信息，如果不存在返回None
        """
        try:
            pages_config = self.load_pages_from_config()
            for page in pages_config:
                if page.path == page_path:
                    return page
            return None
            
        except Exception as e:
            logger.error(f"获取页面信息失败: {e}")
            return None
    
    def reload_config(self) -> bool:
        """
        重新加载配置文件并同步到数据库
        
        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info("重新加载页面配置...")
            count = self.sync_pages_from_config()
            logger.info(f"配置重新加载完成，处理了 {count} 个页面")
            return True
            
        except Exception as e:
            logger.error(f"重新加载页面配置失败: {e}")
            return False