import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import jieba
from collections import Counter
import re
import requests
import time

def get_hot_keywords(news_items, top_n=10):
    """
    Analyzes news titles to extract hot keywords using jieba.
    Returns a list of (keyword, count) tuples.
    """
    if not news_items:
        return []
        
    text = ""
    for item in news_items:
        text += str(item.get('标题', '')) + " "
        
    # Exclude common stop words (simplified list)
    stop_words = {'的', '了', '在', '是', '和', '有', '为', '对', '等', '及', '与', '上', '下', '年', '月', '日', '公司', '财联社', '电', '表示', '显示', '指出', '称', '至', '于', '中', '大', '小', '前', '后', '万', '元', '华尔街', '见闻', '快讯'}
    
    words = jieba.cut(text)
    filtered_words = []
    for w in words:
        if len(w) > 1 and w not in stop_words and not w.isnumeric():
            filtered_words.append(w)
            
    return Counter(filtered_words).most_common(top_n)

def fetch_cls_news_fallback():
    """
    恢复自 look.py 的稳健抓取逻辑：聚合财联社、华尔街见闻和国际 RSS 源。
    并保留“近3日”过滤逻辑。
    """
    all_news = []
    seen_titles = set()
    
    # 获取 3 天前的时间戳
    now = datetime.now()
    three_days_ago = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_timestamp = int(three_days_ago.timestamp())
    
    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # 1. 抓取财联社 (CLS)
    print(f"Fetching from CLS (Target: {datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M')})...")
    cls_url = "https://www.cls.cn/nodeapi/telegraphList"
    
    # 既然 nodeapi 分页彻底失效，我们只能通过合并所有分类来尽可能覆盖更多数据
    # 增加更多分类标识
    categories = [
        "", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "stock", "fund", "money", "hkstock", "usstock", "future", "bond", "forex",
        "announcement", "interpretation", "red", "push", "remind", "watch", "fund_news",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"
    ]
    
    for cat in categories:
        try:
            # 每个分类只抓取第 1 页，因为分页参数失效
            params = {
                "rn": 100, # 尝试请求更多，虽然 API 可能只给 50
                "refresh_type": 1, 
                "app": "CailianpressWeb", 
                "os": "web",
                "category": cat
            }
            
            res = session.get(cls_url, params=params, headers=headers, timeout=10)
            data_json = res.json()
            items = data_json.get('data', {}).get('roll_data', [])

            if not items: continue
            
            for item in items:
                ctime = item.get('ctime')
                if not ctime: continue
                
                if ctime < start_timestamp: continue
                
                title = str(item.get('title', '')).strip()
                content = str(item.get('content', '')).strip()
                if not title and content:
                    title = content[:30].strip() + "..."
                
                if not title: continue
                if title in seen_titles: continue
                seen_titles.add(title)
                
                dt = datetime.fromtimestamp(ctime)
                all_news.append({
                    '标题': title,
                    '内容': content,
                    '发布时间': dt.strftime('%H:%M:%S'),
                    '发布日期': dt.strftime('%Y-%m-%d'),
                    'timestamp': ctime,
                    '来源': '财联社'
                })
            time.sleep(0.05)
        except Exception:
            continue
    print(f"CLS fetch finished via multi-category aggregation. Total unique items: {len([n for n in all_news if n['来源'] == '财联社'])}")

    # 2. 抓取华尔街见闻 (WallStreetCN) - 使用 look.py 的多频道配置
    print("Fetching from WallStreetCN (Multi-Channel)...")
    wsn_channels = [
        {"id": "global-channel", "name": "全球要闻"},
        {"id": "us-stock-channel", "name": "美股快讯"},
        {"id": "forex-channel", "name": "全球外汇"},
        {"id": "commodity-channel", "name": "大宗商品"}
    ]
    
    for channel in wsn_channels:
        last_cursor = None
        page_count = 0
        max_wsn_pages = 10 # 华尔街见闻各频道也增加抓取深度
        
        while page_count < max_wsn_pages:
            try:
                wsn_api = "https://api-one.wallstcn.com/apiv1/content/lives"
                params = {"channel": channel['id'], "client": "pc", "limit": 100}
                if last_cursor:
                    params["cursor"] = last_cursor
                
                res = session.get(wsn_api, params=params, headers=headers, timeout=10)
                data = res.json().get('data', {})
                items = data.get('items', [])
                if not items: break
                
                page_count += 1
                next_cursor = data.get('next_cursor')
                last_cursor = next_cursor
                
                reached_start = False
                page_min_time = items[0].get('display_time')
                
                for item in items:
                    ctime = item.get('display_time')
                    page_min_time = min(page_min_time, ctime)
                    
                    if ctime < start_timestamp:
                        reached_start = True
                        continue
                    
                    content = re.sub(r'<[^>]+>', '', item.get('content_text', ''))
                    title = item.get('title', '').strip()
                    if not title:
                        title = content[:30].strip() + "..."
                    
                    title_key = title[:20]
                    if title_key in seen_titles: continue
                    seen_titles.add(title_key)
                    
                    dt = datetime.fromtimestamp(ctime)
                    all_news.append({
                        '标题': title,
                        '内容': content,
                        '发布时间': dt.strftime('%H:%M:%S'),
                        '发布日期': dt.strftime('%Y-%m-%d'),
                        'timestamp': ctime,
                        '来源': f"华尔街见闻({channel['name']})"
                    })
                
                if reached_start or not next_cursor: break
                time.sleep(0.1)
            except Exception as e:
                print(f"WallStreetCN {channel['name']} error at page {page_count}: {e}")
                break
        print(f"WSN {channel['name']}: Finished after {page_count} pages")

    # 3. 抓取国际源 (RSS) - 使用 look.py 的正则解析方式（不依赖 feedparser）
    print("Fetching from International Sources (RSS)...")
    int_sources = [
        {"name": "CNBC (Business)", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
        {"name": "CNBC (World)", "url": "https://www.cnbc.com/id/100727302/device/rss/rss.html"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
    ]
    
    for source in int_sources:
        try:
            res = session.get(source['url'], headers=headers, timeout=10)
            if res.status_code == 200:
                xml_content = res.text
                items = re.findall(r'<item>(.*?)</item>', xml_content, re.S)
                for item in items:
                    title_match = re.search(r'<title>(.*?)</title>', item, re.S)
                    date_match = re.search(r'<pubDate>(.*?)</pubDate>', item, re.S)
                    
                    if title_match:
                        title = title_match.group(1).strip()
                        title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title)
                        
                        # 解析时间并过滤
                        dt = None
                        if date_match:
                            try:
                                date_str = date_match.group(1).strip()
                                # 尝试解析常见的 RSS 日期格式
                                dt = datetime.strptime(date_str[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                            except:
                                dt = datetime.now()
                        else:
                            dt = datetime.now()
                        
                        ts = int(dt.timestamp())
                        if ts < start_timestamp: continue
                        
                        if title in seen_titles: continue
                        seen_titles.add(title)
                        
                        desc_match = re.search(r'<description>(.*?)</description>', item, re.S)
                        content = ""
                        if desc_match:
                            content = desc_match.group(1).strip()
                            content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content)
                            content = re.sub(r'<[^>]+>', '', content)
                        
                        all_news.append({
                            '标题': f"【{source['name']}】{title}",
                            '内容': content,
                            '发布时间': dt.strftime('%H:%M:%S'),
                            '发布日期': dt.strftime('%Y-%m-%d'),
                            'timestamp': ts,
                            '来源': f"{source['name']}"
                        })
        except Exception as e:
            print(f"RSS error for {source['name']}: {e}")

    # 按时间倒序排序
    df = pd.DataFrame(all_news)
    if not df.empty:
        df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
        
    return df

def fetch_cls_news(keyword=None, target_date=None):
    """
    获取财联社及组合源新闻。
    """
    df = fetch_cls_news_fallback()
    
    # 统一计算起始时间戳（用于备选方案过滤）
    now = datetime.now()
    three_days_ago = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_timestamp = int(three_days_ago.timestamp())

    if df.empty:
        try:
            # 如果主抓取逻辑失败，使用 AkShare 作为备选
            df = ak.stock_info_global_cls()
            if not df.empty:
                # 转换发布日期和时间为 timestamp 进行过滤
                # AkShare 返回的格式通常包含 '发布日期' 和 '发布时间'
                def to_ts(row):
                    try:
                        dt_str = f"{row['发布日期']} {row['发布时间']}"
                        return int(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').timestamp())
                    except:
                        return 0
                
                df['timestamp'] = df.apply(to_ts, axis=1)
                # 严格执行近3日过滤
                df = df[df['timestamp'] >= start_timestamp]
        except Exception:
            return []

    if df is None or df.empty:
        return []

    news_list = df.to_dict('records')
    
    if keyword:
        filtered_news = []
        keyword_lower = keyword.lower()
        for n in news_list:
            if keyword_lower in str(n.get('标题', '')).lower() or keyword_lower in str(n.get('内容', '')).lower():
                filtered_news.append(n)
        return filtered_news
    
    return news_list

if __name__ == "__main__":
    news = fetch_cls_news()
    print(f"Total news fetched: {len(news)}")
    if news:
        print("First item:", news[0])
