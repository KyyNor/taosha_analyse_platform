"""
提示词模板渲染器
支持从数据库获取模板并渲染，提供参数替换功能
"""

import re
from typing import Dict, Any, List, Optional
from utils.logger import logger


class PromptTemplateRenderer:
    """提示词模板渲染器"""

    def __init__(self, template_service=None):
        self.template_service = template_service

    def render_template(self, template_name: str, params: Dict[str, Any],
                       default_template: Optional[str] = None) -> str:
        """
        渲染指定的模板

        Args:
            template_name: 模板名称
            params: 模板参数字典
            default_template: 默认模板（当数据库中找不到模板时使用）

        Returns:
            渲染后的提示词字符串
        """
        try:
            # 从数据库获取模板
            template = None
            if self.template_service:
                template_data = self.template_service.get_template_by_name(template_name)
                if template_data:
                    template = template_data.get('template', '')
                    logger.info(f"使用数据库模板: {template_name}")

            # 如果没有找到模板，使用默认模板
            if not template:
                if default_template:
                    template = default_template
                    logger.warning(f"数据库中未找到模板 '{template_name}'，使用默认模板")
                else:
                    raise ValueError(f"未找到模板 '{template_name}' 且未提供默认模板")

            # 渲染模板
            rendered_prompt = self._replace_placeholders(template, params)

            logger.info(f"模板渲染成功: {template_name}，参数数量: {len(params)}")
            return rendered_prompt

        except Exception as e:
            logger.error(f"模板渲染失败: {template_name}, 错误: {e}")
            raise

    def _replace_placeholders(self, template: str, params: Dict[str, Any]) -> str:
        """
        替换模板中的占位符

        Args:
            template: 模板字符串
            params: 参数字典

        Returns:
            替换后的字符串
        """
        try:
            # 使用正则表达式查找所有占位符 {field_name}
            placeholders = re.findall(r'\{(\w+)\}', template)

            result = template
            missing_params = []

            # 替换每个占位符
            for placeholder in placeholders:
                if placeholder in params:
                    value = params[placeholder]
                    # 确保值是字符串类型
                    if value is None:
                        str_value = ""
                    else:
                        str_value = str(value)

                    # 替换占位符
                    result = result.replace(f'{{{{{placeholder}}}}}', str_value)
                else:
                    missing_params.append(placeholder)
                    logger.warning(f"缺少参数: {placeholder}")

            # 如果有缺失的参数，记录警告但不抛出异常
            if missing_params:
                logger.warning(f"模板渲染时缺少以下参数: {', '.join(missing_params)}")

            return result

        except Exception as e:
            logger.error(f"占位符替换失败: {e}")
            raise

    def validate_template(self, template: str, required_fields: List[str]) -> List[str]:
        """
        验证模板是否包含所有必需的字段

        Args:
            template: 模板字符串
            required_fields: 必需的字段列表

        Returns:
            验证错误列表
        """
        errors = []

        try:
            # 找出模板中的所有占位符
            placeholders = set(re.findall(r'\{\{(\w+)\}\}', template))

            # 找出必需字段
            required_set = set(required_fields)

            # 检查是否有模板中缺少的必需字段
            missing_fields = required_set - placeholders
            if missing_fields:
                errors.append(f"模板中缺少必需的字段: {', '.join(missing_fields)}")

            # 检查是否有模板中多余的字段（警告级别）
            extra_fields = placeholders - required_set
            if extra_fields:
                logger.info(f"模板中包含非必需字段: {', '.join(extra_fields)}")

        except Exception as e:
            errors.append(f"模板验证失败: {e}")

        return errors

    def preview_template(self, template_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        预览模板渲染结果

        Args:
            template_name: 模板名称
            params: 预览参数（可选）

        Returns:
            包含模板信息和预览结果的字典
        """
        try:
            # 获取模板数据
            template_data = None
            if self.template_service:
                template_data = self.template_service.get_template_by_name(template_name)

            if not template_data:
                return {
                    "success": False,
                    "error": f"未找到模板: {template_name}"
                }

            template = template_data.get('template', '')
            fields = template_data.get('fields', [])

            # 构建预览参数
            preview_params = {}
            if params:
                preview_params.update(params)
            else:
                # 使用默认预览值
                for field in fields:
                    if field == "user_input":
                        preview_params[field] = "示例用户查询"
                    elif field == "current_date":
                        from datetime import datetime
                        preview_params[field] = datetime.now().strftime("%Y-%m-%d")
                    elif field == "table_info":
                        preview_params[field] = "示例表信息"
                    else:
                        preview_params[field] = f"示例{field}"

            # 渲染模板
            rendered = self._replace_placeholders(template, preview_params)

            return {
                "success": True,
                "template_name": template_name,
                "template": template,
                "fields": fields,
                "preview_params": preview_params,
                "rendered_preview": rendered
            }

        except Exception as e:
            logger.error(f"模板预览失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_template_fields(self, template_name: str) -> List[str]:
        """
        获取模板中的所有字段

        Args:
            template_name: 模板名称

        Returns:
            字段列表
        """
        try:
            template_data = None
            if self.template_service:
                template_data = self.template_service.get_template_by_name(template_name)

            if not template_data:
                return []

            template = template_data.get('template', '')
            placeholders = re.findall(r'\{\{(\w+)\}\}', template)

            return list(set(placeholders))  # 去重

        except Exception as e:
            logger.error(f"获取模板字段失败: {e}")
            return []

    def render_template_with_fallback(self, template_name: str, params: Dict[str, Any],
                                    fallback_templates: Dict[str, str]) -> str:
        """
        使用回退模板渲染模板

        Args:
            template_name: 主模板名称
            params: 模板参数
            fallback_templates: 回退模板字典

        Returns:
            渲染后的字符串
        """
        try:
            # 尝试使用主模板
            return self.render_template(template_name, params)
        except Exception as e:
            logger.warning(f"主模板渲染失败: {e}，尝试使用回退模板")

            # 尝试使用回退模板
            if template_name in fallback_templates:
                fallback_template = fallback_templates[template_name]
                return self._replace_placeholders(fallback_template, params)
            else:
                raise ValueError(f"未找到回退模板: {template_name}")