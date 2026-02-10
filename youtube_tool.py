import yt_dlp
from datetime import datetime, timedelta
import time
import concurrent.futures

def format_duration(seconds):
    """Formats duration in seconds to MM:SS or HH:MM:SS."""
    if not seconds or not isinstance(seconds, (int, float)):
        return "N/A"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_number(num):
    if not num:
        return "0"
    num = int(num)
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    if num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def get_video_details(video_url, proxy=None):
    """Fetches full metadata for a single video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'force_generic_extractor': False,
    }
    if proxy:
        ydl_opts['proxy'] = proxy
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'url': video_url,
                'duration_sec': info.get('duration'),
                'duration': format_duration(info.get('duration')),
                'channel': info.get('uploader') or info.get('channel') or 'Unknown',
                'view_count_raw': info.get('view_count') or 0,
                'view_count': format_number(info.get('view_count')),
                'like_count_raw': info.get('like_count') or 0,
                'like_count': format_number(info.get('like_count')),
                'timestamp': info.get('timestamp') or (time.mktime(time.strptime(info.get('upload_date'), '%Y%m%d')) if info.get('upload_date') else None),
                'description': info.get('description') or ""
            }
    except Exception as e:
        print(f"Error fetching details for {video_url}: {e}")
        return None

def search_youtube(keyword, limit=10, sort_by="relevance", upload_date_filter="all", duration_filter="all", proxy=None):
    """
    Searches YouTube for videos matching the keyword with advanced filters.
    """
    print(f"Searching YouTube: '{keyword}' (sort: {sort_by}, date: {upload_date_filter}, duration: {duration_filter})")
    
    # Step 1: Flat search to get candidates
    search_prefix = "ytsearch"
    if sort_by == "date":
        search_prefix = "ytsearchdate"
    
    # Fetch more to allow for filtering
    fetch_limit = 40 if duration_filter == "all" else 80
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'noplaylist': True,
    }
    if proxy:
        ydl_opts['proxy'] = proxy
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"{search_prefix}{fetch_limit}:{keyword}"
            result = ydl.extract_info(search_query, download=False)
            
            candidates = []
            if 'entries' in result:
                for entry in result['entries']:
                    if not entry: continue
                    
                    v_id = entry.get('id')
                    url = entry.get('url') or f"https://www.youtube.com/watch?v={v_id}"
                    duration = entry.get('duration') or 0
                    
                    # Pre-filter by duration if possible
                    if duration_filter != "all":
                        if duration_filter == "under15" and duration >= 900: continue
                        if duration_filter == "15to30" and (duration < 900 or duration >= 1800): continue
                        if duration_filter == "30to60" and (duration < 1800 or duration >= 3600): continue
                        if duration_filter == "60to120" and (duration < 3600 or duration >= 7200): continue
                        if duration_filter == "over120" and duration < 7200: continue
                    
                    candidates.append(url)

            # Limit number of detailed fetches to stay relatively fast
            candidates = candidates[:25] 
            
            # Step 2: Fetch detailed info in parallel
            videos = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(get_video_details, url, proxy): url for url in candidates}
                for future in concurrent.futures.as_completed(future_to_url):
                    res = future.result()
                    if res:
                        videos.append(res)

            # Step 3: Local Filtering & Sorting
            filtered_videos = []
            now_ts = time.time()
            
            for v in videos:
                # Date Filter
                if upload_date_filter != "all" and v['timestamp']:
                    days_ago = (now_ts - v['timestamp']) / (24 * 3600)
                    if upload_date_filter == "week" and days_ago > 7: continue
                    if upload_date_filter == "3months" and days_ago > 90: continue
                    if upload_date_filter == "6months" and days_ago > 180: continue
                    if upload_date_filter == "year" and days_ago > 365: continue
                    if upload_date_filter == "2years" and days_ago > 730: continue
                
                # Format publish date for display
                v['publish_date'] = datetime.fromtimestamp(v['timestamp']).strftime('%Y-%m-%d') if v['timestamp'] else "Unknown"
                
                filtered_videos.append(v)

            # Sort
            if sort_by == "view_count":
                filtered_videos.sort(key=lambda x: x['view_count_raw'], reverse=True)
            elif sort_by == "like_count": # Mapping "Most Liked" to likes if we have them
                filtered_videos.sort(key=lambda x: x['like_count_raw'], reverse=True)
            elif sort_by == "date":
                filtered_videos.sort(key=lambda x: x['timestamp'] or 0, reverse=True)
            else: # relevance - keep original search order if possible
                # To keep original order, we need to sort by their index in the 'candidates' list
                url_order = {url: i for i, url in enumerate(candidates)}
                filtered_videos.sort(key=lambda x: url_order.get(x['url'], 999))

            return filtered_videos[:limit]
            
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        return []

if __name__ == "__main__":
    # Test
    start_time = time.time()
    vids = search_youtube("AI News", limit=5, sort_by="relevance", upload_date_filter="all")
    for v in vids:
        print(f"{v['publish_date']} | {v['view_count']} | {v['like_count']} | {v['title']}")
    print(f"Time taken: {time.time() - start_time:.2f}s")
