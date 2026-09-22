import urllib.request
import re
from youtube_transcript_api import YouTubeTranscriptApi
import json

def get_dutchy_videos():
    query = 'Dutchy+ICT+AMD+power+of+3'
    url = f'https://www.youtube.com/results?search_query={query}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')

    video_ids = re.findall(r'"videoId":"([^"]+)"', html)
    unique_ids = list(dict.fromkeys(video_ids))[:3]

    print(f'Found Top 3 Video IDs: {unique_ids}')

    for vid in unique_ids:
        print(f'\n========================================')
        print(f'--- Digesting Video ID: {vid} ---')
        try:
            transcript = YouTubeTranscriptApi.get_transcript(vid)
            text = ' '.join([t['text'] for t in transcript])
            print(text) 
        except Exception as e:
            print(f'Could not fetch transcript: {e}')

if __name__ == '__main__':
    get_dutchy_videos()
