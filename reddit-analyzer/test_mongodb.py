# test_mongodb.py
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mongodb_connection():
    # Get MongoDB URI from environment variable
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ ERROR: MONGODB_URI not found in environment variables")
        return False
    
    try:
        # Try to connect
        client = MongoClient(mongodb_uri)
        # The ismaster command is cheap and does not require auth
        client.admin.command('ismaster')
        print("✅ Successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(f"❌ ERROR: Could not connect to MongoDB: {e}")
        return False

def test_data_insertion():
    client = test_mongodb_connection()
    if not client:
        return
    
    try:
        # Get database and collection
        db = client['reddit_analytics']
        
        # Create test data
        test_data = {
            'date': datetime.utcnow(),
            'subreddit': 'test',
            'contributors': {
                'test_user': {
                    'post_count': 1,
                    'comment_count': 1,
                    'total_activity': 2,
                    'last_active': datetime.utcnow().strftime('%Y-%m-%d')
                }
            },
            'activity_data': [
                {'hour': '00', 'count': 1}
            ]
        }
        
        # Insert test data
        result = db.daily_stats.insert_one(test_data)
        print("✅ Successfully inserted test data!")
        
        # Verify we can read it back
        retrieved = db.daily_stats.find_one({'_id': result.inserted_id})
        if retrieved:
            print("✅ Successfully retrieved test data!")
        
        # Clean up test data
        db.daily_stats.delete_one({'_id': result.inserted_id})
        print("✅ Successfully cleaned up test data!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        client.close()

def view_recent_data():
    client = test_mongodb_connection()
    if not client:
        return
    
    try:
        db = client['reddit_analytics']
        
        # Get most recent entry
        recent = db.daily_stats.find_one(
            {'subreddit': 'uofm'},
            sort=[('date', -1)]
        )
        
        if recent:
            print("\n📊 Most Recent Data:")
            print(f"Date: {recent['date']}")
            print(f"Number of contributors: {len(recent['contributors'])}")
            print("\nTop Contributors:")
            for username, stats in recent['contributors'].items():
                print(f"\nUsername: {username}")
                print(f"Posts: {stats['post_count']}")
                print(f"Comments: {stats['comment_count']}")
                print(f"Total Activity: {stats['total_activity']}")
                print(f"Last Active: {stats['last_active']}")
        else:
            print("\n❌ No data found for r/uofm")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        client.close()

def check_latest_data():
    client = test_mongodb_connection()
    if not client:
        return
    
    try:
        db = client['reddit_analytics']
        
        # Get most recent entry
        recent = db.daily_stats.find_one(
            {'subreddit': 'uofm'},
            sort=[('date', -1)]
        )
        
        if recent:
            print("\n✅ Latest Data Found:")
            print(f"Date: {recent['date']}")
            print(f"Number of contributors: {len(recent['contributors'])}")
            print("\nActivity Data Sample:")
            for hour_data in recent['activity_data'][:3]:  # Show first 3 hours
                print(f"Hour {hour_data['hour']}: {hour_data['count']} activities")
            
            print("\nTop 3 Contributors:")
            sorted_contributors = sorted(
                recent['contributors'].items(),
                key=lambda x: x[1]['total_activity'],
                reverse=True
            )[:3]
            for username, stats in sorted_contributors:
                print(f"\nu/{username}:")
                print(f"Posts: {stats['post_count']}")
                print(f"Comments: {stats['comment_count']}")
                print(f"Total Activity: {stats['total_activity']}")
        else:
            print("\n❌ No data found for r/uofm")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    print("\n🔍 Checking Latest Data...")
    check_latest_data()
    print("\n🔍 Testing MongoDB Setup...")
    print("\n1. Testing Connection:")
    test_mongodb_connection()
    
    print("\n2. Testing Data Operations:")
    test_data_insertion()
    
    print("\n3. Viewing Recent Data:")
    view_recent_data()