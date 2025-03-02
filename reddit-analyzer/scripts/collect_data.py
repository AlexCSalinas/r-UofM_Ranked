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

# Add this to your store_data() function in collect_data.py

def store_data():
    subreddit = 'uofm'
    collection_date = datetime.utcnow()
    
    # Get data
    contributors = get_top_contributors(subreddit, limit=20)  # Increased to track more users
    activity_data = get_activity_times(subreddit)
    
    # Get previous day's data to calculate position changes
    previous_data = db.daily_stats.find_one(
        {'subreddit': subreddit},
        sort=[('date', -1)]
    )
    
    # Track position changes
    if previous_data and 'contributors' in previous_data:
        # Create sorted list of previous contributors
        prev_contributors = sorted(
            previous_data['contributors'].items(),
            key=lambda x: x[1]['total_activity'],
            reverse=True
        )
        
        # Create a map of username -> previous rank
        prev_ranks = {username: idx + 1 for idx, (username, _) in enumerate(prev_contributors)}
        
        # Update current contributors with position change and streak data
        current_sorted = sorted(
            contributors.items(),
            key=lambda x: x[1]['total_activity'],
            reverse=True
        )
        
        for idx, (username, stats) in enumerate(current_sorted):
            current_rank = idx + 1
            prev_rank = prev_ranks.get(username, 0)  # 0 indicates new user
            
            # Add rank tracking
            contributors[username]['current_rank'] = current_rank
            contributors[username]['previous_rank'] = prev_rank
            
            # Calculate position change
            if prev_rank == 0:
                contributors[username]['position_change'] = 'new'
            else:
                contributors[username]['position_change'] = prev_rank - current_rank
            
            # Add streak information - number of consecutive days user has appeared
            user_streak = 1  # Default to 1 for today
            if username in prev_ranks:
                # Check if user had a streak recorded previously
                if 'streak' in previous_data['contributors'].get(username, {}):
                    user_streak = previous_data['contributors'][username]['streak'] + 1
            
            contributors[username]['streak'] = user_streak
    else:
        # First data collection, set defaults
        for username, stats in contributors.items():
            contributors[username]['current_rank'] = list(contributors.keys()).index(username) + 1
            contributors[username]['previous_rank'] = 0
            contributors[username]['position_change'] = 'new'
            contributors[username]['streak'] = 1
    
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