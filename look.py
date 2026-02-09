import akshare as ak
import pandas as pd
from datetime import datetime
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
    stop_words = {'的', '了', '在', '是', '和', '有', '为', '对', '等', '及', '与', '上', '下', '年', '月', '日', '公司', '财联社', '电', '表示', '显示', '指出', '称', '至', '于', '中', '大', '小', '前', '后', '万', '元'}
    
    words = jieba.cut(text)
    filtered_words = []
    for w in words:
        if len(w) > 1 and w not in stop_words and not w.isnumeric():
            filtered_words.append(w)
            
    return Counter(filtered_words).most_common(top_n)

def fetch_cls_news_fallback():
    """
    备用方法：聚合财联社、新浪财经和东方财富的新闻。
    解决财联社单源数量限制（约50条）的问题，确保达到500+条。
    """
    import requests
    import pandas as pd
    from datetime import datetime
    import time
    import re

    all_news = []
    seen_titles = set()
    
    # 获取本地日期
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # 1. 抓取财联社 (CLS) - 约 50 条
    print("Fetching from CLS...")
    cls_url = "https://www.cls.cn/nodeapi/telegraphList"
    try:
        params = {"rn": 50, "refresh_type": 1, "app": "CailianpressWeb", "os": "web"}
        res = session.get(cls_url, params=params, headers=headers, timeout=10)
        items = res.json().get('data', {}).get('roll_data', [])
        for item in items:
            title = str(item.get('title', '')).strip()
            content = str(item.get('content', '')).strip()
            if not title and content:
                title = content[:20] + "..."
            
            if title in seen_titles: continue
            seen_titles.add(title)
            
            ctime = item.get('ctime')
            dt = datetime.fromtimestamp(ctime)
            all_news.append({
                '标题': title,
                '内容': content,
                '发布时间': dt.strftime('%H:%M:%S'),
                '发布日期': dt.strftime('%Y-%m-%d'),
                'timestamp': ctime,
                '来源': '财联社'
            })
    except Exception as e:
        print(f"CLS fetch error: {e}")

    # 2. 抓取新浪财经 (Sina) - 暂时注释掉
    # print("Fetching from Sina...")
    # sina_url = "https://zhibo.sina.com.cn/api/zhibo/feed"
    # for page in range(1, 6):
    #     try:
    #         params = {"page": page, "page_size": 100, "zhibo_id": "152", "type": "1"}
    #         res = session.get(sina_url, params=params, headers=headers, timeout=10)
    #         items = res.json().get('result', {}).get('data', {}).get('feed', {}).get('list', [])
    #         if not items: break
    #         for item in items:
    #             content = re.sub(r'<[^>]+>', '', item.get('rich_text', ''))
    #             title = item.get('title', '')
    #             if not title:
    #                 title = content[:30].strip() + "..."
    #             
    #             # 去重：标题前20个字符相同则视为重复
    #             title_key = title[:20]
    #             if title_key in seen_titles: continue
    #             seen_titles.add(title_key)
    #             
    #             # 新浪时间格式: "2026-02-05 23:23:06"
    #             time_str = item.get('create_time')
    #             dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    #             all_news.append({
    #                 '标题': title,
    #                 '内容': content,
    #                 '发布时间': dt.strftime('%H:%M:%S'),
    #                 '发布日期': dt.strftime('%Y-%m-%d'),
    #                 'timestamp': int(dt.timestamp()),
    #                 '来源': '新浪财经'
    #             })
    #         time.sleep(0.2)
    #     except Exception as e:
    #         print(f"Sina fetch error on page {page}: {e}")
    #         break

    # 3. 抓取东方财富 (EastMoney) - 暂时注释掉
    # print("Fetching from EastMoney...")
    # em_url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
    # sort_end = ""
    # for page in range(5):
    #     try:
    #         params = {
    #             "client": "web", "biz": "web_724", "fastColumn": "102",
    #             "sortEnd": sort_end, "pageSize": 100, "req_trace": str(int(time.time() * 1000))
    #         }
    #         res = session.get(em_url, params=params, headers=headers, timeout=10)
    #         items = res.json().get('data', {}).get('fastNewsList', [])
    #         if not items: break
    #         for item in items:
    #             title = item.get('title', '')
    #             content = item.get('summary', '')
    #             if not title:
    #                 title = content[:30].strip() + "..."
    #             
    #             title_key = title[:20]
    #             if title_key in seen_titles: continue
    #             seen_titles.add(title_key)
    #             
    #             # 东财时间格式: "2026-02-05 19:44:24"
    #             time_str = item.get('showTime')
    #             dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    #             all_news.append({
    #                 '标题': title,
    #                 '内容': content,
    #                 '发布时间': dt.strftime('%H:%M:%S'),
    #                 '发布日期': dt.strftime('%Y-%m-%d'),
    #                 'timestamp': int(dt.timestamp()),
    #                 '来源': '东方财富'
    #             })
    #         sort_end = items[-1].get('showTime')
    #         time.sleep(0.2)
    #     except Exception as e:
    #         print(f"EM fetch error on page {page}: {e}")
    #         break

    # 4. 抓取华尔街见闻 (WallStreetCN) - 多频道聚合
    print("Fetching from WallStreetCN (Multi-Channel)...")
    wsn_channels = [
        {"id": "global-channel", "name": "全球要闻"},
        {"id": "us-stock-channel", "name": "美股快讯"},
        {"id": "forex-channel", "name": "全球外汇"},
        {"id": "commodity-channel", "name": "大宗商品"}
    ]
    
    for channel in wsn_channels:
        try:
            print(f"  Fetching {channel['name']}...")
            # 使用更稳定的 api-one 域名
            wsn_api = "https://api-one.wallstcn.com/apiv1/content/lives"
            params = {"channel": channel['id'], "client": "pc", "limit": 40}
            res = session.get(wsn_api, params=params, headers=headers, timeout=10)
            items = res.json().get('data', {}).get('items', [])
            
            for item in items:
                content = re.sub(r'<[^>]+>', '', item.get('content_text', ''))
                title = item.get('title', '')
                if not title:
                    title = content[:30].strip() + "..."
                
                title_key = title[:20]
                if title_key in seen_titles: continue
                seen_titles.add(title_key)
                
                ctime = item.get('display_time')
                dt = datetime.fromtimestamp(ctime)
                all_news.append({
                    '标题': title,
                    '内容': content,
                    '发布时间': dt.strftime('%H:%M:%S'),
                    '发布日期': dt.strftime('%Y-%m-%d'),
                    'timestamp': ctime,
                    '来源': f"华尔街见闻({channel['name']})"
                })
        except Exception as e:
            print(f"WallStreetCN {channel['name']} error: {e}")

    # 5. 尝试抓取国际源 (RSS) - 增加容错和更多源
    print("Fetching from International Sources (RSS)...")
    int_sources = [
        {"name": "CNBC (Business)", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"}, # Business News
        {"name": "CNBC (World)", "url": "https://www.cnbc.com/id/100727302/device/rss/rss.html"},    # World News
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
    ]
    
    for source in int_sources:
        try:
            res = session.get(source['url'], headers=headers, timeout=10)
            if res.status_code == 200:
                # 简单正则解析 RSS (不引入 feedparser 以免打包出错)
                xml_content = res.text
                items = re.findall(r'<item>(.*?)</item>', xml_content, re.S)
                for item in items[:15]: # 每个源取前15条
                    title_match = re.search(r'<title>(.*?)</title>', item, re.S)
                    link_match = re.search(r'<link>(.*?)</link>', item, re.S)
                    desc_match = re.search(r'<description>(.*?)</description>', item, re.S)
                    date_match = re.search(r'<pubDate>(.*?)</pubDate>', item, re.S)
                    
                    if title_match:
                        title = title_match.group(1).strip()
                        # 清理 CDATA
                        title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title)
                        
                        if title in seen_titles: continue
                        seen_titles.add(title)
                        
                        content = ""
                        if desc_match:
                            content = desc_match.group(1).strip()
                            content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content)
                            content = re.sub(r'<[^>]+>', '', content) # 清理 HTML
                        
                        # 解析时间
                        dt = None
                        if date_match:
                            try:
                                # "Mon, 09 Feb 2026 10:00:00 GMT"
                                date_str = date_match.group(1).strip()
                                dt = datetime.strptime(date_str[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                            except:
                                dt = datetime.now()
                        else:
                            dt = datetime.now()
                            
                        all_news.append({
                            '标题': f"【{source['name']}】{title}",
                            '内容': content,
                            '发布时间': dt.strftime('%H:%M:%S'),
                            '发布日期': dt.strftime('%Y-%m-%d'),
                            'timestamp': int(dt.timestamp()),
                            '来源': f"{source['name']}"
                        })
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")

    # 按时间倒序排序
    df = pd.DataFrame(all_news)
    if not df.empty:
        df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
        
    return df

def fetch_cls_news(keyword=None, target_date=None):
    """
    获取财联社新闻。
    默认直接使用 API 获取以保证速度，如果失败则尝试 AkShare。
    """
    # 优先使用直接 API 获取，因为更快且更稳定
    print("Attempting to fetch news via direct API...")
    df = fetch_cls_news_fallback()
    
    if df.empty:
        try:
            print("Direct API failed or returned empty. Fallback to AkShare...")
            df = ak.stock_info_global_cls()
        except Exception as e:
            print(f"AkShare fetch failed: {e}")
            return []
    else:
        print(f"Direct API successful, fetched {len(df)} items.")

    if df is None or df.empty:
        return []

    news_list = df.to_dict('records')
    
    # 过滤关键词
    if keyword:
        filtered_news = []
        keyword_lower = keyword.lower()
        for n in news_list:
            if keyword_lower in str(n.get('标题', '')).lower() or keyword_lower in str(n.get('内容', '')).lower():
                filtered_news.append(n)
        return filtered_news
    
    return news_list

if __name__ == "__main__":
    # Test
    news = fetch_cls_news()
    print(f"Total news fetched: {len(news)}")
    if news:
        print("First item:", news[0])
        print("Last item:", news[-1])
