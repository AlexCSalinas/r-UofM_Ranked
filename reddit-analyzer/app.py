# app.py
from flask import Flask, render_template
import praw
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

app = Flask(__name__)

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="script:reddit_analyzer:v1.0 (by /u/SnooTigers930)"
)
print(reddit.read_only)  # Should print True

def setup_database():
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS contributors (
            username TEXT PRIMARY KEY,
            post_count INTEGER,
            comment_count INTEGER,
            total_karma INTEGER,
            last_updated TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_top_contributors(subreddit_name, limit=10, timeframe='month'):
    subreddit = reddit.subreddit(subreddit_name)
    contributors = {}
    
    try:
        # Fetch top submissions efficiently
        for submission in subreddit.top(time_filter=timeframe, limit=200):
            if not submission.author:
                continue
            
            author_name = submission.author.name
            
            # Initialize or update contributor's post-related metrics
            if author_name not in contributors:
                contributors[author_name] = {
                    'post_count': 1,
                    'comment_count': 0,
                    'post_karma': submission.score,
                    'comment_karma': 0,
                    'last_active': submission.created_utc,
                    'awards_received': 0
                }
            else:
                contributors[author_name]['post_count'] += 1
                contributors[author_name]['post_karma'] += submission.score
            
            # Aggregate awards more accurately
            contributors[author_name]['awards_received'] += sum(
                award.get('count', 1) for award in getattr(submission, 'all_awardings', [])
            )
        
        # Efficiently fetch comments
        for submission in subreddit.top(time_filter=timeframe, limit=100):
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:20]:  # Limit comments per submission
                if not comment.author:
                    continue
                
                author_name = comment.author.name
                
                if author_name not in contributors:
                    contributors[author_name] = {
                        'post_count': 0,
                        'comment_count': 1,
                        'post_karma': 0,
                        'comment_karma': comment.score,
                        'last_active': comment.created_utc,
                        'awards_received': 0
                    }
                else:
                    contributors[author_name]['comment_count'] += 1
                    contributors[author_name]['comment_karma'] += comment.score
                
                # Aggregate comment awards
                contributors[author_name]['awards_received'] += sum(
                    award.get('count', 1) for award in getattr(comment, 'all_awardings', [])
                )
        
        # Final calculations
        for author, data in contributors.items():
            # More accurate last active time
            data['total_karma'] = data['post_karma'] + data['comment_karma']
            data['engagement_score'] = (
                data['post_karma'] * 1.5 + 
                data['comment_karma'] + 
                data['awards_received'] * 10
            )
            data['last_active'] = datetime.fromtimestamp(data['last_active']).strftime('%Y-%m-%d')

        # Sort and limit contributors
        sorted_contributors = dict(
            sorted(
                contributors.items(), 
                key=lambda x: x[1]['engagement_score'], 
                reverse=True
            )[:limit]
        )

        return sorted_contributors
        
    except Exception as e:
        print(f"Error in get_top_contributors: {e}")
        return {}

@app.route('/')
def index():
    subreddit = 'uofm'
    print("Getting top contributors...")  # Debug print
    top_contributors = get_top_contributors(subreddit)
    return render_template('index.html',
                         contributors=top_contributors,
                         subreddit=subreddit)

if __name__ == '__main__':
    app.run(debug=True)