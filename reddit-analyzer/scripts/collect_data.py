import os
import praw
from datetime import datetime, timedelta
from pymongo import MongoClient
from collections import defaultdict
from dotenv import load_dotenv 

load_dotenv()

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent="script:reddit_analyzer:v1.0 (by /u/SnooTigers930)"
)

# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['reddit_analytics']

def get_activity_times(subreddit_name, timeframe='week'):
    subreddit = reddit.subreddit(subreddit_name)
    activity_hours = defaultdict(int)
    
    try:
        # Count post times
        for submission in subreddit.top(time_filter=timeframe, limit=200):
            hour = datetime.fromtimestamp(submission.created_utc).hour
            activity_hours[hour] += 1
        
        # Count comment times
        for submission in subreddit.top(time_filter=timeframe, limit=100):
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:20]:
                if comment.author:
                    hour = datetime.fromtimestamp(comment.created_utc).hour
                    activity_hours[hour] += 1
        
        # Format for storage
        formatted_data = []
        for hour in range(24):
            formatted_data.append({
                'hour': str(hour).zfill(2),
                'count': activity_hours.get(hour, 0)
            })
        
        return formatted_data
    
    except Exception as e:
        print(f"Error in get_activity_times: {e}")
        return []

def get_top_contributors(subreddit_name, limit=3, timeframe='week'):
    subreddit = reddit.subreddit(subreddit_name)
    contributors = {}
    
    # Calculate cutoff time
    now = datetime.now()
    cutoff_time = now - timedelta(days=7)
    
    try:
        # Fetch recent submissions
        for submission in subreddit.new(limit=500):
            submission_time = datetime.fromtimestamp(submission.created_utc)
            if submission_time < cutoff_time:
                continue
            
            if not submission.author:
                continue
            
            author_name = submission.author.name
            
            if author_name not in contributors:
                contributors[author_name] = {
                    'post_count': 1,
                    'comment_count': 0,
                    'total_activity': 1,
                    'last_active': submission_time.strftime('%Y-%m-%d')
                }
            else:
                contributors[author_name]['post_count'] += 1
                contributors[author_name]['total_activity'] += 1
                if submission_time > datetime.strptime(contributors[author_name]['last_active'], '%Y-%m-%d'):
                    contributors[author_name]['last_active'] = submission_time.strftime('%Y-%m-%d')

        # Fetch comments
        for submission in subreddit.new(limit=200):
            if datetime.fromtimestamp(submission.created_utc) < cutoff_time:
                continue
                
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                if not comment.author:
                    continue
                
                comment_time = datetime.fromtimestamp(comment.created_utc)
                if comment_time < cutoff_time:
                    continue

                author_name = comment.author.name
                
                if author_name not in contributors:
                    contributors[author_name] = {
                        'post_count': 0,
                        'comment_count': 1,
                        'total_activity': 1,
                        'last_active': comment_time.strftime('%Y-%m-%d')
                    }
                else:
                    contributors[author_name]['comment_count'] += 1
                    contributors[author_name]['total_activity'] += 1
                    if comment_time > datetime.strptime(contributors[author_name]['last_active'], '%Y-%m-%d'):
                        contributors[author_name]['last_active'] = comment_time.strftime('%Y-%m-%d')

        # Sort and limit
        sorted_contributors = dict(
            sorted(
                contributors.items(),
                key=lambda x: x[1]['total_activity'],
                reverse=True
            )[:limit]
        )

        return sorted_contributors

    except Exception as e:
        print(f"Error in get_top_contributors: {e}")
        return {}

def store_data():
    subreddit = 'uofm'
    collection_date = datetime.utcnow()
    
    # Get data
    contributors = get_top_contributors(subreddit)
    activity_data = get_activity_times(subreddit)
    
    # Store in MongoDB
    analytics_data = {
        'date': collection_date,
        'contributors': contributors,
        'activity_data': activity_data,
        'subreddit': subreddit
    }
    
    # Use the date as an identifier for upsert
    db.daily_stats.update_one(
        {'date': collection_date.strftime('%Y-%m-%d')},
        {'$set': analytics_data},
        upsert=True
    )

if __name__ == '__main__':
    store_data()