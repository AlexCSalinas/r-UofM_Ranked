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
                                activity_data=latest_data['activity_data'],
                                last_updated=latest_data['date'].strftime('%Y-%m-%d %H:%M UTC'))
        
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