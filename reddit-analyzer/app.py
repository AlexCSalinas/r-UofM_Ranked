from flask import Flask, render_template, jsonify
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv('FLASK_ENV') == 'development':
    load_dotenv()

app = Flask(__name__)

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
        
        # Find rising stars (new users with high activity or users with big rank jumps)
        rising_stars = []
        if latest_data and 'contributors' in latest_data:
            for username, stats in latest_data['contributors'].items():
                # New user with high activity (in top 15)
                if stats.get('position_change') == 'new' and stats.get('current_rank', 99) <= 15:
                    rising_stars.append({
                        'username': username,
                        'reason': 'New user with high activity',
                        'stats': stats
                    })
                # Big rank improvement (moved up at least 5 places)
                elif isinstance(stats.get('position_change'), (int, float)) and stats.get('position_change', 0) >= 5:
                    rising_stars.append({
                        'username': username,
                        'reason': f'Moved up {stats["position_change"]} places',
                        'stats': stats
                    })
                # Long streak (active for at least 5 days)
                elif stats.get('streak', 0) >= 5:
                    rising_stars.append({
                        'username': username,
                        'reason': f'Active for {stats["streak"]} days in a row',
                        'stats': stats
                    })
            
            # Sort by rank and limit to top 5
            rising_stars = sorted(rising_stars, key=lambda x: x['stats'].get('current_rank', 99))[:5]
        
        if latest_data:
            return render_template('index.html',
                                contributors=latest_data['contributors'],
                                rising_stars=rising_stars,
                                subreddit=subreddit,
                                activity_data=latest_data['activity_data'],
                                last_updated=latest_data['date'].strftime('%Y-%m-%d %H:%M UTC'))
        
        return render_template('index.html',
                            contributors={},
                            rising_stars=[],
                            subreddit=subreddit,
                            activity_data=[],
                            last_updated=None)
                            
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html',
                            contributors={},
                            rising_stars=[],
                            subreddit=subreddit,
                            activity_data=[],
                            last_updated=None)
    finally:
        if client:
            client.close()