import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import traceback
import sys
import os

# --- 时区处理 ---
def get_beijing_time():
    # Streamlit Cloud 默认是 UTC 时间，需要手动转为北京时间 (UTC+8)
    return datetime.utcnow() + timedelta(hours=8)

# 将当前目录加入搜索路径，确保能找到工具类
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from news_tool import fetch_cls_news, get_hot_keywords
from youtube_tool import search_youtube

# --- 权限验证 ---
def check_password():
    """验证密码，成功返回 True，否则显示输入框"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("### 🔒 系统访问权限")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == "jhx654321":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密码错误！")
    return False

def main():
    # 页面配置
    st.set_page_config(
        page_title="嘉和信 信息抓取系统",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    if not check_password():
        return

    # 自定义 CSS 样式
    st.markdown("""
    <style>
        /* 优化表格中复选框的样式 */
        div[data-testid="stDataEditor"] .stCheckbox input[type="checkbox"]:checked {
            background-color: #ff0000 !important;
            border-color: #ff0000 !important;
        }
        /* 让表格容器更宽 */
        div[data-testid="stDataEditor"] {
            width: 100% !important;
        }
        .news-card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
            margin-bottom: 1rem;
            background-color: white;
        }
        .news-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 0.5rem;
        }
        .news-label {
            color: white;
            padding: 2px 8px;
            font-size: 0.8rem;
            border-radius: 4px;
            font-weight: bold;
        }
        .source-domestic { background-color: #3498db; }
        .source-global { background-color: #9b59b6; }
        .news-time { color: #e74c3c; font-size: 0.9rem; }
        .news-title { font-size: 1.1rem; font-weight: bold; color: #2c3e50; }
        .news-content { color: #34495e; line-height: 1.6; margin-top: 0.5rem; white-space: pre-wrap; }
        .hot-keyword {
            display: inline-block;
            background-color: #fff3e0;
            color: #e65100;
            padding: 4px 12px;
            border-radius: 16px;
            margin-right: 8px;
            margin-bottom: 8px;
            font-size: 0.9rem;
            border: 1px solid #ffe0b2;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("🔍 Jiahexin 数据抓取系统")
    
    tab1, tab2 = st.tabs(["📰 近3日新闻 & 热点", "🎥 YouTube 视频搜索"])
    
    # --- 1. 新闻面板 ---
    with tab1:
        col1, col2 = st.columns([4, 1])
        with col1:
            news_keyword = st.text_input("输入新闻关键词 (留空查看近3日热点)...", key="news_input")
        with col2:
            st.write(" ") # 占位
            st.write(" ") # 占位
            fetch_news_btn = st.button("获取新闻", use_container_width=True)
            
        # 只有点击按钮后才执行抓取，不再进入页面自动抓取
        if fetch_news_btn:
            with st.spinner("正在抓取最新新闻，请稍候..."):
                try:
                    items = fetch_cls_news(keyword=news_keyword)
                    st.session_state.news_data = items
                except Exception as e:
                    st.error(f"抓取失败: {e}")
                    st.session_state.news_data = []

        if 'news_data' in st.session_state and st.session_state.news_data:
            items = st.session_state.news_data
            
            # 热点话题
            if not news_keyword:
                hot = get_hot_keywords(items, top_n=12)
                st.markdown("### 🔥 近3日热点话题")
                hot_html = "".join([f'<span class="hot-keyword">{w} ({c})</span>' for w, c in hot])
                st.markdown(hot_html, unsafe_allow_html=True)
                st.write("---")
            
            # 新闻列表
            st.markdown(f"### 📋 找到 {len(items)} 条相关新闻")
            beijing_now = get_beijing_time()
            today_str = beijing_now.strftime('%Y-%m-%d')
            
            for item in items:
                title = item.get('标题', '').strip()
                time_str = item.get('发布时间', '').strip()
                date_str = item.get('发布日期', '').strip()
                content = item.get('内容', '').strip()
                source = item.get('来源', '未知').strip()
                
                # 针对 Streamlit Cloud 的时区修正：
                # 原始抓取到的 timestamp 是北京时间戳，但在云端服务器（UTC）环境下
                # datetime.fromtimestamp(ctime) 会按 UTC 转换，导致显示慢 8 小时
                ctime = item.get('timestamp')
                if ctime:
                    # 强制按北京时间 (UTC+8) 显示
                    dt_beijing = datetime.utcfromtimestamp(ctime) + timedelta(hours=8)
                    display_time = dt_beijing.strftime('%H:%M:%S')
                    display_date = dt_beijing.strftime('%Y-%m-%d')
                else:
                    display_time = time_str
                    display_date = date_str

                final_display_time = display_time if display_date == today_str else f"{display_date} {display_time}"
                source_class = "source-global" if any(x in source for x in ["华尔街见闻", "CNBC", "Yahoo"]) else "source-domestic"
                
                header_title = f"【{title}】" if title and title != "快讯" else ""
                
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-header">
                        <span class="news-label {source_class}">{source}</span>
                        <span class="news-time">{final_display_time}</span>
                        <span class="news-title">{header_title}</span>
                    </div>
                    <div class="news-content">{content}</div>
                </div>
                """, unsafe_allow_html=True)
        elif st.session_state.news_data == []:
            st.warning("未找到相关新闻。如果是刚启动，可能是网络超时，请点击“获取新闻”重试。")

    # --- 2. YouTube 面板 ---
    with tab2:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            yt_keyword = st.text_input("输入关键词搜索 YouTube 视频...", key="yt_input")
        with col2:
            yt_limit = st.number_input("搜索数量", min_value=1, max_value=50, value=10)
        with col3:
            st.write(" ") # 占位
            st.write(" ") # 占位
            yt_search_btn = st.button("搜索视频", use_container_width=True)
            
        if yt_search_btn:
            if not yt_keyword:
                st.warning("请输入关键词")
            else:
                with st.spinner("正在搜索 YouTube，请确保网络环境正常..."):
                    try:
                        results = search_youtube(yt_keyword, limit=yt_limit)
                        if results:
                            st.session_state.yt_results = results
                        else:
                            st.error("未找到视频或抓取失败。")
                            st.session_state.yt_results = None
                    except Exception as e:
                        st.error(f"搜索出错: {e}")
                        st.session_state.yt_results = None

        if 'yt_results' in st.session_state and st.session_state.yt_results:
            # 转换数据为 DataFrame 以便显示
            # 注意：youtube_tool 返回的字段顺序是 title, url, duration, channel
            df = pd.DataFrame(st.session_state.yt_results)
            
            # 重新整理列顺序和命名，确保不会填反
            df = df[['title', 'channel', 'duration', 'url']]
            df.columns = ["标题", "频道", "时长", "链接"]
            
            # 添加选择列，默认设为 True (全选)
            df.insert(0, "选择", True)
            
            st.markdown("### 🎬 搜索结果")
            
            # 配置表格显示
            edited_df = st.data_editor(
                df,
                column_config={
                    "选择": st.column_config.CheckboxColumn(
                        "选择",
                        help="勾选以复制链接",
                        default=True,
                        width="small",
                    ),
                    "标题": st.column_config.TextColumn(
                        "视频标题",
                        width="large",
                    ),
                    "频道": st.column_config.TextColumn(
                        "发布频道",
                        width="medium",
                    ),
                    "时长": st.column_config.TextColumn(
                        "视频时长",
                        width="small",
                    ),
                    "链接": st.column_config.LinkColumn(
                        "视频链接",
                        width="large",
                    ),
                },
                disabled=["标题", "频道", "链接", "时长"],
                hide_index=True,
                use_container_width=True,
            )
            
            # 提取选中的视频链接并提供复制按钮
            selected_rows = edited_df[edited_df["选择"] == True]
            if not selected_rows.empty:
                links_to_copy = "\n".join(selected_rows["链接"].tolist())
                # 隐藏 text_area，只提供一个按钮
                st.code(links_to_copy, language="text")
                st.info("👆 请点击上方框内右上角的按钮直接复制全部链接")
            else:
                st.info("在表格中勾选视频以获取链接")

if __name__ == "__main__":
    main()
