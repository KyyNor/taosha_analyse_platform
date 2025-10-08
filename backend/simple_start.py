"""
临时简化的后端启动文件
仅用于测试基础功能
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="淘沙分析平台 API",
    description="基于自然语言的企业数据分析平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "code": 0,
        "message": "淘沙分析平台 API 服务运行正常",
        "data": {
            "version": "1.0.0",
            "docs_url": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

@app.get("/api/taosha/v1/ping")
async def ping():
    """Ping接口"""
    return {
        "code": 0,
        "message": "pong",
        "data": {
            "status": "healthy",
            "version": "1.0.0"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "simple_start:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )