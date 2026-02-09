import streamlit as st
import pandas as pd
from datetime import datetime
import traceback
import sys
import os

# 将当前目录加入搜索路径，确保能找到工具类
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from news_tool import fetch_cls_news, get_hot_keywords
from youtube_tool import search_youtube

# 页面配置
st.set_page_config(
    page_title="Jiahexin 数据抓取系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS 样式
st.markdown("""
<style>
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

def main():
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
            
        # 初始加载或点击按钮
        if 'news_data' not in st.session_state:
            st.session_state.news_data = None
            
        if fetch_news_btn or st.session_state.news_data is None:
            with st.spinner("正在抓取最新新闻，请稍候..."):
                try:
                    items = fetch_cls_news(keyword=news_keyword)
                    st.session_state.news_data = items
                except Exception as e:
                    st.error(f"抓取失败: {e}")
                    st.session_state.news_data = []

        if st.session_state.news_data:
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
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            for item in items:
                title = item.get('标题', '').strip()
                time_str = item.get('发布时间', '').strip()
                date_str = item.get('发布日期', '').strip()
                content = item.get('内容', '').strip()
                source = item.get('来源', '未知').strip()
                
                display_time = time_str if date_str == today_str else f"{date_str} {time_str}"
                source_class = "source-global" if any(x in source for x in ["华尔街见闻", "CNBC", "Yahoo"]) else "source-domestic"
                
                header_title = f"【{title}】" if title and title != "快讯" else ""
                
                st.markdown(f"""
                <div class="news-card">
                    <div class="news-header">
                        <span class="news-label {source_class}">{source}</span>
                        <span class="news-time">{display_time}</span>
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
            df = pd.DataFrame(st.session_state.yt_results)
            # 重命名列以便显示
            df.columns = ["标题", "频道", "时长", "视频链接"]
            
            # 使用 st.data_editor 实现可选中的表格
            st.markdown("### 🎬 搜索结果")
            st.write("勾选下方表格左侧复选框，然后点击按钮复制链接。")
            
            # 添加选择列
            df.insert(0, "选择", True)
            edited_df = st.data_editor(
                df,
                column_config={
                    "选择": st.column_config.CheckboxColumn(required=True),
                    "视频链接": st.column_config.LinkColumn()
                },
                disabled=["标题", "频道", "时长", "视频链接"],
                hide_index=True,
                use_container_width=True
            )
            
            # 复制链接功能
            selected_urls = edited_df[edited_df["选择"]]["视频链接"].tolist()
            if selected_urls:
                copy_text = "\n".join(selected_urls)
                if st.button(f"📋 复制选中的 {len(selected_urls)} 条链接"):
                    # Web 端复制到剪贴板比较特殊，通常通过 st.code 或 st.text_area 配合用户手动复制，
                    # 或者使用 st.toast/st.success 提示
                    st.text_area("点击下方框内内容并全选复制 (Ctrl+A, Ctrl+C):", value=copy_text, height=100)
                    st.success("已生成复制文本，请在上方文本框中手动复制。")
            else:
                st.info("请在表格中勾选至少一个视频以获取链接。")

if __name__ == "__main__":
    main()
