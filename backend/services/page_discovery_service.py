"""
页面发现服务
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from services.permission_service import PageService
from utils.logger import logger


class PageDiscoveryService:
    """页面发现服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.page_service = PageService(db)
        self.config_path = Path(__file__).parent.parent / "config" / "pages.yaml"
    
    def load_pages_from_config(self) -> List[Dict[str, str]]:
        """从配置文件加载页面信息"""
        try:
            if not self.config_path.exists():
                logger.warning(f"页面配置文件不存在: {self.config_path}")
                return []
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                pages = config.get('pages', [])
                
                logger.info(f"从配置文件加载了 {len(pages)} 个页面定义")
                return pages
                
        except Exception as e:
            logger.error(f"加载页面配置文件失败: {e}")
            return []
    
    def sync_pages_from_config(self) -> int:
        """从配置文件同步页面到数据库"""
        try:
            pages_config = self.load_pages_from_config()
            if not pages_config:
                logger.warning("没有页面配置需要同步")
                return 0
            
            synced_count = self.page_service.sync_pages_from_config(pages_config)
            
            # 提交事务
            self.db.commit()
            
            logger.info(f"页面配置同步完成，同步了 {synced_count} 个页面")
            return synced_count
            
        except Exception as e:
            logger.error(f"同步页面配置失败: {e}")
            self.db.rollback()
            raise
    
    def sync_pages_on_startup(self) -> None:
        """系统启动时同步页面信息"""
        try:
            logger.info("开始系统启动页面同步...")
            synced_count = self.sync_pages_from_config()
            logger.info(f"系统启动页面同步完成，同步了 {synced_count} 个页面")
            
        except Exception as e:
            logger.error(f"系统启动页面同步失败: {e}")
            # 不抛出异常，避免影响系统启动