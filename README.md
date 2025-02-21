# Reddit Community Analyzer

A web app that shows who's most active in the University of Michigan subreddit (r/uofm) and when people are most active.

[Check it out here!](https://reddit-analyzer.vercel.app/)

## What it does
- Shows top active users based on their posts and comments
- Charts when people are most active throughout the day
- Updates automatically every day at midnight
- Looks like Reddit 🙂

## How it works
- GitHub Actions collects Reddit data daily
- Data gets stored in MongoDB
- Flask web app displays the data
- Deployed on Vercel for fast loading

## Tech used
- Python (Flask)
- MongoDB
- GitHub Actions
- Reddit API (PRAW)
- Tailwind CSS
- Chart.js

## Local setup
1. Clone the repo
2. Create virtual environment: `python -m venv venv`
3. Activate it: 
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Add your .env file with: