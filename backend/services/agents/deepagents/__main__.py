"""
DeepAgents CLI 入口

使用方式:
    python -m backend.services.agents.deepagents "分析近三个月的销售趋势"
    python -m backend.services.agents.deepagents -o ./reports "用户活跃度分析"
    python -m backend.services.agents.deepagents --interactive
    python -m backend.services.agents.deepagents --engine duckdb "数据质量检查"
"""

import sys
import argparse
from pathlib import Path

# 确保 backend 在 Python 路径中
backend_root = Path(__file__).parent.parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="python -m backend.services.agents.deepagents",
        description="淘沙分析平台 - DeepAgents 数据分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m backend.services.agents.deepagents "分析近三个月的销售趋势"
  python -m backend.services.agents.deepagents -o ./reports "用户活跃度分析"
  python -m backend.services.agents.deepagents --interactive
  python -m backend.services.agents.deepagents --session abc123 "继续上次的分析"
        """
    )

    parser.add_argument(
        "question",
        nargs="?",
        help="数据分析问题"
    )

    parser.add_argument(
        "-o", "--output",
        default="./analysis_output",
        help="输出目录 (默认: ./analysis_output)"
    )

    parser.add_argument(
        "-s", "--session",
        default=None,
        help="会话ID，用于继续之前的分析或文件隔离"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式，可以连续输入多个问题"
    )

    parser.add_argument(
        "--engine",
        choices=["duckdb", "spark", "empty"],
        default=None,
        help="查询引擎类型 (默认: 使用配置文件中的设置)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )

    parser.add_argument(
        "--list-files",
        action="store_true",
        help="列出指定会话的所有文件"
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # 导入服务（延迟导入，避免启动时间过长）
    from services.agents.deep_analyse_agent_service import DeepAnalyseAgentService
    from utils.logger import logger

    # 创建服务实例
    service = DeepAnalyseAgentService(
        session_id=args.session,
        output_base_dir=args.output
    )

    # 如果只是列出文件
    if args.list_files:
        if not args.session:
            print("错误: 列出文件需要指定 --session 参数")
            sys.exit(1)
        files = service.get_session_files()
        if files:
            print(f"\n会话 {service.session_id} 的文件列表:")
            print("-" * 60)
            for f in files:
                print(f"  {f['path']:<40} {f['size']:>10} bytes")
            print("-" * 60)
        else:
            print(f"会话 {service.session_id} 没有文件")
        return

    # 交互模式
    if args.interactive:
        run_interactive(service)
    elif args.question:
        run_single_analysis(service, args.question)
    else:
        parser.print_help()
        sys.exit(1)


def run_single_analysis(service, question: str):
    """运行单次分析"""
    print()
    print("=" * 60)
    print("淘沙分析平台 - DeepAgents 数据分析")
    print("=" * 60)
    print(f"会话ID: {service.session_id}")
    print(f"问题: {question}")
    print("-" * 60)
    print()

    try:
        # 创建 Agent 并运行分析
        service.create_agent()
        result = service.run_analysis(question)

        print()
        print("-" * 60)

        if result["success"]:
            print(f"分析完成！耗时: {result['duration_seconds']:.2f} 秒")
            print(f"输出目录: {result['output_dir']}")

            if result["report_exists"]:
                print(f"报告文件: {result['report_path']}")
            else:
                print("提示: 未生成 report.html 文件")

            # 列出生成的文件
            files = service.get_session_files()
            if files:
                print()
                print("生成的文件:")
                for f in files:
                    print(f"  - {f['path']}")
        else:
            print(f"分析失败: {result.get('error', '未知错误')}")

        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n\n已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


def run_interactive(service):
    """交互模式"""
    print()
    print("=" * 60)
    print("淘沙分析平台 - DeepAgents 交互模式")
    print("=" * 60)
    print(f"会话ID: {service.session_id}")
    print(f"输出目录: {service.output_dir}")
    print()
    print("命令:")
    print("  输入分析问题开始分析")
    print("  输入 'files' 查看生成的文件")
    print("  输入 'read <文件路径>' 查看文件内容")
    print("  输入 'exit' 或 'quit' 退出")
    print("=" * 60)
    print()

    # 创建 Agent
    service.create_agent()

    while True:
        try:
            user_input = input("请输入分析问题> ").strip()

            if not user_input:
                continue

            # 退出命令
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n再见！")
                break

            # 列出文件
            if user_input.lower() == 'files':
                files = service.get_session_files()
                if files:
                    print("\n生成的文件:")
                    for f in files:
                        print(f"  {f['path']:<40} {f['size']:>10} bytes")
                    print()
                else:
                    print("\n暂无文件\n")
                continue

            # 读取文件
            if user_input.lower().startswith('read '):
                file_path = user_input[5:].strip()
                content = service.read_file(file_path)
                if content:
                    print(f"\n--- {file_path} ---")
                    print(content)
                    print(f"--- END ---\n")
                else:
                    print(f"\n文件不存在或无法读取: {file_path}\n")
                continue

            # 帮助
            if user_input.lower() in ['help', '?']:
                print("\n命令帮助:")
                print("  <问题>        - 输入分析问题开始分析")
                print("  files         - 列出所有生成的文件")
                print("  read <路径>   - 查看指定文件内容")
                print("  exit/quit/q   - 退出程序")
                print()
                continue

            # 执行分析
            print()
            print("-" * 40)
            print("开始分析...")
            print("-" * 40)
            print()

            result = service.run_analysis(user_input)

            print()
            if result["success"]:
                print(f"分析完成！耗时: {result['duration_seconds']:.2f} 秒")
                if result["report_exists"]:
                    print(f"报告: {result['report_path']}")
            else:
                print(f"分析失败: {result.get('error', '未知错误')}")
            print()

        except KeyboardInterrupt:
            print("\n\n已中断，输入 'exit' 退出")
            continue
        except EOFError:
            break

    # 清理资源
    service.cleanup()


if __name__ == "__main__":
    main()
