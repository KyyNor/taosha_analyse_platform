"""
OCR识别服务
集成GLM-OCR SDK，提供图片识别功能
"""
from utils.config import settings
from utils.logger import logger
import requests
import base64
from typing import Optional

class OCRService:
    """OCR识别服务类"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化OCR服务

        Args:
            api_key: GLM-OCR API密钥（可选，默认为配置文件中的值）
        """
        self.api_key = api_key or settings.glm_ocr_api_key
        self.base_url = settings.glm_ocr_base_url or "https://open.bigmodel.cn/api/paas/v4"
        self.timeout = settings.glm_ocr_timeout or 60

        if not self.api_key:
            logger.warning("GLM-OCR API密钥未配置")

    def recognize_to_json(self, image_bytes: bytes) -> dict:
        """
        OCR识别并返回JSON格式结果

        Args:
            image_bytes: 图片字节数据

        Returns:
            JSON格式的识别结果
        """
        return self._call_ocr_api(image_bytes, "json")

    def recognize_to_markdown(self, image_bytes: bytes) -> str:
        """
        OCR识别并返回Markdown格式结果

        Args:
            image_bytes: 图片字节数据

        Returns:
            Markdown格式的识别结果
        """
        return self._call_ocr_api(image_bytes, "markdown")

    def _call_ocr_api(self, image_bytes: bytes, output_format: str = "json") -> dict or str:
        """
        调用GLM-OCR API

        Args:
            image_bytes: 图片字节数据
            output_format: 输出格式（json 或 markdown）

        Returns:
            识别结果
        """
        if not self.api_key:
            raise Exception("GLM-OCR API密钥未配置")

        try:
            # 将图片转换为base64编码
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # 构建请求参数
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": "glm-ocr",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"识别图片内容，返回格式：{output_format}"
                            }
                        ]
                    }
                ],
                "temperature": 0.01,
                "top_p": 0.7,
                "max_tokens": 8192
            }

            # 发送请求
            logger.info("调用GLM-OCR API")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            # 处理响应
            response.raise_for_status()
            result = response.json()

            if "choices" not in result or len(result["choices"]) == 0:
                raise Exception("API响应格式错误")

            # 提取识别结果
            content = result["choices"][0]["message"]["content"]

            logger.info("GLM-OCR API调用成功")
            return content

        except requests.exceptions.RequestException as e:
            logger.error(f"GLM-OCR API请求失败: {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"OCR识别过程中出错: {str(e)}")
            raise Exception(f"识别失败: {str(e)}")
