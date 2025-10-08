"""
元数据管理服务
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from models.metadata_models import (
    MetadataDataTheme, MetadataTable, MetadataField, 
    MetadataGlossary, MetadataTableTheme, MetadataRelation
)
from schemas.metadata_schemas import (
    DataThemeCreate, DataThemeUpdate, DataThemeResponse,
    TableCreate, TableUpdate, TableResponse,
    FieldCreate, FieldUpdate, FieldResponse,
    GlossaryCreate, GlossaryUpdate, GlossaryResponse
)
from schemas.base import PaginatedData, PaginationParams
from utils.exceptions import ResourceNotFoundException, BusinessLogicException
from utils.logger import get_logger

logger = get_logger(__name__)


class MetadataService:
    """元数据管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== 数据主题管理 ==========
    async def create_theme(self, theme_data: DataThemeCreate, user_id: int) -> DataThemeResponse:
        """创建数据主题"""
        # 检查主题名称是否已存在
        existing = await self.db.execute(
            select(MetadataDataTheme).where(MetadataDataTheme.theme_name == theme_data.theme_name)
        )
        if existing.scalar_one_or_none():
            raise BusinessLogicException(f"主题名称 '{theme_data.theme_name}' 已存在")
        
        # 创建主题
        theme = MetadataDataTheme(
            **theme_data.dict(),
            created_by=user_id,
            updated_by=user_id
        )
        self.db.add(theme)
        await self.db.flush()
        
        logger.info(f"用户 {user_id} 创建数据主题: {theme.theme_name}")
        return DataThemeResponse.from_orm(theme)
    
    async def get_theme(self, theme_id: int) -> DataThemeResponse:
        """获取数据主题"""
        theme = await self.db.get(MetadataDataTheme, theme_id)
        if not theme:
            raise ResourceNotFoundException(f"数据主题 {theme_id} 不存在")
        
        # 统计表数量
        table_count_result = await self.db.execute(
            select(func.count(MetadataTableTheme.table_id))
            .where(MetadataTableTheme.theme_id == theme_id)
        )
        table_count = table_count_result.scalar() or 0
        
        theme_data = DataThemeResponse.from_orm(theme)
        theme_data.table_count = table_count
        return theme_data
    
    async def update_theme(self, theme_id: int, theme_data: DataThemeUpdate, user_id: int) -> DataThemeResponse:
        """更新数据主题"""
        theme = await self.db.get(MetadataDataTheme, theme_id)
        if not theme:
            raise ResourceNotFoundException(f"数据主题 {theme_id} 不存在")
        
        # 检查名称重复
        if theme_data.theme_name and theme_data.theme_name != theme.theme_name:
            existing = await self.db.execute(
                select(MetadataDataTheme).where(
                    and_(
                        MetadataDataTheme.theme_name == theme_data.theme_name,
                        MetadataDataTheme.id != theme_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise BusinessLogicException(f"主题名称 '{theme_data.theme_name}' 已存在")
        
        # 更新字段
        update_data = theme_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(theme, field, value)
        theme.updated_by = user_id
        
        await self.db.flush()
        logger.info(f"用户 {user_id} 更新数据主题 {theme_id}: {theme.theme_name}")
        return DataThemeResponse.from_orm(theme)
    
    async def delete_theme(self, theme_id: int, user_id: int) -> bool:
        """删除数据主题"""
        theme = await self.db.get(MetadataDataTheme, theme_id)
        if not theme:
            raise ResourceNotFoundException(f"数据主题 {theme_id} 不存在")
        
        # 检查是否有关联的表
        table_count_result = await self.db.execute(
            select(func.count(MetadataTableTheme.table_id))
            .where(MetadataTableTheme.theme_id == theme_id)
        )
        table_count = table_count_result.scalar() or 0
        
        if table_count > 0:
            raise BusinessLogicException(f"主题下还有 {table_count} 个表，无法删除")
        
        await self.db.delete(theme)
        logger.info(f"用户 {user_id} 删除数据主题 {theme_id}: {theme.theme_name}")
        return True
    
    async def list_themes(self, params: Dict[str, Any]) -> PaginatedData[DataThemeResponse]:
        """获取数据主题列表"""
        query = select(MetadataDataTheme)
        
        # 应用过滤条件
        if params.get('is_public') is not None:
            query = query.where(MetadataDataTheme.is_public == params['is_public'])
        
        if params.get('keyword'):
            keyword = f"%{params['keyword']}%"
            query = query.where(
                or_(
                    MetadataDataTheme.theme_name.ilike(keyword),
                    MetadataDataTheme.theme_description.ilike(keyword)
                )
            )
        
        # 排序
        if params.get('sort_by') == 'name':
            if params.get('sort_order') == 'desc':
                query = query.order_by(MetadataDataTheme.theme_name.desc())
            else:
                query = query.order_by(MetadataDataTheme.theme_name.asc())
        else:
            query = query.order_by(MetadataDataTheme.sort_order.asc(), MetadataDataTheme.created_at.desc())
        
        # 分页
        page = params.get('page', 1)
        size = params.get('size', 20)
        offset = (page - 1) * size
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 获取数据
        result = await self.db.execute(query.offset(offset).limit(size))
        themes = result.scalars().all()
        
        # 转换为响应模型
        theme_responses = []
        for theme in themes:
            # 统计每个主题的表数量
            table_count_result = await self.db.execute(
                select(func.count(MetadataTableTheme.table_id))
                .where(MetadataTableTheme.theme_id == theme.id)
            )
            table_count = table_count_result.scalar() or 0
            
            theme_data = DataThemeResponse.from_orm(theme)
            theme_data.table_count = table_count
            theme_responses.append(theme_data)
        
        return PaginatedData.create(theme_responses, total, page, size)
    
    # ========== 表元数据管理 ==========
    async def create_table(self, table_data: TableCreate, user_id: int) -> TableResponse:
        """创建表元数据"""
        # 检查表名是否已存在
        existing = await self.db.execute(
            select(MetadataTable).where(MetadataTable.table_name_en == table_data.table_name_en)
        )
        if existing.scalar_one_or_none():
            raise BusinessLogicException(f"表英文名 '{table_data.table_name_en}' 已存在")
        
        # 创建表
        table_dict = table_data.dict(exclude={'theme_ids'})
        table = MetadataTable(
            **table_dict,
            created_by=user_id,
            updated_by=user_id
        )
        self.db.add(table)
        await self.db.flush()
        
        # 关联主题
        if table_data.theme_ids:
            for theme_id in table_data.theme_ids:
                theme_relation = MetadataTableTheme(
                    table_id=table.id,
                    theme_id=theme_id,
                    created_by=user_id
                )
                self.db.add(theme_relation)
        
        await self.db.flush()
        logger.info(f"用户 {user_id} 创建表元数据: {table.table_name_en}")
        
        return await self._build_table_response(table)
    
    async def get_table(self, table_id: int) -> TableResponse:
        """获取表元数据"""
        table = await self.db.get(MetadataTable, table_id)
        if not table:
            raise ResourceNotFoundException(f"表 {table_id} 不存在")
        
        return await self._build_table_response(table)
    
    async def update_table(self, table_id: int, table_data: TableUpdate, user_id: int) -> TableResponse:
        """更新表元数据"""
        table = await self.db.get(MetadataTable, table_id)
        if not table:
            raise ResourceNotFoundException(f"表 {table_id} 不存在")
        
        # 检查英文名重复
        if table_data.table_name_en and table_data.table_name_en != table.table_name_en:
            existing = await self.db.execute(
                select(MetadataTable).where(
                    and_(
                        MetadataTable.table_name_en == table_data.table_name_en,
                        MetadataTable.id != table_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise BusinessLogicException(f"表英文名 '{table_data.table_name_en}' 已存在")
        
        # 更新基本字段
        update_data = table_data.dict(exclude_unset=True, exclude={'theme_ids'})
        for field, value in update_data.items():
            setattr(table, field, value)
        table.updated_by = user_id
        
        # 更新主题关联
        if table_data.theme_ids is not None:
            # 删除现有关联
            await self.db.execute(
                select(MetadataTableTheme).where(MetadataTableTheme.table_id == table_id)
            )
            
            # 添加新关联
            for theme_id in table_data.theme_ids:
                theme_relation = MetadataTableTheme(
                    table_id=table_id,
                    theme_id=theme_id,
                    created_by=user_id
                )
                self.db.add(theme_relation)
        
        await self.db.flush()
        logger.info(f"用户 {user_id} 更新表元数据 {table_id}: {table.table_name_en}")
        
        return await self._build_table_response(table)
    
    async def _build_table_response(self, table: MetadataTable) -> TableResponse:
        """构建表响应对象"""
        # 统计字段数量
        field_count_result = await self.db.execute(
            select(func.count(MetadataField.id))
            .where(MetadataField.table_id == table.id)
        )
        field_count = field_count_result.scalar() or 0
        
        # 获取关联的主题
        themes_result = await self.db.execute(
            select(MetadataDataTheme)
            .join(MetadataTableTheme, MetadataDataTheme.id == MetadataTableTheme.theme_id)
            .where(MetadataTableTheme.table_id == table.id)
        )
        themes = themes_result.scalars().all()
        
        table_data = TableResponse.from_orm(table)
        table_data.field_count = field_count
        table_data.themes = [DataThemeResponse.from_orm(theme) for theme in themes]
        
        return table_data
    
    # ========== 字段元数据管理 ==========
    async def create_field(self, field_data: FieldCreate, user_id: int) -> FieldResponse:
        """创建字段元数据"""
        # 检查表是否存在
        table = await self.db.get(MetadataTable, field_data.table_id)
        if not table:
            raise ResourceNotFoundException(f"表 {field_data.table_id} 不存在")
        
        # 检查字段名是否在同一表中重复
        existing = await self.db.execute(
            select(MetadataField).where(
                and_(
                    MetadataField.table_id == field_data.table_id,
                    MetadataField.field_name_en == field_data.field_name_en
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessLogicException(f"字段英文名 '{field_data.field_name_en}' 在表中已存在")
        
        # 创建字段
        field = MetadataField(
            **field_data.dict(),
            created_by=user_id,
            updated_by=user_id
        )
        self.db.add(field)
        await self.db.flush()
        
        logger.info(f"用户 {user_id} 创建字段元数据: {table.table_name_en}.{field.field_name_en}")
        return await self._build_field_response(field)
    
    async def _build_field_response(self, field: MetadataField) -> FieldResponse:
        """构建字段响应对象"""
        # 获取所属表信息
        table = await self.db.get(MetadataTable, field.table_id)
        
        field_data = FieldResponse.from_orm(field)
        if table:
            field_data.table_name_cn = table.table_name_cn
            field_data.table_name_en = table.table_name_en
        
        return field_data
    
    # ========== 术语管理 ==========
    async def create_glossary(self, glossary_data: GlossaryCreate, user_id: int) -> GlossaryResponse:
        """创建术语"""
        # 检查术语名称是否已存在
        existing = await self.db.execute(
            select(MetadataGlossary).where(MetadataGlossary.term_name == glossary_data.term_name)
        )
        if existing.scalar_one_or_none():
            raise BusinessLogicException(f"术语 '{glossary_data.term_name}' 已存在")
        
        # 处理JSON字段
        glossary_dict = glossary_data.dict()
        if glossary_dict.get('aliases'):
            glossary_dict['aliases'] = glossary_data.aliases
        if glossary_dict.get('related_terms'):
            glossary_dict['related_terms'] = glossary_data.related_terms
        
        # 创建术语
        glossary = MetadataGlossary(
            **glossary_dict,
            user_id=user_id,
            created_by=user_id,
            updated_by=user_id
        )
        self.db.add(glossary)
        await self.db.flush()
        
        logger.info(f"用户 {user_id} 创建术语: {glossary.term_name}")
        return GlossaryResponse.from_orm(glossary)


# 工厂函数
def get_metadata_service(db: AsyncSession) -> MetadataService:
    """获取元数据服务实例"""
    return MetadataService(db)