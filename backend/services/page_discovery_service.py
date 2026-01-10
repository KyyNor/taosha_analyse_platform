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
    """页面信息数据类 - 支持层级结构"""

    def __init__(
        self,
        path: str,
        name: str,
        description: str = "",
        level: int = 0,
        sort_order: int = 0,
        children: List['PageInfo'] = None
    ):
        self.path = path
        self.name = name
        self.description = description
        self.level = level
        self.sort_order = sort_order
        self.children = children or []

    def __repr__(self):
        return f"PageInfo(path='{self.path}', name='{self.name}', level={self.level})"


class PageDiscoveryService:
    """页面发现服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
        self.config_path = Path(__file__).parent.parent / "config" / "pages.yaml"
    
    def load_pages_from_config(self) -> List[PageInfo]:
        """
        从配置文件加载页面信息（支持层级结构）

        Returns:
            List[PageInfo]: 页面信息列表（扁平化）
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

            # 递归解析页面配置
            def parse_page(page_data: Dict[str, Any], parent_id: str = None) -> PageInfo:
                """递归解析页面配置（支持children嵌套）"""
                if not isinstance(page_data, dict):
                    logger.warning(f"跳过无效的页面配置: {page_data}")
                    return None

                path = page_data.get('path')
                name = page_data.get('name')
                description = page_data.get('description', '')
                level = page_data.get('level', 0)
                sort_order = page_data.get('sort_order', 0)
                children_data = page_data.get('children', [])

                if not path or not name:
                    logger.warning(f"跳过不完整的页面配置: {page_data}")
                    return None

                # 递归解析子页面
                children = []
                for child_data in children_data:
                    child_page = parse_page(child_data, path)
                    if child_page:
                        children.append(child_page)

                return PageInfo(
                    path=path,
                    name=name,
                    description=description,
                    level=level,
                    sort_order=sort_order,
                    children=children
                )

            # 解析所有一级页面
            pages = []
            for page_data in config['pages']:
                page = parse_page(page_data)
                if page:
                    pages.append(page)

            logger.info(f"从配置文件加载了 {len(pages)} 个一级页面")
            return pages

        except yaml.YAMLError as e:
            logger.error(f"解析页面配置文件失败: {e}")
            return []
        except Exception as e:
            logger.error(f"加载页面配置失败: {e}")
            return []
    
    def sync_pages_from_config(self) -> int:
        """
        从配置文件同步页面到数据库（支持层级结构）

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

            # 递归同步页面及其子页面
            def sync_page_recursive(page_info: PageInfo, parent_id: str = None) -> None:
                """递归同步页面及其子页面"""
                nonlocal synced_count, updated_count

                # 检查页面是否已存在
                existing_page = self.repo.get_page_by_path(page_info.path)

                if existing_page:
                    # 更新现有页面信息（包括层级字段）
                    if (existing_page.name != page_info.name or
                        existing_page.description != page_info.description or
                        existing_page.level != page_info.level or
                        existing_page.parent_id != parent_id):

                        existing_page.name = page_info.name
                        existing_page.description = page_info.description
                        existing_page.level = page_info.level
                        existing_page.parent_id = parent_id
                        existing_page.path_hash = page_info.path
                        existing_page.sort_order = page_info.sort_order
                        self.repo.update_page(existing_page)
                        updated_count += 1
                        logger.debug(f"更新页面: {page_info.path} (level={page_info.level})")
                else:
                    # 创建新页面
                    new_page = SystemPage(
                        id=str(uuid.uuid4()),
                        path=page_info.path,
                        name=page_info.name,
                        description=page_info.description,
                        level=page_info.level,
                        parent_id=parent_id,
                        path_hash=page_info.path,
                        sort_order=page_info.sort_order
                    )
                    self.repo.create_page(new_page)
                    synced_count += 1
                    logger.debug(f"创建页面: {page_info.path} (level={page_info.level})")

                # 获取当前页面的ID（用于子页面的parent_id）
                current_page = self.repo.get_page_by_path(page_info.path)

                # 递归同步子页面
                if current_page and page_info.children:
                    for child_page in page_info.children:
                        sync_page_recursive(child_page, current_page.id)

            # 同步所有一级页面
            for page_info in pages_config:
                sync_page_recursive(page_info)

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