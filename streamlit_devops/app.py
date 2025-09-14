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
    
    def get_all_metadata_tables(self) -> List[Dict[str, Any]]:
        """获取所有元数据表"""
        try:
            response = requests.get(f"{self.base_url}/dev/metadata/tables", timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            st.error(f"获取元数据失败: {str(e)}")
            return []
    
    def add_table_metadata(self, name: str, comment: str, is_available: int = 0) -> bool:
        """添加表元数据"""
        try:
            response = requests.post(
                f"{self.base_url}/dev/metadata/tables",
                json={"name": name, "comment": comment, "is_available": is_available},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"添加表元数据失败: {str(e)}")
            return False
    
    def update_table_metadata(self, table_name: str, comment: str = None, is_available: int = None) -> bool:
        """更新表元数据"""
        try:
            update_data = {}
            if comment is not None:
                update_data["comment"] = comment
            if is_available is not None:
                update_data["is_available"] = is_available
            
            response = requests.put(
                f"{self.base_url}/dev/metadata/tables/{table_name}",
                json=update_data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"更新表元数据失败: {str(e)}")
            return False
    
    def delete_table_metadata(self, table_name: str) -> bool:
        """删除表元数据"""
        try:
            response = requests.delete(
                f"{self.base_url}/dev/metadata/tables/{table_name}",
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"删除表元数据失败: {str(e)}")
            return False
    
    def add_column_metadata(self, table_name: str, column_name: str, column_type: str, 
                           comment: str, is_available: int = 0, business_type: str = "", relation_id: str = "") -> bool:
        """添加列元数据"""
        try:
            response = requests.post(
                f"{self.base_url}/dev/metadata/columns",
                json={
                    "table_name": table_name,
                    "name": column_name,
                    "type": column_type,
                    "comment": comment,
                    "is_available": is_available,
                    "business_type": business_type,
                    "relation_id": relation_id
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"添加列元数据失败: {str(e)}")
            return False
    
    def update_column_metadata(self, table_name: str, column_name: str, column_type: str = None,
                              comment: str = None, is_available: int = None, business_type: str = None, relation_id: str = None) -> bool:
        """更新列元数据"""
        try:
            update_data = {}
            if column_type is not None:
                update_data["type"] = column_type
            if comment is not None:
                update_data["comment"] = comment
            if is_available is not None:
                update_data["is_available"] = is_available
            if business_type is not None:
                update_data["business_type"] = business_type
            if relation_id is not None:
                update_data["relation_id"] = relation_id
            
            response = requests.put(
                f"{self.base_url}/dev/metadata/columns/{table_name}/{column_name}",
                json=update_data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"更新列元数据失败: {str(e)}")
            return False
    
    def delete_column_metadata(self, table_name: str, column_name: str) -> bool:
        """删除列元数据"""
        try:
            response = requests.delete(
                f"{self.base_url}/dev/metadata/columns/{table_name}/{column_name}",
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"删除列元数据失败: {str(e)}")
            return False
    
    def sync_metadata_from_database(self) -> Dict[str, Any]:
        """从数据库同步元数据"""
        try:
            response = requests.post(
                f"{self.base_url}/dev/metadata/sync-from-database",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def get_all_terms(self) -> List[Dict[str, Any]]:
        """获取所有术语"""
        try:
            response = requests.get(f"{self.base_url}/dev/glossary/terms", timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            st.error(f"获取术语失败: {str(e)}")
            return []
    
    def add_term(self, term: str, definition: str, sql_expression: str, category: str, aliases: List[str]) -> bool:
        """添加术语"""
        try:
            response = requests.post(
                f"{self.base_url}/dev/glossary/terms",
                json={
                    "term": term,
                    "definition": definition,
                    "sql_expression": sql_expression,
                    "category": category,
                    "aliases": aliases
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"添加术语失败: {str(e)}")
            return False
    
    def update_term(self, term_id: int, term: str = None, definition: str = None, 
                   sql_expression: str = None, category: str = None) -> bool:
        """更新术语"""
        try:
            update_data = {}
            if term is not None:
                update_data["term"] = term
            if definition is not None:
                update_data["definition"] = definition
            if sql_expression is not None:
                update_data["sql_expression"] = sql_expression
            if category is not None:
                update_data["category"] = category
            
            response = requests.put(
                f"{self.base_url}/dev/glossary/terms/{term_id}",
                json=update_data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"更新术语失败: {str(e)}")
            return False
    
    def delete_term(self, term_id: int) -> bool:
        """删除术语"""
        try:
            response = requests.delete(f"{self.base_url}/dev/glossary/terms/{term_id}", timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"删除术语失败: {str(e)}")
            return False
    
    def get_all_relation_configs(self) -> List[Dict[str, Any]]:
        """获取所有关联字段配置"""
        try:
            response = requests.get(f"{self.base_url}/dev/relation-configs", timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            st.error(f"获取关联字段配置失败: {str(e)}")
            return []
    
    def add_relation_config(self, family: str, subfamily: str, desc: str = "") -> bool:
        """添加关联字段配置"""
        try:
            response = requests.post(
                f"{self.base_url}/dev/relation-configs",
                json={
                    "relation_family": family,
                    "relation_subfamily": subfamily,
                    "relation_desc": desc
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"添加关联字段配置失败: {str(e)}")
            return False
    
    def update_relation_config(self, relation_id: str, family: str = None, subfamily: str = None, desc: str = None) -> bool:
        """更新关联字段配置"""
        try:
            update_data = {}
            if family is not None:
                update_data["relation_family"] = family
            if subfamily is not None:
                update_data["relation_subfamily"] = subfamily
            if desc is not None:
                update_data["relation_desc"] = desc
            
            response = requests.put(
                f"{self.base_url}/dev/relation-configs/{relation_id}",
                json=update_data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"更新关联字段配置失败: {str(e)}")
            return False
    
    def delete_relation_config(self, relation_id: str) -> bool:
        """删除关联字段配置"""
        try:
            response = requests.delete(f"{self.base_url}/dev/relation-configs/{relation_id}", timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            st.error(f"删除关联字段配置失败: {str(e)}")
            return False
    
    def get_relation_ids(self) -> List[str]:
        """获取所有关联ID列表"""
        try:
            response = requests.get(f"{self.base_url}/dev/relation-configs/ids", timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            st.error(f"获取关联ID列表失败: {str(e)}")
            return []

# 初始化API客户端
@st.cache_resource
def get_api_client():
    return TaoshaAPIClient()

# 缓存数据获取函数
@st.cache_data(ttl=30)  # 30秒缓存
def get_metadata_tables_cached():
    """缓存的元数据表获取"""
    api_client = get_api_client()
    return api_client.get_all_metadata_tables()

@st.cache_data(ttl=30)  # 30秒缓存
def get_terms_cached():
    """缓存的术语获取"""
    api_client = get_api_client()
    return api_client.get_all_terms()

@st.cache_data(ttl=60)  # 60秒缓存
def get_tables_cached():
    """缓存的数据表获取"""
    api_client = get_api_client()
    return api_client.get_tables()

@st.cache_data(ttl=60)  # 60秒缓存  
def get_system_status_cached():
    """缓存的系统状态获取"""
    api_client = get_api_client()
    return api_client.get_system_status()

@st.cache_data(ttl=30)  # 30秒缓存
def get_relation_configs_cached():
    """缓存的关联字段配置获取"""
    api_client = get_api_client()
    return api_client.get_all_relation_configs()

@st.cache_data(ttl=30)  # 30秒缓存
def get_relation_ids_cached():
    """缓存的关联ID列表获取"""
    api_client = get_api_client()
    return api_client.get_relation_ids()

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
                        width='stretch',
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
    # 页面导航
    st.sidebar.title("🔍 淘沙分析平台")
    
    page = st.sidebar.radio(
        "选择页面",
        ["🏠 数据查询", "🛠️ 元数据管理", "📖 术语搜索"],
        index=0
    )
    
    if page == "🛠️ 元数据管理":
        metadata_management_page()
        return
    elif page == "📖 术语搜索":
        glossary_search_page()
        return
    
    # 主页面（数据查询）
    data_query_page()

def metadata_management_page():
    """元数据管理页面"""
    st.title("🛠️ 元数据管理")
    st.markdown("管理数据表和列的元数据信息，以及业务术语表")
    
    api_client = get_api_client()
    
    # 创建选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["📋 表元数据", "📝 术语表", "🔗 关联配置", "🔄 数据库同步"])
    
    with tab1:
        st.header("表元数据管理")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 显示现有表元数据
            col_title, col_refresh = st.columns([3, 1])
            with col_title:
                st.subheader("📋 现有表元数据")
            with col_refresh:
                if st.button("🔄 刷新", key="refresh_metadata"):
                    st.cache_data.clear()
                    st.rerun()
            
            metadata_tables = get_metadata_tables_cached()
            
            if metadata_tables:
                for table in metadata_tables:
                    # 表名显示，根据是否可用添加状态标识
                    availability_icon = "✅" if table.get('is_available', 0) == 0 else "❌"
                    with st.expander(f"{availability_icon} 📊 {table['name']}", expanded=False):
                        col_desc, col_status = st.columns([3, 1])
                        with col_desc:
                            st.write(f"**描述**: {table.get('comment', '无描述')}")
                        with col_status:
                            is_available = table.get('is_available', 0)
                            status_text = "🟢 可用" if is_available == 0 else "🔴 不可用"
                            st.write(f"**状态**: {status_text}")
                        
                        # 显示列信息
                        columns = table.get('columns', [])
                        if columns:
                            st.write(f"**列数**: {len(columns)}")
                            
                            # 显示列信息表格
                            # 为显示添加状态图标
                            display_columns = []
                            for col in columns:
                                display_col = col.copy()
                                # 添加状态图标
                                is_available = col.get('is_available', 0)
                                status_icon = "✅" if is_available == 0 else "❌"
                                display_col['status'] = f"{status_icon} {'可用' if is_available == 0 else '不可用'}"
                                
                                # 优化业务类型显示
                                display_col['business_type'] = col.get('business_type') or col.get('type', '')
                                
                                display_columns.append(display_col)
                            
                            # 创建 DataFrame 并显示
                            col_df = pd.DataFrame(display_columns)
                            # 重新排列列顺序
                            column_order = ['name', 'type', 'business_type', 'status', 'relation_id', 'comment']
                            available_columns = [col for col in column_order if col in col_df.columns]
                            col_df = col_df[available_columns]
                            
                            # 重命名列标题为中文
                            col_df = col_df.rename(columns={
                                'name': '列名',
                                'type': '存储类型', 
                                'business_type': '业务类型',
                                'status': '状态',
                                'relation_id': '关联ID',
                                'comment': '描述'
                            })
                            
                            st.dataframe(col_df, width='stretch')
                            
                            # 列编辑区域
                            with st.expander("📝 编辑列元数据", expanded=False):
                                if columns:
                                    # 列选择
                                    col_names = [col.get('name', '') for col in columns]
                                    selected_col_name = st.selectbox("选择要编辑的列", col_names, key=f"select_col_{table['name']}")
                                    
                                    # 找到选中的列
                                    selected_col = None
                                    selected_index = -1
                                    for i, col in enumerate(columns):
                                        if col.get('name') == selected_col_name:
                                            selected_col = col
                                            selected_index = i
                                            break
                                    
                                    if selected_col:
                                        st.markdown(f"**编辑列: {selected_col_name}**")
                                        
                                        col_form1, col_form2, col_form3, col_form4 = st.columns(4)
                                        
                                        with col_form1:
                                            edit_storage_type = st.selectbox(
                                                "存储类型",
                                                ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"],
                                                index=["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"].index(selected_col.get('type', 'VARCHAR')) if selected_col.get('type') in ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"] else 0,
                                                key=f"edit_col_type_{table['name']}_{selected_index}"
                                            )
                                            
                                            edit_business_type = st.selectbox(
                                                "业务类型",
                                                ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"],
                                                index=["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"].index(selected_col.get('business_type') or selected_col.get('type', 'VARCHAR')) if (selected_col.get('business_type') or selected_col.get('type', 'VARCHAR')) in ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"] else 0,
                                                key=f"edit_col_business_type_{table['name']}_{selected_index}"
                                            )
                                        
                                        with col_form2:
                                            edit_col_comment = st.text_area(
                                                "列描述",
                                                value=selected_col.get('comment', ''),
                                                key=f"edit_col_comment_{table['name']}_{selected_index}"
                                            )
                                        
                                        with col_form3:
                                            edit_col_available = st.selectbox(
                                                "状态",
                                                options=[0, 1],
                                                format_func=lambda x: "可用" if x == 0 else "不可用",
                                                index=selected_col.get('is_available', 0),
                                                key=f"edit_col_available_{table['name']}_{selected_index}"
                                            )
                                            
                                            # 获取关联ID列表
                                            relation_ids = get_relation_ids_cached()
                                            relation_options = [""] + relation_ids
                                            current_relation_index = 0
                                            if selected_col.get('relation_id') and selected_col.get('relation_id') in relation_options:
                                                current_relation_index = relation_options.index(selected_col.get('relation_id'))
                                            
                                            edit_relation_id = st.selectbox(
                                                "关联ID",
                                                options=relation_options,
                                                index=current_relation_index,
                                                key=f"edit_col_relation_{table['name']}_{selected_index}"
                                            )
                                        
                                        with col_form4:
                                            st.write("")  # 对齐
                                            
                                            # 更新按钮
                                            if st.button("📝 更新列", key=f"update_col_{table['name']}_{selected_index}", type="primary"):
                                                if api_client.update_column_metadata(
                                                    table['name'], 
                                                    selected_col.get('name'),
                                                    edit_storage_type,
                                                    edit_col_comment,
                                                    edit_col_available,
                                                    edit_business_type,
                                                    edit_relation_id
                                                ):
                                                    st.success(f"列 {selected_col.get('name')} 元数据已更新")
                                                    st.cache_data.clear()
                                                    st.rerun()
                                            
                                            # 删除按钮
                                            if st.button("🗑️ 删除列", key=f"delete_col_{table['name']}_{selected_index}"):
                                                if st.session_state.get(f"confirm_delete_col_{table['name']}_{selected_col.get('name')}", False):
                                                    if api_client.delete_column_metadata(table['name'], selected_col.get('name')):
                                                        st.success(f"列 {selected_col.get('name')} 已删除")
                                                        st.cache_data.clear()
                                                        st.rerun()
                                                else:
                                                    st.session_state[f"confirm_delete_col_{table['name']}_{selected_col.get('name')}"] = True
                                                    st.warning("再次点击确认删除")
                                    else:
                                        st.warning("未找到选中的列")
                                else:
                                    st.info("该表暂无列元数据")
                        else:
                            st.info("该表暂无列元数据")
                        
                        # 操作按钮
                        col_edit, col_del = st.columns(2)
                        
                        with col_edit:
                            st.markdown("**编辑表元数据**")
                            new_comment = st.text_input(
                                "描述",
                                value=table.get('comment', ''),
                                key=f"edit_comment_{table['name']}"
                            )
                            current_is_available = table.get('is_available', 0)
                            new_is_available = st.selectbox(
                                "状态",
                                options=[0, 1],
                                format_func=lambda x: "可用" if x == 0 else "不可用",
                                index=current_is_available,
                                key=f"edit_status_{table['name']}"
                            )
                            if st.button(f"更新表元数据", key=f"update_{table['name']}"):
                                if api_client.update_table_metadata(table['name'], new_comment, new_is_available):
                                    st.success(f"表 {table['name']} 元数据已更新")
                                    st.cache_data.clear()  # 清除缓存
                                    st.rerun()
                        
                        with col_del:
                            st.write("")  # 对齐
                            if st.button(f"删除表", key=f"delete_{table['name']}"):
                                if st.session_state.get(f"confirm_delete_{table['name']}", False):
                                    if api_client.delete_table_metadata(table['name']):
                                        st.success(f"表 {table['name']} 元数据已删除")
                                        st.cache_data.clear()  # 清除缓存
                                        st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_{table['name']}"] = True
                                    st.warning("再次点击确认删除")
                        
                        # 添加列元数据
                        st.markdown("**添加列元数据**")
                        col_col1, col_col2, col_col3, col_col4 = st.columns(4)
                        
                        with col_col1:
                            new_col_name = st.text_input("列名", key=f"col_name_{table['name']}")
                            new_col_type = st.selectbox(
                                "存储类型",
                                ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"],
                                key=f"col_type_{table['name']}"
                            )
                        
                        with col_col2:
                            new_col_comment = st.text_area("列描述", key=f"col_comment_{table['name']}")
                            new_business_type = st.selectbox(
                                "业务类型",
                                ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"],
                                key=f"col_business_type_{table['name']}"
                            )
                        
                        with col_col3:
                            col_is_available = st.selectbox(
                                "状态",
                                options=[0, 1],
                                format_func=lambda x: "可用" if x == 0 else "不可用",
                                index=0,
                                key=f"col_available_{table['name']}"
                            )
                            # 获取关联ID列表
                            relation_ids = get_relation_ids_cached()
                            relation_options = [""] + relation_ids
                            new_relation_id = st.selectbox(
                                "关联ID",
                                options=relation_options,
                                key=f"col_relation_id_{table['name']}"
                            )
                        
                        with col_col4:
                            st.write("")  # 对齐
                            if st.button("添加列", key=f"add_col_{table['name']}"):
                                if new_col_name and new_col_type:
                                    if api_client.add_column_metadata(
                                        table['name'], new_col_name, new_col_type, 
                                        new_col_comment, col_is_available, new_business_type, new_relation_id
                                    ):
                                        st.success(f"列 {new_col_name} 已添加到表 {table['name']}")
                                        st.cache_data.clear()  # 清除缓存
                                        st.rerun()
                                else:
                                    st.error("请填写列名和类型")
            else:
                st.info("暂无表元数据，可从右侧添加或使用数据库同步功能")
        
        with col2:
            st.subheader("➕ 添加新表")
            
            with st.form("add_table_form"):
                new_table_name = st.text_input("表名")
                new_table_comment = st.text_area("表描述")
                table_is_available = st.selectbox(
                    "状态",
                    options=[0, 1],
                    format_func=lambda x: "可用" if x == 0 else "不可用",
                    index=0
                )
                
                submit_table = st.form_submit_button("添加表")
                
                if submit_table:
                    if new_table_name:
                        if api_client.add_table_metadata(new_table_name, new_table_comment, table_is_available):
                            st.success(f"表 {new_table_name} 元数据已添加")
                            st.cache_data.clear()  # 清除缓存
                            st.rerun()
                    else:
                        st.error("请输入表名")
    
    with tab2:
        st.header("业务术语表管理")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 显示现有术语
            col_title, col_refresh = st.columns([3, 1])
            with col_title:
                st.subheader("📖 现有术语")
            with col_refresh:
                if st.button("🔄 刷新", key="refresh_terms"):
                    st.cache_data.clear()
                    st.rerun()
            
            terms = get_terms_cached()
            
            if terms:
                for i, term in enumerate(terms):
                    term_id = term.get('id')
                    with st.expander(f"📝 {term['term']}", expanded=False):
                        # 显示区域
                        st.write(f"**定义**: {term.get('definition', '无定义')}")
                        st.write(f"**SQL表达式**: {term.get('sql_expression', '无表达式')}")
                        st.write(f"**分类**: {term.get('category', '无分类')}")
                        
                        aliases = term.get('aliases', [])
                        if aliases:
                            st.write(f"**别名**: {', '.join(aliases)}")
                        
                        if term_id:
                            # 编辑区域
                            st.markdown("---")
                            st.markdown("**编辑术语**")
                            
                            col_term1, col_term2 = st.columns(2)
                            
                            with col_term1:
                                edit_term_name = st.text_input(
                                    "术语名称",
                                    value=term.get('term', ''),
                                    key=f"edit_term_name_{term_id}"
                                )
                                edit_definition = st.text_area(
                                    "术语定义",
                                    value=term.get('definition', ''),
                                    key=f"edit_definition_{term_id}"
                                )
                            
                            with col_term2:
                                edit_sql_expr = st.text_area(
                                    "SQL表达式",
                                    value=term.get('sql_expression', ''),
                                    key=f"edit_sql_expr_{term_id}"
                                )
                                edit_category = st.text_input(
                                    "分类",
                                    value=term.get('category', ''),
                                    key=f"edit_category_{term_id}"
                                )
                            
                            # 按钮区域
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                if st.button("📝 更新术语", key=f"update_term_{term_id}", type="primary"):
                                    if api_client.update_term(
                                        term_id,
                                        edit_term_name,
                                        edit_definition,
                                        edit_sql_expr,
                                        edit_category
                                    ):
                                        st.success(f"术语 {edit_term_name} 已更新")
                                        st.cache_data.clear()
                                        st.rerun()
                            
                            with col_btn2:
                                if st.button("🗑️ 删除术语", key=f"del_term_{term_id}"):
                                    if st.session_state.get(f"confirm_delete_term_{term_id}", False):
                                        if api_client.delete_term(term_id):
                                            st.success(f"术语 {term.get('term')} 已删除")
                                            st.cache_data.clear()
                                            st.rerun()
                                    else:
                                        st.session_state[f"confirm_delete_term_{term_id}"] = True
                                        st.warning("再次点击确认删除")
                        else:
                            st.warning("术语ID缺失，无法编辑")
            else:
                st.info("暂无业务术语，可从右侧添加")
        
        with col2:
            st.subheader("➕ 添加新术语")
            
            with st.form("add_term_form"):
                new_term = st.text_input("术语名称")
                new_definition = st.text_area("术语定义")
                new_sql_expr = st.text_area("SQL表达式")
                new_category = st.text_input("分类")
                new_aliases_str = st.text_input("别名（用逗号分隔）")
                
                submit_term = st.form_submit_button("添加术语")
                
                if submit_term:
                    if new_term:
                        aliases = [alias.strip() for alias in new_aliases_str.split(",") if alias.strip()]
                        if api_client.add_term(new_term, new_definition, new_sql_expr, new_category, aliases):
                            st.success(f"术语 {new_term} 已添加")
                            st.cache_data.clear()  # 清除缓存
                            st.rerun()
                    else:
                        st.error("请输入术语名称")
    
    with tab3:
        st.header("🔗 关联字段配置管理")
        st.markdown("管理字段关联ID配置，用于字段业务关联分类")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 显示现有关联配置
            col_title, col_refresh = st.columns([3, 1])
            with col_title:
                st.subheader("🔗 现有关联配置")
            with col_refresh:
                if st.button("🔄 刷新", key="refresh_relations"):
                    st.cache_data.clear()
                    st.rerun()
            
            relation_configs = get_relation_configs_cached()
            
            if relation_configs:
                for config in relation_configs:
                    relation_id = config['relation_id']
                    with st.expander(f"🔗 {relation_id}", expanded=False):
                        # 显示区域
                        st.write(f"**关联族**: {config.get('relation_family', '')}")
                        st.write(f"**关联子族**: {config.get('relation_subfamily', '')}")
                        st.write(f"**描述**: {config.get('relation_desc', '无描述')}")
                        
                        # 编辑区域
                        st.markdown("---")
                        st.markdown("**编辑关联配置**")
                        
                        col_rel1, col_rel2 = st.columns(2)
                        
                        with col_rel1:
                            edit_family = st.text_input(
                                "关联族",
                                value=config.get('relation_family', ''),
                                key=f"edit_family_{relation_id}"
                            )
                            edit_subfamily = st.text_input(
                                "关联子族",
                                value=config.get('relation_subfamily', ''),
                                key=f"edit_subfamily_{relation_id}"
                            )
                        
                        with col_rel2:
                            edit_desc = st.text_area(
                                "描述",
                                value=config.get('relation_desc', ''),
                                key=f"edit_desc_{relation_id}"
                            )
                            
                            # 预览新的关联ID
                            if edit_family and edit_subfamily:
                                new_relation_id = f"{edit_family}|{edit_subfamily}"
                                if new_relation_id != relation_id:
                                    st.info(f"新关联ID: {new_relation_id}")
                        
                        # 按钮区域
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button("📝 更新配置", key=f"update_relation_{relation_id}", type="primary"):
                                if edit_family and edit_subfamily:
                                    if api_client.update_relation_config(
                                        relation_id,
                                        edit_family,
                                        edit_subfamily,
                                        edit_desc
                                    ):
                                        new_id = f"{edit_family}|{edit_subfamily}"
                                        st.success(f"关联配置已更新: {relation_id} -> {new_id}")
                                        st.cache_data.clear()
                                        st.rerun()
                                else:
                                    st.error("请填写关联族和关联子族")
                        
                        with col_btn2:
                            if st.button("🗑️ 删除配置", key=f"delete_relation_{relation_id}"):
                                if st.session_state.get(f"confirm_delete_relation_{relation_id}", False):
                                    if api_client.delete_relation_config(relation_id):
                                        st.success(f"关联配置 {relation_id} 已删除")
                                        st.cache_data.clear()
                                        st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_relation_{relation_id}"] = True
                                    st.warning("再次点击确认删除")
            else:
                st.info("暂无关联配置，可从右侧添加")
        
        with col2:
            st.subheader("➕ 添加关联配置")
            
            with st.form("add_relation_form"):
                st.info("关联ID格式：关联族|关联子族")
                new_family = st.text_input("关联族", placeholder="如：cust_no")
                new_subfamily = st.text_input("关联子族", placeholder="如：17")
                new_desc = st.text_area("描述", placeholder="请输入关联字段的描述...")
                
                # 显示预览
                if new_family and new_subfamily:
                    preview_id = f"{new_family}|{new_subfamily}"
                    st.success(f"预览关联ID: {preview_id}")
                
                submit_relation = st.form_submit_button("添加关联配置")
                
                if submit_relation:
                    if new_family and new_subfamily:
                        if api_client.add_relation_config(new_family, new_subfamily, new_desc):
                            st.success(f"关联配置 {new_family}|{new_subfamily} 已添加")
                            st.cache_data.clear()  # 清除缓存
                            st.rerun()
                    else:
                        st.error("请填写关联族和关联子族")
    
    with tab4:
        st.header("数据库同步")
        st.markdown("从实际数据库自动同步表结构到元数据管理系统")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.info("""
            **同步功能说明**：
            - 自动扫描数据库中的所有表
            - 为不存在的表创建基础元数据
            - 自动添加列信息（名称、类型、是否可空）
            - 不会覆盖已有的描述信息
            """)
        
        with col2:
            if st.button("🔄 从数据库同步元数据", type="primary", width='stretch'):
                with st.spinner("正在同步数据库元数据..."):
                    result = api_client.sync_metadata_from_database()
                
                if result.get('success'):
                    st.success(f"✅ 同步完成！{result.get('message', '')}")
                    
                    synced_tables = result.get('synced_tables', [])
                    if synced_tables:
                        st.write("**同步的表：**")
                        for table in synced_tables:
                            st.write(f"- {table}")
                    
                    # 清除缓存并刷新页面显示最新数据
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ 同步失败：{result.get('error', '未知错误')}")

def glossary_search_page():
    """术语表搜索页面"""
    st.title("🔍 术语表搜索")
    st.markdown("搜索和查找业务术语定义")
    
    api_client = get_api_client()
    
    # 搜索框
    search_query = st.text_input("输入要搜索的术语或别名", placeholder="例如：销售额、收入")
    
    if search_query:
        # 这里需要实现搜索API调用
        st.info("搜索功能待实现 - 需要调用术语搜索API")
    
    # 显示所有术语作为参考
    st.subheader("📋 所有术语")
    terms = get_terms_cached()
    
    if terms:
        for term in terms:
            with st.expander(f"📝 {term['term']}"):
                st.write(f"**定义**: {term.get('definition', '无定义')}")
                if term.get('sql_expression'):
                    st.code(term['sql_expression'], language='sql')
                if term.get('category'):
                    st.badge(term['category'])
                if term.get('aliases'):
                    st.write(f"**别名**: {', '.join(term['aliases'])}")
    else:
        st.info("暂无术语数据")

def data_query_page():
    """数据查询页面"""
    # 侧边栏信息
    with st.sidebar:
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
            status = get_system_status_cached()
            if "error" not in status:
                st.write(f"**应用**: {status.get('app_name')}")
                st.write(f"**版本**: {status.get('version')}")
                st.write(f"**数据库类型**: {status.get('database', {}).get('database_type')}")
                st.write(f"**表数量**: {status.get('database', {}).get('total_tables')}")
            else:
                st.error(status['error'])
        
        # 数据表信息
        with st.expander("📋 数据表"):
            tables = get_tables_cached()
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
            if st.button(query, key=f"example_{query}", width='stretch'):
                st.session_state.query_input = query

    # 主界面内容
    st.title("🔍 淘沙数据分析助手")
    st.markdown("使用自然语言查询您的数据，获得即时的分析结果")
    
    api_client = get_api_client()
    
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
            submit_button = st.button("🚀 查询", type="primary", width='stretch')
    
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
                    st.dataframe(df, width='stretch')
                    
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
                        st.plotly_chart(chart, width='stretch')
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
                        st.rerun()
    
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