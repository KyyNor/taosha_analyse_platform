"""
知识库管理API路由
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from models.db_base import get_db
from models.metadata_models import MetadataKnowledgeDocument, MetadataKnowledgeFragment
from repositories.metadata_repository import KnowledgeDocumentRepository, KnowledgeFragmentRepository
from services.knowledge.document_parser_service import DocumentParserService
from services.knowledge.fragment_generation_service import FragmentGenerationService
from services.knowledge.topic_extraction_service import TopicExtractionService
from api.endpoint_models import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentUpdate,
    FragmentGenerationRequest,
    TopicExtractionRequest,
    SaveFragmentsRequest,
    FragmentUpdateRequest,
    DocumentDetailResponse,
    CandidateFragmentsResponse,
    SaveFragmentsResponse,
    FragmentData,
)
from utils.logger import logger
from datetime import datetime

router = APIRouter()


# ==================== 依赖注入 ====================

def get_document_repository(db: Session = Depends(get_db)) -> KnowledgeDocumentRepository:
    """获取知识文档Repository"""
    return KnowledgeDocumentRepository(db)

def get_fragment_repository(db: Session = Depends(get_db)) -> KnowledgeFragmentRepository:
    """获取知识片段Repository"""
    return KnowledgeFragmentRepository(db)

def get_document_parser() -> DocumentParserService:
    """获取文档解析服务"""
    return DocumentParserService()

def get_fragment_generation_service(db: Session = Depends(get_db)) -> FragmentGenerationService:
    """获取片段生成服务"""
    return FragmentGenerationService(db)

def get_topic_extraction_service(db: Session = Depends(get_db)) -> TopicExtractionService:
    """获取主题提取服务"""
    return TopicExtractionService(db)


# ==================== 文档管理API ====================

@router.post("/documents/add", response_model=dict, summary="新增知识文档")
async def create_document(
    request: KnowledgeDocumentRequest,
    doc_repo: KnowledgeDocumentRepository = Depends(get_document_repository),
    parser: DocumentParserService = Depends(get_document_parser)
):
    """
    新增知识文档

    支持两种方式：
    1. 文件路径：提供 source_path（绝对路径）
    2. 文本输入：提供 raw_content（直接文本）

    Returns:
        创建的文档信息
    """
    try:
        # 验证输入
        if request.source_type == "file" or request.source_type == "sql":
            if not request.source_path:
                raise HTTPException(status_code=400, detail="文件路径不能为空")
            # 从文件解析
            parsed_data = parser.parse_from_file(request.source_path)
            raw_content = parsed_data['raw_content']
            file_size = parsed_data['file_size']
            content_hash = parsed_data['content_hash']
        elif request.source_type == "text":
            if not request.raw_content:
                raise HTTPException(status_code=400, detail="文本内容不能为空")
            # 从文本解析
            parsed_data = parser.parse_from_text(request.raw_content, request.title)
            raw_content = parsed_data['raw_content']
            file_size = parsed_data['file_size']
            content_hash = parsed_data['content_hash']
        else:
            raise HTTPException(status_code=400, detail=f"不支持的源类型: {request.source_type}")

        # 检查是否已存在相同哈希的文档（去重）
        existing = doc_repo.db.query(MetadataKnowledgeDocument).filter(
            MetadataKnowledgeDocument.content_hash == content_hash
        ).first()
        if existing:
            logger.warning(f"已存在相同内容的文档: {existing.id}")
            raise HTTPException(status_code=409, detail="已存在相同内容的文档")

        # 创建文档
        document = doc_repo.create(
            title=request.title,
            source_type=request.source_type,
            source_path=request.source_path,
            raw_content=raw_content,
            file_size=file_size,
            content_hash=content_hash,
            processing_status="pending",
            fragment_count=0
        )

        logger.info(f"成功创建知识文档: ID={document.id}, 标题={document.title}")

        return {
            "id": document.id,
            "title": document.title,
            "source_type": document.source_type,
            "processing_status": document.processing_status,
            "created_at": document.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建文档失败: {str(e)}")


@router.get("/documents", response_model=dict, summary="获取文档列表")
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source_type: str = Query(None, description="源类型过滤"),
    search: str = Query(None, description="搜索关键词"),
    doc_repo: KnowledgeDocumentRepository = Depends(get_document_repository)
):
    """
    获取文档列表（分页）

    支持过滤：
    - source_type: 按源类型过滤
    - search: 按标题或内容搜索
    """
    try:
        # 构建查询
        query = doc_repo.db.query(MetadataKnowledgeDocument)

        # 应用过滤条件
        if source_type:
            query = query.filter(MetadataKnowledgeDocument.source_type == source_type)

        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    MetadataKnowledgeDocument.title.contains(search),
                    MetadataKnowledgeDocument.raw_content.contains(search)
                )
            )

        # 计算总数
        total = query.count()

        # 应用分页和排序
        documents = query.order_by(MetadataKnowledgeDocument.created_at.desc())\
                          .offset((page - 1) * page_size)\
                          .limit(page_size)\
                          .all()

        # 转换为响应格式
        items = [
            {
                "id": doc.id,
                "title": doc.title,
                "source_type": doc.source_type,
                "source_path": doc.source_path,
                "processing_status": doc.processing_status,
                "fragment_count": doc.fragment_count,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            }
            for doc in documents
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse, summary="获取文档详情")
async def get_document_detail(
    doc_id: int,
    doc_repo: KnowledgeDocumentRepository = Depends(get_document_repository),
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    获取文档详情（包含片段列表）
    """
    try:
        # 获取文档
        document = doc_repo.get_with_fragments(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 转换片段为响应格式
        fragments = [
            FragmentData(
                id=frag.id,
                title=frag.title,
                content=frag.content,
                summary=frag.summary,
                generation_method=frag.generation_method,
                extraction_theme=frag.extraction_theme,
                is_modified=frag.is_modified
            )
            for frag in document.fragments
        ]

        return DocumentDetailResponse(
            id=document.id,
            title=document.title,
            source_type=document.source_type,
            source_path=document.source_path,
            raw_content=document.raw_content,
            file_size=document.file_size,
            content_hash=document.content_hash,
            processing_status=document.processing_status,
            fragment_count=document.fragment_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
            fragments=fragments
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")


@router.delete("/documents/{doc_id}", response_model=dict, summary="删除文档")
async def delete_document(
    doc_id: int,
    doc_repo: KnowledgeDocumentRepository = Depends(get_document_repository),
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    删除文档（及其所有片段）
    """
    try:
        # 检查文档是否存在
        document = doc_repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除文档的所有片段
        frag_repo.delete_by_document_id(doc_id)

        # 删除文档
        doc_repo.delete(doc_id)
        doc_repo.db.commit()

        logger.info(f"成功删除文档: ID={doc_id}")

        return {"message": "文档删除成功", "document_id": doc_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.put("/documents/{doc_id}", response_model=dict, summary="更新文档")
async def update_document(
    doc_id: int,
    request: KnowledgeDocumentUpdate,
    doc_repo: KnowledgeDocumentRepository = Depends(get_document_repository)
):
    """
    更新文档信息
    """
    try:
        # 检查文档是否存在
        document = doc_repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 构建更新数据
        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.processing_status is not None:
            update_data['processing_status'] = request.processing_status

        # 更新文档
        updated_doc = doc_repo.update(doc_id, **update_data)

        logger.info(f"成功更新文档: ID={doc_id}")

        return {
            "message": "文档更新成功",
            "document_id": doc_id,
            "title": updated_doc.title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新文档失败: {str(e)}")


# ==================== 片段生成和主题提取API ====================

@router.post("/documents/{doc_id}/generate-fragments", response_model=CandidateFragmentsResponse, summary="生成知识片段")
async def generate_fragments(
    doc_id: int,
    request: FragmentGenerationRequest,
    frag_gen_service: FragmentGenerationService = Depends(get_fragment_generation_service)
):
    """
    生成知识片段（LLM，返回候选片段）

    生成的片段暂存到页面，用户可以查看、编辑和选择。
    只有用户选择的片段才会被保存到数据库。
    """
    try:
        # 验证文档ID
        if doc_id != request.document_id:
            raise HTTPException(status_code=400, detail="文档ID不匹配")

        # 生成片段
        result = frag_gen_service.generate_fragments(
            document_id=request.document_id,
            fragment_count=request.fragment_count
        )

        # 转换为响应格式
        fragments = [
            FragmentData(
                id=None,  # 候选片段没有ID
                title=frag['title'],
                content=frag['content'],
                summary=frag.get('summary'),
                generation_method=frag['generation_method'],
                extraction_theme=frag.get('extraction_theme'),
                is_modified=frag['is_modified']
            )
            for frag in result['fragments']
        ]

        return CandidateFragmentsResponse(
            document_id=result['document_id'],
            fragments=fragments,
            total_count=result['total_count']
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成片段失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成片段失败: {str(e)}")


@router.post("/documents/{doc_id}/extract", response_model=CandidateFragmentsResponse, summary="主题提取")
async def extract_by_topic(
    doc_id: int,
    request: TopicExtractionRequest,
    topic_service: TopicExtractionService = Depends(get_topic_extraction_service)
):
    """
    主题提取（返回提取的片段，暂存）

    根据用户提供的主题和提取逻辑，从文档中提取相关知识。
    提取的片段暂存到页面，与LLM自动生成的片段一起展示。
    用户可以选择要保存的片段。
    """
    try:
        # 提取知识
        result = topic_service.extract_by_topic(
            document_id=doc_id,
            extraction_theme=request.extraction_theme,
            extraction_prompt=request.extraction_prompt
        )

        # 转换为响应格式
        fragment = FragmentData(
            id=None,  # 候选片段没有ID
            title=result['fragment']['title'],
            content=result['fragment']['content'],
            summary=result['fragment'].get('summary'),
            generation_method=result['fragment']['generation_method'],
            extraction_theme=result['fragment']['extraction_theme'],
            is_modified=result['fragment']['is_modified']
        )

        return CandidateFragmentsResponse(
            document_id=result['document_id'],
            fragments=[fragment],
            total_count=1
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"主题提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"主题提取失败: {str(e)}")


@router.post("/documents/{doc_id}/save-fragments", response_model=SaveFragmentsResponse, summary="保存选中的片段")
async def save_selected_fragments(
    doc_id: int,
    request: SaveFragmentsRequest,
    frag_gen_service: FragmentGenerationService = Depends(get_fragment_generation_service)
):
    """
    保存选中的片段到数据库

    用户勾选想要的片段后，调用此接口保存到数据库。
    只有选中的片段会被保存，未选中的片段会被丢弃。
    支持用户编辑片段内容后再保存。
    """
    try:
        # 准备片段数据
        fragments_to_save = []

        # 如果用户提供了编辑内容，应用编辑
        for frag_id in request.fragment_ids:
            if frag_id in request.edited_contents:
                # 用户编辑过的片段
                edited = request.edited_contents[frag_id]
                fragments_to_save.append({
                    'id': frag_id,
                    'title': edited.get('title'),
                    'content': edited.get('content'),
                    'summary': edited.get('summary'),
                    'is_modified': True
                })
            else:
                # 未编辑的片段（从候选列表中选择）
                # 注意：这里需要从前端传递完整的片段数据
                fragments_to_save.append({'id': frag_id})

        # 保存片段
        result = frag_gen_service.save_selected_fragments(
            document_id=doc_id,
            selected_fragments=fragments_to_save
        )

        return SaveFragmentsResponse(
            saved_fragment_ids=result['saved_fragment_ids'],
            saved_count=result['saved_count'],
            document_id=result['document_id']
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"保存片段失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存片段失败: {str(e)}")


# ==================== 片段管理API ====================


# ==================== 片段管理API ====================

@router.get("/fragments", response_model=dict, summary="获取片段列表")
async def get_fragments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    document_id: int = Query(None, description="文档ID过滤"),
    generation_method: str = Query(None, description="生成方式过滤"),
    search: str = Query(None, description="搜索关键词"),
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    获取片段列表（分页）

    支持过滤：
    - document_id: 按文档ID过滤
    - generation_method: 按生成方式过滤
    - search: 按标题、内容或摘要搜索
    """
    try:
        # 构建查询
        query = frag_repo.db.query(MetadataKnowledgeFragment)

        # 应用过滤条件
        if document_id:
            query = query.filter(MetadataKnowledgeFragment.document_id == document_id)

        if generation_method:
            query = query.filter(MetadataKnowledgeFragment.generation_method == generation_method)

        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    MetadataKnowledgeFragment.title.contains(search),
                    MetadataKnowledgeFragment.content.contains(search),
                    MetadataKnowledgeFragment.summary.contains(search)
                )
            )

        # 计算总数
        total = query.count()

        # 应用分页和排序
        fragments = query.order_by(MetadataKnowledgeFragment.created_at.desc())\
                          .offset((page - 1) * page_size)\
                          .limit(page_size)\
                          .all()

        # 转换为响应格式
        items = [
            {
                "id": frag.id,
                "document_id": frag.document_id,
                "title": frag.title,
                "content": frag.content,
                "summary": frag.summary,
                "generation_method": frag.generation_method,
                "extraction_theme": frag.extraction_theme,
                "is_modified": frag.is_modified,
                "created_at": frag.created_at.isoformat(),
                "updated_at": frag.updated_at.isoformat()
            }
            for frag in fragments
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        logger.error(f"获取片段列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取片段列表失败: {str(e)}")


@router.get("/fragments/{frag_id}", response_model=dict, summary="获取片段详情")
async def get_fragment_detail(
    frag_id: int,
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    获取片段详情
    """
    try:
        fragment = frag_repo.get_by_id(frag_id)
        if not fragment:
            raise HTTPException(status_code=404, detail="片段不存在")

        return {
            "id": fragment.id,
            "document_id": fragment.document_id,
            "title": fragment.title,
            "content": fragment.content,
            "summary": fragment.summary,
            "generation_method": fragment.generation_method,
            "extraction_theme": fragment.extraction_theme,
            "extraction_prompt": fragment.extraction_prompt,
            "is_modified": fragment.is_modified,
            "created_at": fragment.created_at.isoformat(),
            "updated_at": fragment.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取片段详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取片段详情失败: {str(e)}")


@router.put("/fragments/{frag_id}", response_model=dict, summary="更新片段")
async def update_fragment(
    frag_id: int,
    request: FragmentUpdateRequest,
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    更新片段内容
    """
    try:
        # 检查片段是否存在
        fragment = frag_repo.get_by_id(frag_id)
        if not fragment:
            raise HTTPException(status_code=404, detail="片段不存在")

        # 构建更新数据
        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.content is not None:
            update_data['content'] = request.content
        if request.summary is not None:
            update_data['summary'] = request.summary
        if request.is_modified is not None:
            update_data['is_modified'] = request.is_modified

        # 如果用户修改了内容，标记为已修改
        if request.title is not None or request.content is not None:
            update_data['is_modified'] = True

        # 更新片段
        updated_frag = frag_repo.update(frag_id, **update_data)

        logger.info(f"成功更新片段: ID={frag_id}")

        return {
            "message": "片段更新成功",
            "fragment_id": frag_id,
            "title": updated_frag.title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新片段失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新片段失败: {str(e)}")


@router.delete("/fragments/{frag_id}", response_model=dict, summary="删除片段")
async def delete_fragment(
    frag_id: int,
    frag_repo: KnowledgeFragmentRepository = Depends(get_fragment_repository)
):
    """
    删除片段
    """
    try:
        # 检查片段是否存在
        fragment = frag_repo.get_by_id(frag_id)
        if not fragment:
            raise HTTPException(status_code=404, detail="片段不存在")

        # 删除片段
        frag_repo.delete(frag_id)
        frag_repo.db.commit()

        logger.info(f"成功删除片段: ID={frag_id}")

        return {"message": "片段删除成功", "fragment_id": frag_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除片段失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除片段失败: {str(e)}")
