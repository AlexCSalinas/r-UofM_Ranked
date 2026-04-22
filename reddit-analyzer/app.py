from flask import Flask, render_template, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv('FLASK_ENV') == 'development':
    load_dotenv()

app = Flask(__name__)

EASTERN = ZoneInfo('America/New_York')
UTC = ZoneInfo('UTC')


def _to_eastern(dt):
    """Convert a (possibly naive UTC) datetime to America/New_York."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(EASTERN)


def _shift_activity_to_eastern(activity_data):
    """Shift hourly activity buckets from UTC to America/New_York."""
    if not activity_data:
        return []
    now_utc = datetime.now(UTC)
    offset_hours = int(now_utc.astimezone(EASTERN).utcoffset().total_seconds() // 3600)
    buckets = {str(h).zfill(2): 0 for h in range(24)}
    for entry in activity_data:
        try:
            utc_hour = int(entry['hour'])
        except (KeyError, ValueError, TypeError):
            continue
        eastern_hour = (utc_hour + offset_hours) % 24
        buckets[str(eastern_hour).zfill(2)] += entry.get('count', 0)
    return [{'hour': h, 'count': buckets[h]} for h in sorted(buckets.keys())]

def get_db():
    """Initialize MongoDB client with error handling"""
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable is not set")
    return MongoClient(mongodb_uri)

@app.route('/api/activity-data')
def activity_data():
    subreddit = 'uofm'
    client = None
    try:
        client = get_db()
        db = client['reddit_analytics']
        latest_data = db.daily_stats.find_one(
            {'subreddit': subreddit},
            sort=[('date', -1)]
        )
        
        if latest_data and 'activity_data' in latest_data:
            return jsonify(latest_data['activity_data'])
        return jsonify([])
        
    except Exception as e:
        print(f"Error fetching activity data: {e}")
        return jsonify([])
    finally:
        if client:
            client.close()

@app.route('/api/user-stats/<username>')
def user_stats(username):
    """API endpoint to get historical stats for a specific user"""
    subreddit = 'uofm'
    client = None
    try:
        client = get_db()
        db = client['reddit_analytics']
        
        # Get last 7 days of data where this user appears
        user_history = []
        
        # Find the last 7 entries with this user
        cursor = db.daily_stats.find(
            {
                'subreddit': subreddit,
                f'contributors.{username}': {'$exists': True}
            },
            {
                'date': 1,
                f'contributors.{username}': 1
            }
        ).sort('date', -1).limit(7)
        
        for doc in cursor:
            if username in doc.get('contributors', {}):
                stats = doc['contributors'][username]
                user_history.append({
                    'date': doc['date'].strftime('%Y-%m-%d'),
                    'activity': stats.get('total_activity', 0),
                    'rank': stats.get('current_rank', 0),
                    'post_count': stats.get('post_count', 0),
                    'comment_count': stats.get('comment_count', 0)
                })
        
        # Get consistency metrics
        consistency_data = {
            'username': username,
            'history': user_history,
            'streak': len(user_history),  # Days active in a row
            'avg_activity': sum(day['activity'] for day in user_history) / max(1, len(user_history)),
            'avg_rank': sum(day['rank'] for day in user_history) / max(1, len(user_history)) if user_history else 0,
            'best_rank': min([day['rank'] for day in user_history], default=0) if user_history else 0,
            'post_to_comment_ratio': sum(day['post_count'] for day in user_history) / 
                                    max(1, sum(day['comment_count'] for day in user_history)) if user_history else 0
        }
        
        return jsonify(consistency_data)
        
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if client:
            client.close()

# Add to the index route t

@app.route('/')
def index():
    subreddit = 'uofm'
    client = None
    try:
        client = get_db()
        db = client['reddit_analytics']
        latest_data = db.daily_stats.find_one(
            {'subreddit': subreddit},
            sort=[('date', -1)]
        )

        if latest_data:
            return render_template('index.html',
                                contributors=latest_data['contributors'],
                                subreddit=subreddit,
                                activity_data=_shift_activity_to_eastern(latest_data.get('activity_data', [])),
                                last_updated=_to_eastern(latest_data['date']).strftime('%Y-%m-%d %H:%M ET'))

        return render_template('index.html',
                            contributors={},
                            subreddit=subreddit,
                            activity_data=[],
                            last_updated=None)

    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html',
                            contributors={},
                            subreddit=subreddit,
                            activity_data=[],
                            last_updated=None)
    finally:
        if client:
            client.close()