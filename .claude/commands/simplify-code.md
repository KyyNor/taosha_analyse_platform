# 简化代码

使用 code-simplifier 简化代码。如果有未提交的文件，则简化这些文件；如果没有未提交的文件，则简化最后一次提交的代码。

## 执行步骤

### 1. 检查是否有未提交的文件

获取未提交的文件列表（排除已删除的文件）：

```bash
git status --porcelain | grep -vE "^.D|AD" | awk '{print $2}'
```

### 2. 根据情况决定简化哪些文件

**情况A：有未提交的文件**
- 获取所有未提交的文件（排除已删除的）
- 过滤出代码文件（.java, .py, .js, .ts, .go, .rs, .c, .cpp等）
- 使用 code-simplifier 处理这些文件

**情况B：没有未提交的文件**
- 获取最后一次提交的文件列表：
  ```bash
  git diff-tree --no-commit-id --name-only -r HEAD
  ```
- 过滤出代码文件
- 使用 code-simplifier 处理这些文件

### 3. 过滤代码文件

只处理代码文件，支持的扩展名：
- Java: `.java`
- Python: `.py`
- JavaScript/TypeScript: `.js`, `.ts`, `.tsx`, `.jsx`
- Go: `.go`
- Rust: `.rs`
- C/C++: `.c`, `.cpp`, `.h`, `.hpp`

跳过：`.md`, `.txt`, `.json`, `.yaml`, `.xml` 等配置和文档文件

### 4. 并行处理

- **3个或更多文件**：使用多个 Task 工具调用并行处理所有文件
- **1-2个文件**：顺序处理

**Code-simplifier 调用参数：**
```
subagent_type: code-simplifier:code-simplifier
prompt: Simplify and refine this file for clarity, consistency, and maintainability while preserving all functionality. Focus on recently modified code unless instructed otherwise.
model: haiku  (用于更快的处理速度)
```

### 5. 报告结果

处理完成后提供摘要：
- 处理的文件数量
- 简化的文件列表
- 遇到的任何错误

## 使用场景

- **提交前清理**：在提交代码前使用此命令清理和简化修改的文件
- **代码重构**：简化最后一次提交的代码以提高可读性和可维护性
- **批量优化**：快速优化多个文件以保持代码风格一致

## 示例

**用户说：**
- "简化我的代码"
- "simplify-code"
- "清理代码"
- "优化代码结构"

**预期输出：**
```
检测到 1 个未提交的文件：
- src/main/java/com/kyynor/flowminer/StreamingJob.java

正在使用 code-simplifier 处理文件...

✅ 成功简化 1 个文件
```
