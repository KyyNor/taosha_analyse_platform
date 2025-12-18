# 代码执行工具安全特性说明

## 概述

本文档说明 `code_execution_tool.py` 的安全特性和使用方法。

## 问题背景

### 原始版本的两个主要问题

1. **FastAPI异步环境下signal不可用**
   - 原代码使用 `signal.SIGALRM` 实现超时控制
   - 在FastAPI的异步环境和多worker模式下无法正常工作
   - 需要异步兼容的超时方案

2. **缺少安全审计机制**
   - 代码可以执行任意系统命令（如 `os.system`, `subprocess`）
   - 可以访问任意文件（如 `/etc/passwd`）
   - 可以进行网络操作
   - 可以使用危险的序列化库（`pickle`）

## 解决方案

### 1. 异步超时控制

**实现方式**：
```python
# 使用 asyncio.wait_for() + asyncio.to_thread() 替代signal
result = await asyncio.wait_for(
    asyncio.to_thread(_execute),
    timeout=timeout
)
```

**优势**：
- ✅ 与FastAPI异步环境完全兼容
- ✅ 支持多worker进程
- ✅ 跨平台支持（不依赖Unix信号）
- ✅ 精确的超时控制

**注意事项**：
- 超时机制对某些阻塞操作（如 `time.sleep`）可能延迟触发
- 建议设置合理的超时值（默认30秒）

### 2. 多层安全防护

#### 2.1 代码静态审计

**审计规则**：
- ❌ 系统命令：`os.system`, `subprocess`
- ❌ 动态执行：`eval`, `exec`
- ❌ 网络操作：`socket`, `urllib`, `requests`, `http.client`
- ❌ 文件操作：`open()` (必须使用 `safe_open()`)
- ❌ 危险库：`pickle`, `marshal`, `shelve`, `ctypes`
- ❌ 程序控制：`sys.exit`, `quit()`, `exit()`
- ❌ 反射访问：直接访问 `__builtins__`, `__globals__`

**实现方式**：
```python
def audit_code(code: str) -> tuple[bool, Optional[str]]:
    """使用正则表达式检测危险模式"""
    dangerous_patterns = [
        (r'\bos\.system\b', '不允许执行系统命令'),
        (r'\bsubprocess\b', '不允许创建子进程'),
        # ... 更多规则
    ]
```

#### 2.2 受限的内置函数

**移除的危险函数**：
- `eval`, `exec`: 动态代码执行
- `open`: 文件操作（提供安全版本）
- `input`, `raw_input`: 用户输入
- `exit`, `quit`: 程序退出
- `compile`: 代码编译

**保留的函数**：
- 所有基本内置函数：`sum`, `len`, `range`, `print` 等
- `__import__`: 保留以支持 import 语句（但通过审计控制）
- 类型和容器：`dict`, `list`, `tuple`, `set`, `str`, `int`, `float` 等

#### 2.3 安全的文件访问

**工作目录限制**：
```python
ALLOWED_WORK_DIR = Path("/tmp/taosha_code_execution")
```

**safe_open 函数**：
```python
def create_safe_open(allowed_dir: Path):
    """只允许访问指定目录下的文件"""
    def safe_open(file, mode='r', *args, **kwargs):
        # 1. 解析并验证路径
        file_path = Path(file).resolve()
        # 2. 检查是否在允许的目录内
        file_path.relative_to(allowed_dir)  # 会抛出ValueError
        # 3. 检查文件模式安全性
        # 4. 调用真正的open
        return open(file_path, mode, *args, **kwargs)
    return safe_open
```

**特点**：
- ✅ 路径穿越保护（`..` 等）
- ✅ 绝对路径检查
- ✅ 文件模式限制
- ✅ 符号链接解析

#### 2.4 预加载的安全库

**可用库**：
```python
- pandas (pd)      # 数据处理
- numpy (np)       # 数值计算
- datetime         # 日期时间
- math             # 数学函数
- statistics       # 统计函数
- re               # 正则表达式
- collections      # 集合类型
- itertools        # 迭代工具
- json             # JSON处理
```

**特点**：
- 预导入，无需用户显式import
- 命名空间隔离
- 仅包含数据处理相关的安全库

## 使用方法

### 基本使用

```python
from code_execution_tool import execute_code

# 简单计算
result = execute_code("""
result = sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
""")
# 返回: {"success": true, "result": 15, "stdout": "Sum: 15\n"}

# 数据处理
result = execute_code("""
data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
result = {"count": len(data), "names": [d["name"] for d in data]}
""")
```

### 启用文件访问

```python
# 写入文件
result = execute_code("""
with safe_open(f"{WORK_DIR}/data.txt", "w") as f:
    f.write("Hello, World!")
result = "文件写入成功"
""", enable_file_access=True)

# 读取文件
result = execute_code("""
with safe_open(f"{WORK_DIR}/data.txt", "r") as f:
    content = f.read()
result = f"内容: {content}"
""", enable_file_access=True)
```

**注意**：
- 必须设置 `enable_file_access=True`
- 必须使用 `safe_open()` 而不是 `open()`
- 文件路径必须在 `WORK_DIR` 目录内
- `WORK_DIR` 变量在代码中自动可用

### 异步使用（FastAPI环境）

```python
from code_execution_tool import execute_code_tool_async

@app.post("/execute")
async def execute_endpoint(code: str):
    result = await execute_code_tool_async(
        code=code,
        timeout=30,
        enable_file_access=False
    )
    return JSONResponse(json.loads(result))
```

### 自定义超时

```python
# 短超时（10秒）
result = execute_code(code, timeout=10)

# 长超时（60秒）
result = execute_code(code, timeout=60)
```

## 安全测试

### 运行测试

```bash
# 完整测试套件
python backend/services/agents/tools/test_code_execution_security.py

# 简化测试
python test_code_execution_simple.py

# 功能测试
python test_safe_features.py
```

### 测试覆盖

1. **正常执行**：基本计算、数据处理、库使用
2. **安全违规检测**：所有危险操作被拦截
3. **文件访问控制**：路径限制、权限检查
4. **超时控制**：长时间运行代码被终止
5. **异步执行**：FastAPI异步兼容性

## 安全级别对比

### ⚠️ 原始版本
- ❌ 无安全审计
- ❌ 可执行系统命令
- ❌ 可访问任意文件
- ❌ 可进行网络操作
- ⚠️ 超时机制不可靠

### ✅ 安全版本
- ✅ 多层安全审计
- ✅ 禁止系统命令
- ✅ 文件访问受限
- ✅ 禁止网络操作
- ✅ 可靠的超时控制
- ✅ FastAPI异步兼容

## 已知限制

### 1. 超时精度
- 某些阻塞操作（如 `time.sleep`）可能延迟触发超时
- 建议设置合理的超时值并做好错误处理

### 2. 审计绕过
- 审计基于静态代码分析（正则表达式）
- 理论上存在混淆绕过的可能性
- 建议配合其他安全措施（容器隔离、资源限制等）

### 3. 性能开销
- 每次执行都会创建新的命名空间
- 每次都会进行代码审计
- 对于大量短时执行可能有性能影响

## 最佳实践

### 1. 使用场景
✅ **适合**：
- 数据分析和处理
- 简单的计算任务
- 报表生成
- AI Agent 工具调用

❌ **不适合**：
- 长时间运行的任务
- 需要系统交互的任务
- 需要网络访问的任务
- 需要访问数据库的任务

### 2. 配置建议

```python
# 开发环境：宽松超时
execute_code(code, timeout=60, enable_file_access=True)

# 生产环境：严格限制
execute_code(code, timeout=30, enable_file_access=False)

# AI Agent：中等限制
execute_code(code, timeout=45, enable_file_access=True)
```

### 3. 错误处理

```python
import json

result_json = execute_code(code)
result = json.loads(result_json)

if not result["success"]:
    error_msg = result["error"]
    if "安全审计失败" in error_msg:
        # 处理安全违规
        logger.warning(f"安全违规: {error_msg}")
    elif "超时" in error_msg:
        # 处理超时
        logger.error(f"执行超时: {error_msg}")
    else:
        # 处理其他错误
        logger.error(f"执行失败: {error_msg}")
        if "traceback" in result:
            logger.error(result["traceback"])
```

### 4. 容器化部署

虽然已有多层安全防护，但建议在生产环境中：
- 使用 Docker 容器隔离
- 限制容器资源（CPU、内存）
- 使用只读文件系统
- 禁用网络访问
- 使用非root用户运行

## 未来改进方向

### 短期
- [ ] 增加更多审计规则
- [ ] 优化超时机制（支持CPU时间限制）
- [ ] 添加内存使用限制
- [ ] 支持自定义工作目录

### 中期
- [ ] 集成 RestrictedPython 库
- [ ] 添加代码复杂度分析
- [ ] 支持资源配额管理
- [ ] 添加审计日志和统计

### 长期
- [ ] 使用独立的沙箱进程
- [ ] 支持分布式执行
- [ ] 集成商业沙箱方案
- [ ] 支持自定义安全策略

## 参考资料

- [PEP 578 – Python Runtime Audit Hooks](https://peps.python.org/pep-0578/)
- [RestrictedPython Documentation](https://restrictedpython.readthedocs.io/)
- [OWASP Code Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

## 联系方式

如有安全问题或改进建议，请联系开发团队。

---

**最后更新**: 2025-12-19
**版本**: 2.0.0 (安全增强版)
