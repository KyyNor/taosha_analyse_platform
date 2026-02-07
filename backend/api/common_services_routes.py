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

router = APIRouter(prefix="/common-services", tags=["公共服务"])

@router.post("/ocr/recognize", summary="OCR识别")
async def ocr_recognize(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
    output_format: str = Form("json"),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    OCR识别接口

    Args:
        file: 上传的图片文件
        api_key: GLM-OCR API密钥（可选，可配置在系统中）
        output_format: 输出格式（json 或 markdown）
        current_user: 当前用户信息

    Returns:
        识别结果
    """
    try:
        logger.info(f"OCR识别请求 - 用户: {current_user.user_id}, 文件名: {file.filename}, 输出格式: {output_format}")

        # 读取文件内容
        file_content = await file.read()

        # 初始化OCR服务
        ocr_service = OCRService(api_key=api_key)

        # 调用OCR识别
        if output_format == "markdown":
            result = ocr_service.recognize_to_markdown(file_content)
        else:
            result = ocr_service.recognize_to_json(file_content)

        logger.info(f"OCR识别成功 - 用户: {current_user.user_id}")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result,
                "message": "识别成功"
            }
        )
    except Exception as e:
        logger.error(f"OCR识别失败 - 用户: {current_user.user_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR识别失败: {str(e)}"
        )
