"""
多智能体协作流水线

支持以下启动模式：
1. 全自动模式：问题提出 → 数据分析 → 评分（默认）
2. 手动问题模式：数据分析 → 评分（跳过问题提出，使用用户指定的问题）
3. 仅问题提出：只运行问题提出智能体
4. 仅评分：对已有会话进行评分
5. 交互模式：可多次输入问题

使用方式:
    # 全自动流水线
    python -m services.agents.deepagents.multi_agent_pipeline

    # 指定输出目录
    python -m services.agents.deepagents.multi_agent_pipeline -o ./reports

    # 手动输入问题，跳过问题提出智能体
    python -m services.agents.deepagents.multi_agent_pipeline --question "分析近三个月销售趋势"

    # 只运行问题提出智能体
    python -m services.agents.deepagents.multi_agent_pipeline --only-propose

    # 只运行评分智能体
    python -m services.agents.deepagents.multi_agent_pipeline --only-score --session <session_id>

    # 交互模式
    python -m services.agents.deepagents.multi_agent_pipeline --interactive
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 确保 backend 在 Python 路径中
backend_root = Path(__file__).parent.parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


def run_full_pipeline(
    output_dir: str = "./analysis_output",
    context: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """运行完整的多智能体流水线

    流程：问题提出 → 数据分析 → 评分

    Args:
        output_dir: 输出目录
        context: 业务上下文
        verbose: 详细输出

    Returns:
        流水线执行结果
    """
    from services.agents.deepagents.question_proposer_agent import QuestionProposerAgent
    from services.agents.deepagents.data_analyser_agent import DataAnalyserAgent
    from services.agents.deepagents.scorer_agent import ScorerAgent
    from models import SessionLocal
    from repositories.deepagents import AnalysisSessionRepository
    from utils.logger import logger

    result = {
        "success": False,
        "stages": {},
        "start_time": datetime.now().isoformat(),
    }

    print()
    print("=" * 70)
    print("淘沙分析平台 - 多智能体协作流水线")
    print("=" * 70)
    print()

    # 阶段1：问题提出
    print("[阶段 1/3] 问题提出智能体")
    print("-" * 50)

    try:
        proposer = QuestionProposerAgent()
        propose_result = proposer.propose_topics(context)

        if not propose_result.get("success"):
            print(f"问题提出失败: {propose_result.get('error')}")
            result["stages"]["propose"] = propose_result
            return result

        # 获取推荐问题
        topics = propose_result.get("topics", [])
        recommended_id = propose_result.get("recommended_topic_id")

        question = None
        for topic in topics:
            if topic.get("id") == recommended_id or topic.get("is_recommended"):
                question = f"{topic.get('title', '')}。{topic.get('description', '')}"
                break

        if not question and topics:
            topic = topics[0]
            question = f"{topic.get('title', '')}。{topic.get('description', '')}"

        if not question:
            print("未能生成分析问题")
            result["stages"]["propose"] = propose_result
            return result

        print(f"推荐分析问题: {question[:100]}...")
        print(f"推荐理由: {propose_result.get('recommendation_reason', 'N/A')}")
        print()

        if verbose:
            print("所有候选主题：")
            for t in topics:
                marker = "★" if t.get("is_recommended") else " "
                print(f"  {marker} {t.get('id')}. {t.get('title')} [{t.get('priority', 'N/A')}]")
            print()

        result["stages"]["propose"] = {
            "success": True,
            "question": question,
            "topics_count": len(topics),
        }

    except Exception as e:
        logger.error(f"问题提出阶段失败: {e}")
        print(f"问题提出阶段出错: {e}")
        result["stages"]["propose"] = {"success": False, "error": str(e)}
        return result

    # 阶段2：数据分析
    print("[阶段 2/3] 数据分析智能体")
    print("-" * 50)

    try:
        analyser = DataAnalyserAgent(output_base_dir=output_dir)
        analyser.create_agent()
        analyse_result = analyser.run_analysis(question)

        session_id = analyse_result.get("session_id")
        print(f"会话ID: {session_id}")
        print(f"耗时: {analyse_result.get('duration_seconds', 0):.1f} 秒")

        if analyse_result.get("success"):
            print(f"输出目录: {analyse_result.get('output_dir')}")
            if analyse_result.get("report_exists"):
                print(f"报告文件: {analyse_result.get('report_path')}")

            # 保存会话到数据库
            _save_session_to_db(
                session_id=session_id,
                question=question,
                question_source="proposer",
                result=analyse_result,
                llm_output=analyser.llm_output
            )
        else:
            print(f"分析失败: {analyse_result.get('error')}")

        print()
        result["stages"]["analyse"] = {
            "success": analyse_result.get("success"),
            "session_id": session_id,
            "duration_seconds": analyse_result.get("duration_seconds"),
        }

    except Exception as e:
        logger.error(f"数据分析阶段失败: {e}")
        print(f"数据分析阶段出错: {e}")
        result["stages"]["analyse"] = {"success": False, "error": str(e)}
        return result

    # 阶段3：评分
    print("[阶段 3/3] 评分智能体")
    print("-" * 50)

    try:
        scorer = ScorerAgent()
        score_result = scorer.evaluate_and_save(session_id)

        if score_result.get("success"):
            print(f"过程评分: {score_result.get('process_score', {}).get('score', 0)}")
            print(f"报告评分: {score_result.get('report_score', {}).get('score', 0)}")
            print(f"结论评分: {score_result.get('conclusion_score', {}).get('score', 0)}")
            print(f"综合评分: {score_result.get('overall_score', 0)}")

            suggestions = score_result.get("improvement_suggestions", [])
            if suggestions:
                print("\n改进建议：")
                for s in suggestions[:3]:
                    print(f"  - [{s.get('priority', 'N/A')}] {s.get('suggestion', '')}")
        else:
            print(f"评分失败: {score_result.get('error')}")

        print()
        result["stages"]["score"] = {
            "success": score_result.get("success"),
            "overall_score": score_result.get("overall_score"),
        }

    except Exception as e:
        logger.error(f"评分阶段失败: {e}")
        print(f"评分阶段出错: {e}")
        result["stages"]["score"] = {"success": False, "error": str(e)}

    # 完成
    result["success"] = all(
        stage.get("success")
        for stage in result["stages"].values()
    )
    result["end_time"] = datetime.now().isoformat()
    result["session_id"] = session_id

    print("=" * 70)
    if result["success"]:
        print("流水线执行完成！")
    else:
        print("流水线执行部分失败，请检查日志。")
    print("=" * 70)
    print()

    return result


def run_with_question(
    question: str,
    output_dir: str = "./analysis_output",
    verbose: bool = False
) -> Dict[str, Any]:
    """使用指定问题运行分析和评分

    流程：数据分析 → 评分（跳过问题提出）

    Args:
        question: 分析问题
        output_dir: 输出目录
        verbose: 详细输出

    Returns:
        执行结果
    """
    from services.agents.deepagents.data_analyser_agent import DataAnalyserAgent
    from services.agents.deepagents.scorer_agent import ScorerAgent
    from utils.logger import logger

    result = {
        "success": False,
        "stages": {},
        "start_time": datetime.now().isoformat(),
    }

    print()
    print("=" * 70)
    print("淘沙分析平台 - 数据分析流水线（手动问题模式）")
    print("=" * 70)
    print(f"分析问题: {question}")
    print()

    # 阶段1：数据分析
    print("[阶段 1/2] 数据分析智能体")
    print("-" * 50)

    try:
        analyser = DataAnalyserAgent(output_base_dir=output_dir)
        analyser.create_agent()
        analyse_result = analyser.run_analysis(question)

        session_id = analyse_result.get("session_id")
        print(f"会话ID: {session_id}")
        print(f"耗时: {analyse_result.get('duration_seconds', 0):.1f} 秒")

        if analyse_result.get("success"):
            print(f"输出目录: {analyse_result.get('output_dir')}")
            if analyse_result.get("report_exists"):
                print(f"报告文件: {analyse_result.get('report_path')}")

            # 保存会话到数据库
            _save_session_to_db(
                session_id=session_id,
                question=question,
                question_source="manual",
                result=analyse_result,
                llm_output=analyser.llm_output
            )
        else:
            print(f"分析失败: {analyse_result.get('error')}")

        print()
        result["stages"]["analyse"] = {
            "success": analyse_result.get("success"),
            "session_id": session_id,
            "duration_seconds": analyse_result.get("duration_seconds"),
        }

    except Exception as e:
        logger.error(f"数据分析阶段失败: {e}")
        print(f"数据分析阶段出错: {e}")
        result["stages"]["analyse"] = {"success": False, "error": str(e)}
        return result

    # 阶段2：评分
    print("[阶段 2/2] 评分智能体")
    print("-" * 50)

    try:
        scorer = ScorerAgent()
        score_result = scorer.evaluate_and_save(session_id)

        if score_result.get("success"):
            print(f"过程评分: {score_result.get('process_score', {}).get('score', 0)}")
            print(f"报告评分: {score_result.get('report_score', {}).get('score', 0)}")
            print(f"结论评分: {score_result.get('conclusion_score', {}).get('score', 0)}")
            print(f"综合评分: {score_result.get('overall_score', 0)}")
        else:
            print(f"评分失败: {score_result.get('error')}")

        print()
        result["stages"]["score"] = {
            "success": score_result.get("success"),
            "overall_score": score_result.get("overall_score"),
        }

    except Exception as e:
        logger.error(f"评分阶段失败: {e}")
        print(f"评分阶段出错: {e}")
        result["stages"]["score"] = {"success": False, "error": str(e)}

    result["success"] = all(
        stage.get("success")
        for stage in result["stages"].values()
    )
    result["end_time"] = datetime.now().isoformat()
    result["session_id"] = session_id

    print("=" * 70)
    print("执行完成！")
    print("=" * 70)
    print()

    return result


def run_only_propose(context: Optional[str] = None) -> Dict[str, Any]:
    """仅运行问题提出智能体

    Args:
        context: 业务上下文

    Returns:
        执行结果
    """
    from services.agents.deepagents.question_proposer_agent import QuestionProposerAgent

    print()
    print("=" * 70)
    print("淘沙分析平台 - 问题提出智能体")
    print("=" * 70)
    print()

    proposer = QuestionProposerAgent()
    result = proposer.propose_topics(context)

    if result.get("success"):
        topics = result.get("topics", [])
        print(f"生成了 {len(topics)} 个分析主题：\n")

        for topic in topics:
            marker = "★ [推荐]" if topic.get("is_recommended") else ""
            print(f"{topic.get('id')}. {topic.get('title')} {marker}")
            print(f"   描述: {topic.get('description', 'N/A')}")
            print(f"   优先级: {topic.get('priority', 'N/A')}")
            print()

        print(f"推荐理由: {result.get('recommendation_reason', 'N/A')}")
    else:
        print(f"问题提出失败: {result.get('error')}")

    print()
    print("=" * 70)
    print()

    return result


def run_only_score(session_id: str) -> Dict[str, Any]:
    """仅运行评分智能体

    Args:
        session_id: 分析会话ID

    Returns:
        执行结果
    """
    from services.agents.deepagents.scorer_agent import ScorerAgent

    print()
    print("=" * 70)
    print("淘沙分析平台 - 评分智能体")
    print("=" * 70)
    print(f"评估会话: {session_id}")
    print()

    scorer = ScorerAgent()
    result = scorer.evaluate_and_save(session_id)

    if result.get("success"):
        print("评分结果：")
        print("-" * 50)

        process = result.get("process_score", {})
        print(f"\n分析过程评分: {process.get('score', 0)}")
        if process.get("reasons"):
            print("  优点:")
            for r in process.get("reasons", []):
                print(f"    + {r}")
        if process.get("deductions"):
            print("  扣分项:")
            for d in process.get("deductions", []):
                print(f"    - {d}")

        report = result.get("report_score", {})
        print(f"\n分析报告评分: {report.get('score', 0)}")
        if report.get("reasons"):
            print("  优点:")
            for r in report.get("reasons", []):
                print(f"    + {r}")
        if report.get("deductions"):
            print("  扣分项:")
            for d in report.get("deductions", []):
                print(f"    - {d}")

        conclusion = result.get("conclusion_score", {})
        print(f"\n分析结论评分: {conclusion.get('score', 0)}")
        if conclusion.get("reasons"):
            print("  优点:")
            for r in conclusion.get("reasons", []):
                print(f"    + {r}")
        if conclusion.get("deductions"):
            print("  扣分项:")
            for d in conclusion.get("deductions", []):
                print(f"    - {d}")

        print(f"\n综合评分: {result.get('overall_score', 0)}")

        suggestions = result.get("improvement_suggestions", [])
        if suggestions:
            print("\n改进建议：")
            for s in suggestions:
                print(f"  [{s.get('category', 'other')}][{s.get('priority', 'N/A')}] {s.get('suggestion', '')}")
    else:
        print(f"评分失败: {result.get('error')}")

    print()
    print("=" * 70)
    print()

    return result


def run_interactive(output_dir: str = "./analysis_output"):
    """交互模式

    Args:
        output_dir: 输出目录
    """
    print()
    print("=" * 70)
    print("淘沙分析平台 - 多智能体交互模式")
    print("=" * 70)
    print()
    print("命令:")
    print("  输入问题开始分析（自动评分）")
    print("  输入 'propose' 运行问题提出智能体")
    print("  输入 'score <session_id>' 对指定会话评分")
    print("  输入 'auto' 运行全自动流水线")
    print("  输入 'exit' 或 'quit' 退出")
    print("=" * 70)
    print()

    while True:
        try:
            user_input = input("请输入> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n再见！")
                break

            if user_input.lower() == 'propose':
                run_only_propose()
                continue

            if user_input.lower().startswith('score '):
                session_id = user_input[6:].strip()
                if session_id:
                    run_only_score(session_id)
                else:
                    print("请提供会话ID")
                continue

            if user_input.lower() == 'auto':
                run_full_pipeline(output_dir=output_dir)
                continue

            if user_input.lower() in ['help', '?']:
                print("\n命令帮助:")
                print("  <问题>           - 输入分析问题开始分析")
                print("  propose          - 运行问题提出智能体")
                print("  score <id>       - 对指定会话评分")
                print("  auto             - 运行全自动流水线")
                print("  exit/quit/q      - 退出程序")
                print()
                continue

            # 作为分析问题处理
            run_with_question(user_input, output_dir=output_dir)

        except KeyboardInterrupt:
            print("\n\n已中断，输入 'exit' 退出")
            continue
        except EOFError:
            break


def _save_session_to_db(
    session_id: str,
    question: str,
    question_source: str,
    result: Dict[str, Any],
    llm_output: Optional[str] = None
):
    """保存会话到数据库"""
    try:
        from models import SessionLocal
        from models.deepagents import AnalysisSession
        from datetime import datetime

        db = SessionLocal()
        try:
            session = AnalysisSession(
                session_id=session_id,
                question=question,
                question_source=question_source,
                status="completed" if result.get("success") else "failed",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_seconds=result.get("duration_seconds"),
                report_path=result.get("report_path"),
                report_content=result.get("report_content"),
                llm_output=llm_output,
            )
            db.add(session)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        from utils.logger import logger
        logger.error(f"保存会话到数据库失败: {e}")


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="python -m services.agents.deepagents.multi_agent_pipeline",
        description="淘沙分析平台 - 多智能体协作流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全自动流水线
  python -m services.agents.deepagents.multi_agent_pipeline

  # 手动指定问题
  python -m services.agents.deepagents.multi_agent_pipeline -q "分析销售趋势"

  # 只运行问题提出
  python -m services.agents.deepagents.multi_agent_pipeline --only-propose

  # 只运行评分
  python -m services.agents.deepagents.multi_agent_pipeline --only-score -s <session_id>

  # 交互模式
  python -m services.agents.deepagents.multi_agent_pipeline -i
        """
    )

    parser.add_argument(
        "-o", "--output",
        default="./analysis_output",
        help="输出目录 (默认: ./analysis_output)"
    )

    parser.add_argument(
        "-q", "--question",
        help="手动指定分析问题（跳过问题提出智能体）"
    )

    parser.add_argument(
        "--only-propose",
        action="store_true",
        help="只运行问题提出智能体"
    )

    parser.add_argument(
        "--only-score",
        action="store_true",
        help="只运行评分智能体"
    )

    parser.add_argument(
        "-s", "--session",
        help="指定会话ID（用于单独评分）"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式"
    )

    parser.add_argument(
        "--context",
        help="业务上下文（可选）"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # 根据参数选择运行模式
    if args.only_propose:
        run_only_propose(context=args.context)

    elif args.only_score:
        if not args.session:
            print("错误: --only-score 需要指定 --session 参数")
            sys.exit(1)
        run_only_score(args.session)

    elif args.interactive:
        run_interactive(output_dir=args.output)

    elif args.question:
        run_with_question(
            question=args.question,
            output_dir=args.output,
            verbose=args.verbose
        )

    else:
        # 默认：全自动流水线
        run_full_pipeline(
            output_dir=args.output,
            context=args.context,
            verbose=args.verbose
        )


if __name__ == "__main__":
    main()
