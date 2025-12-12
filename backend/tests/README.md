# 测试说明

## 运行测试

### 方法1：使用测试脚本
```bash
cd backend
python run_tests.py
```

### 方法2：直接使用pytest
```bash
cd backend
python -m pytest tests/fraudhunter/test_model_hit_alert_manager.py -v
```

### 方法3：使用uv运行
```bash
cd backend
uv run pytest tests/fraudhunter/test_model_hit_alert_manager.py -v
```

## 测试内容

### 模型命中与告警管理器属性测试

- **属性1：命中记录创建完整性** - 验证创建的命中记录包含所有必需字段
- **属性2：多模型命中存储一致性** - 验证多个模型命中时数据存储的一致性
- **属性3：重复命中记录独立性** - 验证重复命中时创建独立记录

每个属性测试使用Hypothesis库运行100次随机测试用例，确保代码在各种输入下的正确性。

## 测试依赖

- pytest: 测试框架
- hypothesis: 属性基础测试库
- sqlalchemy: 数据库ORM（内存SQLite用于测试）