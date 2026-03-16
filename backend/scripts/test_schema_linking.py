"""
Schema Linking智能筛选服务测试脚本

测试两阶段Schema筛选流程：
1. 向量检索召回候选表
2. LLM精确筛选最相关表
"""

import sys
import asyncio
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.db_base import SessionLocal
from services.agents.schema_linking_service import SchemaLinkingService
from models.prompt_templates import SchemaLinkingTemplates
from utils.logger import logger


class MockLLMService:
    """模拟LLM服务（用于测试）"""

    def __init__(self):
        self.call_count = 0

    async def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.1) -> str:
        """模拟LLM生成

        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            模拟的LLM响应
        """
        self.call_count += 1
        logger.info(f"LLM调用 #{self.call_count}")
        logger.debug(f"提示词长度: {len(prompt)} 字符")

        # 简单的规则匹配（模拟LLM筛选逻辑）
        if "活期" in prompt or "定期" in prompt:
            if "余额" in prompt:
                # 查询活期/定期余额 -> 账户明细表
                return '''```json
{
  "selected_tables": ["hxb_acct_dtl"],
  "reasoning": "问题涉及活期和定期存款的余额分布，只需要账户明细表中的产品类型和余额字段",
  "table_count": 1
}
```'''
            else:
                # 查询活期/定期客户数量 -> 账户明细表
                return '''```json
{
  "selected_tables": ["hxb_acct_dtl"],
  "reasoning": "问题涉及活期存款客户数量统计，只需要账户明细表",
  "table_count": 1
}
```'''

        elif "交易" in prompt or "trans" in prompt.lower():
            # 交易相关 -> 交易流水表
            return '''```json
{
  "selected_tables": ["hxb_trans_log"],
  "reasoning": "问题涉及交易统计，需要交易流水表",
  "table_count": 1
}
```'''

        elif "客户" in prompt and ("余额" in prompt or "交易" in prompt):
            # 客户信息 + 余额/交易 -> 需要关联
            return '''```json
{
  "selected_tables": ["hxb_cust_info", "hxb_acct_dtl"],
  "reasoning": "问题涉及客户信息和账户余额，需要关联客户信息表和账户明细表",
  "table_count": 2
}
```'''

        else:
            # 默认返回前2个表
            return '''```json
{
  "selected_tables": ["hxb_acct_dtl", "hxb_cust_info"],
  "reasoning": "根据问题相关性，选择账户明细表和客户信息表",
  "table_count": 2
}
```'''


async def test_prompt_templates():
    """测试提示词模板"""
    logger.info("=" * 80)
    logger.info("测试提示词模板")
    logger.info("=" * 80)

    # 获取简化模板
    simple_template = SchemaLinkingTemplates.get_template(use_simple=True)
    logger.info(f"\n简化模板长度: {len(simple_template)} 字符")

    # 填充简化模板
    prompt = simple_template.format(
        question="查询活期存款客户的数量",
        candidate_tables="- hxb_acct_dtl: 账户明细表\n- hxb_cust_info: 客户信息表"
    )
    logger.info(f"\n填充后的提示词:\n{prompt}")

    # 获取完整模板（不填充，只检查长度）
    try:
        # 直接访问模板而不填充
        full_template_raw = SchemaLinkingTemplates.SCHEMA_LINKING_TEMPLATE
        logger.info(f"\n完整模板原始长度: {len(full_template_raw)} 字符")
    except Exception as e:
        logger.warning(f"完整模板访问失败: {e}")


async def test_schema_linking_service():
    """测试Schema Linking服务"""
    logger.info("\n" + "=" * 80)
    logger.info("测试Schema Linking服务")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 初始化模拟LLM服务
        mock_llm = MockLLMService()

        # 初始化Schema Linking服务
        schema_linking_service = SchemaLinkingService(db, llm_service=mock_llm)
        logger.info("Schema Linking服务初始化成功\n")

        # 测试问题列表
        test_questions = [
            "查询活期存款客户的数量",
            "查询2024年每月的交易总额",
            "查询客户张三的账户余额和交易记录",
            "统计各产品类型的余额分布"
        ]

        for question in test_questions:
            logger.info("\n" + "-" * 80)
            logger.info(f"用户问题: {question}")
            logger.info("-" * 80)

            # 执行Schema Linking
            result = await schema_linking_service.select_relevant_tables(
                question=question,
                candidate_top_k=10,
                selected_top_k=5,
                use_cache=True
            )

            # 显示结果
            logger.info(f"\n筛选结果:")
            logger.info(f"  选择的表: {result.selected_tables}")
            logger.info(f"  选择理由: {result.reasoning}")
            logger.info(f"  候选表数量: {result.candidate_count}")
            logger.info(f"  是否使用降级: {result.use_fallback}")

        # 显示缓存统计
        cache_stats = schema_linking_service.get_cache_stats()
        logger.info("\n" + "=" * 80)
        logger.info(f"缓存统计: {json.dumps(cache_stats, indent=2, ensure_ascii=False)}")

        # 测试缓存效果
        logger.info("\n测试缓存效果...")
        logger.info("再次询问相同问题，应该使用缓存")

        result = await schema_linking_service.select_relevant_tables(
            question="查询活期存款客户的数量",
            candidate_top_k=10,
            selected_top_k=5,
            use_cache=True
        )

        logger.info(f"\n筛选结果: {result.selected_tables}")
        logger.info(f"LLM调用次数: {mock_llm.call_count}（应该保持不变）")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


async def test_fallback_strategy():
    """测试降级策略"""
    logger.info("\n" + "=" * 80)
    logger.info("测试降级策略")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 测试1：无LLM服务
        logger.info("\n测试1：无LLM服务（直接降级到向量检索）")
        schema_linking_service = SchemaLinkingService(db, llm_service=None)

        result = await schema_linking_service.select_relevant_tables(
            question="查询活期存款客户的数量",
            candidate_top_k=10,
            selected_top_k=5
        )

        logger.info(f"\n筛选结果:")
        logger.info(f"  选择的表: {result.selected_tables}")
        logger.info(f"  是否使用降级: {result.use_fallback}")

        # 测试2：强制降级
        logger.info("\n测试2：强制降级策略")

        mock_llm = MockLLMService()
        schema_linking_service = SchemaLinkingService(db, llm_service=mock_llm)

        result = await schema_linking_service.select_relevant_tables(
            question="查询活期存款客户的数量",
            candidate_top_k=10,
            selected_top_k=5,
            force_fallback=True
        )

        logger.info(f"\n筛选结果:")
        logger.info(f"  选择的表: {result.selected_tables}")
        logger.info(f"  是否使用降级: {result.use_fallback}")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


async def test_table_description_extraction():
    """测试表描述提取功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试表描述提取功能")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        schema_linking_service = SchemaLinkingService(db, llm_service=None)

        # 模拟Schema摘要
        mock_summary = """表名：hxb_acct_dtl
表注释：账户明细表

字段列表：
1. acct_no VARCHAR(50) - 账号
   值样例：['6222021234567890']
2. acct_desc VARCHAR(10) - 产品类型
   值样例：['S', 'T']
3. balance DECIMAL(18,2) - 账户余额
   值范围：0.00 ~ 999999999.99
...

关键字段：acct_desc, balance
"""

        # 测试描述提取
        description = schema_linking_service._extract_table_description(
            "hxb_acct_dtl",
            mock_summary
        )

        logger.info(f"\n提取的表描述:\n{description}")
        logger.info(f"\n描述长度: {len(description)} 字符")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


async def main():
    """主测试函数"""
    logger.info("开始Schema Linking服务测试\n")

    # 测试1：提示词模板
    await test_prompt_templates()

    # 测试2：Schema Linking服务
    await test_schema_linking_service()

    # 测试3：降级策略
    await test_fallback_strategy()

    # 测试4：表描述提取
    await test_table_description_extraction()

    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(main())
