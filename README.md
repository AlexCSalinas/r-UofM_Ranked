# Reddit Community Analyzer

A web app that shows who's most active in the University of Michigan subreddit (r/uofm) and when people are most active.

[Check it out here!](https://reddit-analyzer.vercel.app/)

## What it does
- Shows top active users based on their posts and comments
- Charts when people are most active throughout the day
- Updates automatically every day at midnight

## How it works
- GitHub Actions collects Reddit data daily
- Data gets stored in MongoDB
- Flask web app displays the data
- Deployed on Vercel

## Tech used
- Python (Flask)
- MongoDB
- GitHub Actions
- Reddit API (PRAW)
- Tailwind CSS
- Chart.js

