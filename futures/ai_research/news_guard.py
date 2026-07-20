import urllib.request
import json
import datetime
import pandas as pd

class NewsGuard:
    def __init__(self):
        self.last_fetch_date = None
        self.red_folder_times = [] # List of pandas datetime objects in UTC
        self.cache_valid = False
        
    def fetch_calendar(self):
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            self.red_folder_times = []
            for event in data:
                if event.get('country') == 'USD' and event.get('impact') == 'High':
                    # Parse ISO8601 date to pandas UTC
                    event_time = pd.to_datetime(event.get('date'), utc=True)
                    self.red_folder_times.append(event_time)
            
            self.cache_valid = True
            print(f"📰 NewsGuard: Successfully cached {len(self.red_folder_times)} High-Impact USD events for this week.")
        except Exception as e:
            print(f"⚠️ NewsGuard Error fetching calendar: {e}")
            self.cache_valid = False
            
    def is_standby_window(self, current_time: pd.Timestamp) -> bool:
        """
        Takes current time (must be localized or convertible to UTC).
        Returns True if we are within +/- 10 minutes of a Red Folder USD event.
        """
        # Ensure current_time is UTC for comparison
        if current_time.tzinfo is None:
            # Assume naive times are EST (US/Eastern) for safety based on the rest of the bot
            # But wait, ai_live_server uses naive datetimes (Time obj). 
            # We'll just convert everything to naive EST for comparison
            pass
            
        current_date = current_time.date()
        real_now = datetime.datetime.now().date()
        
        # Disable Live News Guard for Historical Backtesting
        if current_date < real_now - datetime.timedelta(days=7):
            return False
            
        if self.last_fetch_date != current_date:
            self.fetch_calendar()
            self.last_fetch_date = current_date
            
        if not self.cache_valid:
            return False
            
        # Standardize current time to UTC for safe comparison
        if current_time.tzinfo is None:
            current_time = current_time.tz_localize('US/Eastern').tz_convert('UTC')
        else:
            current_time = current_time.tz_convert('UTC')
            
        for event_time in self.red_folder_times:
            # event_time is already UTC
            time_diff = abs((current_time - event_time).total_seconds())
            if time_diff <= 600: # 10 minutes (600 seconds)
                return True
                
        return False

# Global Singleton
news_guard = NewsGuard()
