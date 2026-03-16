"""
OCR识别服务
集成本地GLM-OCR服务，提供图片和PDF识别功能
"""
from utils.config import settings
from utils.logger import logger
import requests
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import tempfile
from urllib.parse import urlparse


class ImagePreprocessInfo(BaseModel):
    """图片预处理信息"""
    original_size: List[int]
    processed_size: List[int]
    image_type: str
    resized: bool


class OCRResult(BaseModel):
    """OCR识别结果"""
    success: bool
    result: str
    mode: str
    preprocess: Optional[ImagePreprocessInfo] = None
    json_result: Optional[Dict[str, Any]] = None


class PDFPageResult(BaseModel):
    """PDF单页识别结果"""
    page: int
    result: str
    preprocess: Dict[str, Any]


class PDFResult(BaseModel):
    """PDF识别结果"""
    success: bool
    mode: str
    total_pages: int
    pages: List[PDFPageResult]
    preprocess: Dict[str, Any]


class OCRService:
    """OCR识别服务类"""

    # 支持的识别模式
    MODE_TEXT = "text"
    MODE_FORMULA = "formula"
    MODE_TABLE = "table"
    MODE_JSON = "json"

    ALL_MODES = [MODE_TEXT, MODE_FORMULA, MODE_TABLE, MODE_JSON]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        初始化OCR服务

        Args:
            api_key: GLM-OCR API密钥（可选，默认为配置文件中的值）
            base_url: OCR服务地址（可选，默认为配置文件中的值）
            timeout: 请求超时时间（可选，默认为配置文件中的值）
        """
        self.api_key = api_key or settings.glm_ocr_api_key
        self.base_url = (base_url or settings.glm_ocr_base_url).rstrip("/")
        self.timeout = timeout or settings.glm_ocr_timeout

        if not self.api_key:
            logger.warning("GLM-OCR API密钥未配置")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-API-Key": self.api_key
        }

    def _download_file_from_url(self, url: str) -> str:
        """
        从URL下载文件到临时目录

        Args:
            url: 文件URL

        Returns:
            临时文件路径
        """
        try:
            logger.info(f"从URL下载文件: {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # 从URL或Content-Type推断文件扩展名
            content_type = response.headers.get("Content-Type", "")
            url_path = urlparse(url).path

            if ".pdf" in url_path.lower() or "application/pdf" in content_type:
                ext = ".pdf"
            elif ".png" in url_path.lower() or "image/png" in content_type:
                ext = ".png"
            elif ".jpg" in url_path.lower() or ".jpeg" in url_path.lower() or "image/jpeg" in content_type:
                ext = ".jpg"
            elif ".gif" in url_path.lower() or "image/gif" in content_type:
                ext = ".gif"
            elif ".webp" in url_path.lower() or "image/webp" in content_type:
                ext = ".webp"
            elif ".bmp" in url_path.lower() or "image/bmp" in content_type:
                ext = ".bmp"
            elif ".tiff" in url_path.lower() or "image/tiff" in content_type:
                ext = ".tiff"
            else:
                ext = ".bin"  # 默认扩展名

            # 保存到临时文件
            temp_dir = settings.glm_ocr_images_path
            temp_file_path = os.path.join(temp_dir, f"ocr_download_{os.urandom(8).hex()}{ext}")

            with open(temp_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"文件已下载到: {temp_file_path}")
            return temp_file_path

        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            raise Exception(f"下载文件失败: {str(e)}")

    def _cleanup_temp_file(self, file_path: str) -> None:
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

    def parse_image(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        mode: str = MODE_TEXT,
        json_schema: Optional[str] = None
    ) -> OCRResult:
        """
        对单张图片进行OCR文字识别

        Args:
            file_path: 图片文件的完整路径（本地文件）
            file_url: 图片文件的远程URL（远程文件）
            mode: 识别模式（text/formula/table/json）
            json_schema: JSON格式模板（当mode=json时必填）

        Returns:
            OCR识别结果

        Raises:
            ValueError: 参数校验失败
            Exception: API调用失败
        """
        temp_file = None
        actual_file_path = file_path

        try:
            # 参数校验
            if mode not in self.ALL_MODES:
                raise ValueError(f"不支持的识别模式: {mode}，支持的模式: {', '.join(self.ALL_MODES)}")

            if mode == self.MODE_JSON and not json_schema:
                raise ValueError("使用 json 模式时必须提供 json_schema 参数")

            # 确定文件来源
            if file_url:
                # 从URL下载文件
                temp_file = self._download_file_from_url(file_url)
                actual_file_path = temp_file
            elif not file_path:
                raise ValueError("必须提供 file_path 或 file_url 参数")

            # 检查文件是否存在
            if not os.path.exists(actual_file_path):
                raise FileNotFoundError(f"文件不存在: {actual_file_path}")

            # 构建请求参数
            data = {
                "file_path": actual_file_path,
                "mode": mode
            }

            if json_schema:
                data["json_schema"] = json_schema

            logger.info(f"调用GLM-OCR API - 文件: {actual_file_path}, 模式: {mode}")

            # 发送请求
            response = requests.post(
                f"{self.base_url}/api/v1/parse",
                data=data,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            # 处理响应
            response.raise_for_status()
            result = response.json()

            logger.info(f"GLM-OCR API调用成功 - 文件: {actual_file_path}")

            return OCRResult(**result)

        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            logger.error(f"GLM-OCR API请求失败: {error_detail}")
            raise Exception(f"API请求失败: {error_detail}")
        except Exception as e:
            logger.error(f"OCR识别过程中出错: {str(e)}")
            raise
        finally:
            # 清理临时文件
            if temp_file:
                self._cleanup_temp_file(temp_file)

    def parse_pdf(
        self,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        mode: str = MODE_TEXT,
        json_schema: Optional[str] = None
    ) -> PDFResult:
        """
        对PDF文件进行多页OCR文字识别

        Args:
            file_path: PDF文件的完整路径（本地文件）
            file_url: PDF文件的远程URL（远程文件）
            mode: 识别模式（text/formula/table/json）
            json_schema: JSON格式模板（当mode=json时必填）

        Returns:
            PDF识别结果

        Raises:
            ValueError: 参数校验失败
            Exception: API调用失败
        """
        temp_file = None
        actual_file_path = file_path

        try:
            # 参数校验
            if mode not in self.ALL_MODES:
                raise ValueError(f"不支持的识别模式: {mode}，支持的模式: {', '.join(self.ALL_MODES)}")

            if mode == self.MODE_JSON and not json_schema:
                raise ValueError("使用 json 模式时必须提供 json_schema 参数")

            # 确定文件来源
            if file_url:
                # 从URL下载文件
                temp_file = self._download_file_from_url(file_url)
                actual_file_path = temp_file
            elif not file_path:
                raise ValueError("必须提供 file_path 或 file_url 参数")

            # 检查文件是否存在
            if not os.path.exists(actual_file_path):
                raise FileNotFoundError(f"文件不存在: {actual_file_path}")

            # 构建请求参数
            data = {
                "file_path": actual_file_path,
                "mode": mode
            }

            if json_schema:
                data["json_schema"] = json_schema

            logger.info(f"调用GLM-OCR PDF API - 文件: {actual_file_path}, 模式: {mode}")

            # 发送请求
            response = requests.post(
                f"{self.base_url}/api/v1/parse_pdf",
                data=data,
                headers=self._get_headers(),
                timeout=self.timeout * 10  # PDF处理时间更长，增加超时时间
            )

            # 处理响应
            response.raise_for_status()
            result = response.json()

            logger.info(f"GLM-OCR PDF API调用成功 - 文件: {actual_file_path}, 总页数: {result.get('total_pages', 0)}")

            return PDFResult(**result)

        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            logger.error(f"GLM-OCR PDF API请求失败: {error_detail}")
            raise Exception(f"API请求失败: {error_detail}")
        except Exception as e:
            logger.error(f"PDF OCR识别过程中出错: {str(e)}")
            raise
        finally:
            # 清理临时文件
            if temp_file:
                self._cleanup_temp_file(temp_file)

    def health_check(self) -> bool:
        """
        检查OCR服务是否正常运行

        Returns:
            服务是否正常
        """
        try:
            response = requests.get(
                f"{self.base_url}/",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result.get("status") == "running"
        except Exception as e:
            logger.error(f"OCR服务健康检查失败: {str(e)}")
            return False
