"""
公共服务API路由
包含OCR识别等公共服务接口
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from middleware.auth_middleware import get_current_user
from services.token_service import UserInfo
from services.common_services.ocr_service import OCRService
from utils.logger import logger
from typing import Optional
import os
import tempfile
import uuid
from pathlib import Path

router = APIRouter(prefix="/common-services", tags=["公共服务"])

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}
# 支持的PDF格式
SUPPORTED_PDF_FORMATS = {".pdf"}

# 最大文件大小 200MB
MAX_FILE_SIZE = 200 * 1024 * 1024


def _save_upload_file_tmp(upload_file: UploadFile) -> str:
    """
    保存上传的文件到临时目录

    Args:
        upload_file: 上传的文件

    Returns:
        临时文件路径
    """
    # 获取文件扩展名
    file_ext = Path(upload_file.filename or "").suffix.lower()

    # 创建临时文件
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_file_path = os.path.join(temp_dir, temp_filename)

    # 保存文件
    with open(temp_file_path, "wb") as f:
        f.write(upload_file.file.read())

    logger.info(f"文件已保存到临时目录: {temp_file_path}")
    return temp_file_path


def _cleanup_temp_file(file_path: str) -> None:
    """
    清理临时文件

    Args:
        file_path: 临时文件路径
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"临时文件已删除: {file_path}")
    except Exception as e:
        logger.warning(f"删除临时文件失败: {file_path}, 错误: {str(e)}")


@router.post("/ocr/recognize", summary="图片OCR识别")
async def ocr_recognize(
    file: UploadFile = File(...),
    mode: str = Form("text"),
    json_schema: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    图片OCR识别接口

    Args:
        file: 上传的图片文件（支持 jpg, png, bmp, gif, webp, tiff）
        mode: 识别模式（text/formula/table/json），默认 text
        json_schema: JSON格式模板（当mode=json时必填）
        api_key: GLM-OCR API密钥（可选，可配置在系统中）
        current_user: 当前用户信息

    Returns:
        识别结果
    """
    temp_file_path = None
    try:
        logger.info(f"OCR识别请求 - 用户: {current_user.user_id}, 文件名: {file.filename}, 模式: {mode}")

        # 验证文件格式
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in SUPPORTED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式: {file_ext}，支持的格式: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
            )

        # 保存到临时文件
        temp_file_path = _save_upload_file_tmp(file)

        # 初始化OCR服务
        ocr_service = OCRService(api_key=api_key)

        # 调用OCR识别
        result = ocr_service.parse_image(
            file_path=temp_file_path,
            mode=mode,
            json_schema=json_schema
        )

        logger.info(f"OCR识别成功 - 用户: {current_user.user_id}")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result.model_dump(),
                "message": "识别成功"
            }
        )

    except ValueError as e:
        logger.error(f"OCR参数错误 - 用户: {current_user.user_id}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OCR识别失败 - 用户: {current_user.user_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file_path:
            _cleanup_temp_file(temp_file_path)


@router.post("/ocr/parse_pdf", summary="PDF OCR识别")
async def ocr_parse_pdf(
    file: UploadFile = File(...),
    mode: str = Form("text"),
    json_schema: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    PDF OCR识别接口

    Args:
        file: 上传的PDF文件
        mode: 识别模式（text/formula/table/json），默认 text
        json_schema: JSON格式模板（当mode=json时必填）
        api_key: GLM-OCR API密钥（可选，可配置在系统中）
        current_user: 当前用户信息

    Returns:
        识别结果（包含每页的识别内容）
    """
    temp_file_path = None
    try:
        logger.info(f"PDF OCR识别请求 - 用户: {current_user.user_id}, 文件名: {file.filename}, 模式: {mode}")

        # 验证文件格式
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in SUPPORTED_PDF_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}，仅支持PDF格式"
            )

        # 保存到临时文件
        temp_file_path = _save_upload_file_tmp(file)

        # 初始化OCR服务
        ocr_service = OCRService(api_key=api_key)

        # 调用PDF OCR识别
        result = ocr_service.parse_pdf(
            file_path=temp_file_path,
            mode=mode,
            json_schema=json_schema
        )

        logger.info(f"PDF OCR识别成功 - 用户: {current_user.user_id}, 总页数: {result.total_pages}")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result.model_dump(),
                "message": f"识别成功，共 {result.total_pages} 页"
            }
        )

    except ValueError as e:
        logger.error(f"PDF OCR参数错误 - 用户: {current_user.user_id}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"PDF OCR识别失败 - 用户: {current_user.user_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF OCR识别失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file_path:
            _cleanup_temp_file(temp_file_path)


@router.get("/ocr/health", summary="OCR服务健康检查")
async def ocr_health_check(
    api_key: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
):
    """
    OCR服务健康检查接口

    Args:
        api_key: GLM-OCR API密钥（可选）
        current_user: 当前用户信息

    Returns:
        服务状态
    """
    try:
        ocr_service = OCRService(api_key=api_key)
        is_healthy = ocr_service.health_check()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "status": "running" if is_healthy else "unavailable",
                    "base_url": ocr_service.base_url
                },
                "message": "服务正常" if is_healthy else "服务不可用"
            }
        )
    except Exception as e:
        logger.error(f"OCR健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "data": {
                    "status": "error",
                    "error": str(e)
                },
                "message": "服务异常"
            }
        )
