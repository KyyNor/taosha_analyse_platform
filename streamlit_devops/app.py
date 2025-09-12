"""
淘沙分析平台 - Streamlit前端应用
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import json
import time

# 页面配置
st.set_page_config(
    page_title="淘沙分析平台",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 后端API配置
API_BASE_URL = "http://localhost:8000/api/v1"

class TaoshaAPIClient:
    """后端API客户端"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def query(self, query_text: str, max_retries: int = 2) -> Dict[str, Any]:
        """发送自然语言查询"""
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json={"query": query_text, "max_retries": max_retries},
                timeout=240
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """获取表信息"""
        try:
            response = requests.get(f"{self.base_url}/tables", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"获取表信息失败: {str(e)}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"获取系统状态失败: {str(e)}"}
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# 初始化API客户端
@st.cache_resource
def get_api_client():
    return TaoshaAPIClient()

def create_chart(data: List[Dict], chart_type: str = "auto"):
    """根据数据创建图表"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    # 如果只有一行数据，显示为指标卡片
    if len(df) == 1:
        return None
    
    # 自动判断图表类型
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        # 柱状图
        x_col = categorical_cols[0]
        y_col = numeric_cols[0]
        
        fig = px.bar(
            df, 
            x=x_col, 
            y=y_col,
            title=f"{y_col} 按 {x_col} 分布",
            labels={x_col: x_col, y_col: y_col}
        )
        
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            showlegend=False
        )
        
        return fig
    
    elif len(numeric_cols) >= 2:
        # 散点图
        fig = px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            title=f"{numeric_cols[1]} vs {numeric_cols[0]}"
        )
        return fig
    
    return None

def display_input_clarity_result(clear_check_details):
    """显示输入清晰度验证结果"""
    if not clear_check_details:
        return False
    
    # 处理结构化数据或字符串格式
    is_clear = clear_check_details.get('is_clear', True)
    reason = clear_check_details.get('reason', '')
    suggestions = clear_check_details.get('suggestions', [])
    
    if not is_clear:
        st.warning("🤔 您的问题可能不够清晰")
        
        if reason:
            st.info(f"**原因**: {reason}")
        
        if suggestions:
            st.markdown("### 💡 改进建议")
            st.markdown("请选择以下建议之一来完善您的查询：")
            
            # 创建建议选择按钮
            col_count = min(len(suggestions), 2)  # 最多2列
            cols = st.columns(col_count)
            
            for i, suggestion in enumerate(suggestions):
                with cols[i % col_count]:
                    if st.button(
                        suggestion, 
                        key=f"suggestion_{i}", 
                        use_container_width=True,
                        help="点击将此建议作为新查询"
                    ):
                        # 将建议设置为新的查询输入
                        st.session_state.query_input = suggestion
                        st.rerun()
            
            # 也提供复制建议的功能
            with st.expander("📋 复制建议内容"):
                for i, suggestion in enumerate(suggestions, 1):
                    st.code(f"{i}. {suggestion}", language="text")
        
        return True  # 表示显示了清晰度问题
    
    return False  # 输入清晰，没有显示额外内容

def display_query_logs(logs: List[Dict]):
    """显示查询日志"""
    if not logs:
        return
    
    with st.expander("🔍 查询执行日志", expanded=False):
        for i, log in enumerate(logs):
            step = log.get('step', 'unknown')
            success = log.get('success', False)
            timestamp = log.get('timestamp', '')
            
            # 状态图标
            status_icon = "✅" if success else "❌"
            
            st.write(f"**{i+1}. {step}** {status_icon}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if log.get('input_data'):
                    st.text_area(
                        "输入数据",
                        value=log['input_data'],
                        height=100,
                        key=f"input_{i}",
                        disabled=True
                    )
            
            with col2:
                if log.get('model_output'):
                    st.text_area(
                        "模型输出",
                        value=log['model_output'],
                        height=100,
                        key=f"output_{i}",
                        disabled=True
                    )
            
            if log.get('error'):
                st.error(f"错误: {log['error']}")
            
            if log.get('prompt'):
                with st.expander(f"查看提示词 - {step}"):
                    st.code(log['prompt'], language="text")
            
            st.divider()

def main():
    """主应用"""
    # 侧边栏
    with st.sidebar:
        st.title("🔍 淘沙分析平台")
        st.markdown("---")
        
        # 健康检查
        api_client = get_api_client()
        if api_client.health_check():
            st.success("✅ 后端服务正常")
        else:
            st.error("❌ 后端服务异常")
            st.stop()
        
        # 系统状态
        with st.expander("📊 系统状态"):
            status = api_client.get_system_status()
            if "error" not in status:
                st.write(f"**应用**: {status.get('app_name')}")
                st.write(f"**版本**: {status.get('version')}")
                st.write(f"**数据库类型**: {status.get('database', {}).get('database_type')}")
                st.write(f"**表数量**: {status.get('database', {}).get('total_tables')}")
            else:
                st.error(status['error'])
        
        # 数据表信息
        with st.expander("📋 数据表"):
            tables = api_client.get_tables()
            if tables:
                for table in tables:
                    st.write(f"**{table['table_name']}**")
                    if table.get('comment'):
                        st.write(f"_{table['comment']}_")
                    st.write(f"行数: {table.get('row_count', 0)}")
                    st.divider()
            else:
                st.warning("未找到数据表")
        
        # 示例查询
        st.markdown("### 💡 示例查询")
        example_queries = [
            "显示所有销售数据",
            "北京地区的销售额是多少？",
            "按产品类别统计销售量",
            "哪个客户购买最多？",
            "今年的总销售额",
            "电子产品的平均价格"
        ]
        
        for query in example_queries:
            if st.button(query, key=f"example_{query}", use_container_width=True):
                st.session_state.query_input = query

    # 主界面
    st.title("🔍 淘沙数据分析助手")
    st.markdown("使用自然语言查询您的数据，获得即时的分析结果")
    
    # 查询输入区域
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query_input = st.text_input(
            "请输入您的问题：",
            value=st.session_state.get('query_input', ''),
            placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计",
            key="main_query_input",
            help="💡 提示：尽量明确时间范围、统计指标和筛选条件，这样能得到更准确的结果"
        )
    
    with col2:
        st.write("")  # 对齐
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            max_retries = st.selectbox("重试次数", [0, 1, 2, 3], index=2)
        with col2_2:
            submit_button = st.button("🚀 查询", type="primary", use_container_width=True)
    
    # 处理查询
    if submit_button and query_input:
        with st.spinner("正在分析您的问题..."):
            start_time = time.time()
            result = api_client.query(query_input, max_retries)
            end_time = time.time()
        
        # 首先显示输入清晰度验证结果（如果不清晰）
        clear_check_details = result.get('clear_check_details')
        clarity_issues_shown = display_input_clarity_result(clear_check_details)
        
        # 显示结果
        if result.get('success'):
            st.success(f"✅ 查询成功！耗时: {end_time - start_time:.2f}秒")
            
            # 显示生成的SQL
            if result.get('sql_query'):
                with st.expander("📝 生成的SQL查询", expanded=True):
                    st.code(result['sql_query'], language='sql')
            
            # 显示数据结果
            data = result.get('data', [])
            if data:
                st.markdown("### 📊 查询结果")
                
                # 创建两列布局
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### 📋 数据表格")
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # 数据统计
                    st.markdown("#### 📈 数据统计")
                    st.write(f"**总行数**: {len(data)}")
                    st.write(f"**列数**: {len(df.columns) if len(data) > 0 else 0}")
                    
                    # 如果是单行数据，显示为指标
                    if len(data) == 1:
                        st.markdown("#### 🎯 关键指标")
                        for key, value in data[0].items():
                            st.metric(label=key, value=value)
                
                with col2:
                    st.markdown("#### 📊 可视化图表")
                    
                    # 尝试创建图表
                    chart = create_chart(data)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    else:
                        st.info("数据不适合图表展示，或行数太少")
                        
                        # 如果数据有数值列，显示简单统计
                        df = pd.DataFrame(data)
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            st.markdown("**数值列统计：**")
                            st.dataframe(df[numeric_cols].describe())
            
            else:
                st.info("查询成功，但没有返回数据")
            
            # 显示执行日志
            if result.get('logs'):
                display_query_logs(result['logs'])
        
        else:
            st.error(f"❌ 查询失败: {result.get('error', '未知错误')}")
            
            # 如果之前没有显示过清晰度问题，再次尝试显示
            if not clarity_issues_shown:
                clear_check_details = result.get('clear_check_details')
                display_input_clarity_result(clear_check_details)
            
            # 显示执行日志（失败情况下也很有用）
            if result.get('logs'):
                display_query_logs(result['logs'])
    
    # 聊天历史（简单实现）
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # 如果有新的查询结果，添加到历史
    if submit_button and query_input:
        chat_entry = {
            'query': query_input,
            'timestamp': time.time(),
            'success': result.get('success', False),
            'sql': result.get('sql_query', ''),
            'data_count': len(result.get('data', [])) if result.get('data') is not None else 0
        }
        st.session_state.chat_history.append(chat_entry)
        # 只保留最近10条
        st.session_state.chat_history = st.session_state.chat_history[-10:]
    
    # 显示查询历史
    if st.session_state.chat_history:
        with st.expander("📜 查询历史", expanded=False):
            for i, entry in enumerate(reversed(st.session_state.chat_history)):
                success_icon = "✅" if entry['success'] else "❌"
                timestamp = time.strftime("%H:%M:%S", time.localtime(entry['timestamp']))
                
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{success_icon} {entry['query']}")
                with col2:
                    st.write(f"⏰ {timestamp}")
                with col3:
                    if st.button("重新查询", key=f"retry_{i}"):
                        st.session_state.query_input = entry['query']
                        st.experimental_rerun()
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        🔍 淘沙分析平台 - 让数据分析变得简单 | 
        <a href='http://localhost:8000/docs' target='_blank'>API文档</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()