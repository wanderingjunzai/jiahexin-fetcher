import yt_dlp

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

def search_youtube(keyword, limit=10, proxy=None):
    """
    Searches YouTube for videos matching the keyword using yt-dlp.
    Returns a list of dictionaries containing title and url.
    """
    print(f"Searching YouTube for: '{keyword}' (limit: {limit})")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'noplaylist': True,
    }
    
    if proxy:
        print(f"Using proxy: {proxy}")
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ytsearchN:keyword searches for N videos
            search_query = f"ytsearch{limit}:{keyword}"
            result = ydl.extract_info(search_query, download=False)
            
            videos = []
            if 'entries' in result:
                for entry in result['entries']:
                    duration_raw = entry.get('duration')
                    videos.append({
                        'title': entry.get('title', 'No Title'),
                        'url': entry.get('url', 'No Link'), 
                        'duration': format_duration(duration_raw),
                        'channel': entry.get('uploader', 'Unknown')
                    })
                    
            # Normalize links if they are just IDs
            for v in videos:
                if 'youtube.com' not in v['url'] and 'youtu.be' not in v['url']:
                    v['url'] = f"https://www.youtube.com/watch?v={v['url']}"
                    
            return videos
            
    except Exception as e:
        print(f"Error searching YouTube with yt-dlp: {e}")
        return []

if __name__ == "__main__":
    # Test
    vids = search_youtube("Python programming", limit=3)
    for v in vids:
        print(v)
