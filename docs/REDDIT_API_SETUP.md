# Reddit API Setup Guide

This guide walks you through obtaining Reddit API credentials (Client ID and Client Secret) needed for the social trends analyzer.

## Step 1: Create a Reddit Account

If you don't have a Reddit account, create one at https://www.reddit.com/register

## Step 2: Create a Reddit Application

1. Go to https://www.reddit.com/prefs/apps
2. Scroll down to the bottom of the page
3. Click **"create another app..."** or **"create app"** button

## Step 3: Fill Out the Application Form

Fill in the following details:

- **Name**: `SocialTrendsBot` (or any name you prefer)
- **Type**: Select **"script"** (this is the appropriate type for server-side applications)
- **Description**: `Real-time social trend and sentiment analyzer` (optional)
- **About URL**: Leave empty or add your project URL
- **Redirect URI**: `http://localhost:8080` (required but not used for script apps)

## Step 4: Get Your Credentials

After creating the app, you'll see a box with your app details:

- **Client ID**: This is the string under your app name (looks like: `abc123def456ghi789`)
- **Client Secret**: This is the "secret" field (looks like: `xyz789_secret_abc123`)

**Important**: The Client Secret is only shown once when you create the app. If you lose it, you'll need to create a new app.

## Step 5: Configure Your Application

Copy the credentials to your `.env` file:

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=SocialTrendsBot/1.0
```

### User Agent Format

The User Agent should follow this format:
```
<platform>:<app ID>:<version string> (by /u/<reddit username>)
```

For example:
```
SocialTrendsBot/1.0 (by /u/yourusername)
```

Or simpler (as used in the code):
```
SocialTrendsBot/1.0
```

## Step 6: Verify Your Setup

Test your credentials by running the fetcher once:

```bash
python -m src.fetcher.main --once
```

If successful, you should see output like:
```
Fetched X new posts from r/technology
Fetched X new posts from r/programming
...
```

## Troubleshooting

### "Invalid Client" Error

- Double-check your Client ID and Secret in `.env`
- Ensure there are no extra spaces or quotes
- Verify the app type is set to "script"

### "403 Forbidden" Error

- Check your User Agent format
- Ensure your Reddit account is verified (check email)
- Some subreddits may have restrictions

### Rate Limiting

Reddit API has rate limits:
- **60 requests per minute** per application
- The fetcher includes automatic rate limiting (1 second delay between subreddits)

If you hit rate limits:
- Reduce the number of subreddits
- Increase `FETCH_INTERVAL_SEC` in `.env`
- Use multiple Reddit apps with different credentials

## Reddit API Terms of Service

Important points to remember:

1. **Rate Limits**: Respect the 60 requests/minute limit
2. **User Agent**: Always include a descriptive User Agent
3. **Data Usage**: Don't redistribute Reddit content without permission
4. **Privacy**: Don't store or share personal user information
5. **Attribution**: When displaying Reddit content, attribute it properly

Read the full API terms: https://www.reddit.com/wiki/api

## Alternative: Using Reddit's OAuth2 (Advanced)

For production or higher rate limits, you can use OAuth2:

1. Set app type to "web app" instead of "script"
2. Implement OAuth2 flow to get access tokens
3. Use access tokens for API requests

For MVP, the "script" type is sufficient and simpler.

## Security Best Practices

1. **Never commit `.env` to version control** (already in `.gitignore`)
2. **Use environment variables in production** (not `.env` files)
3. **Rotate credentials periodically**
4. **Use different credentials for dev/staging/prod**
5. **Store secrets in a secrets manager** (AWS SSM, HashiCorp Vault, etc.)

## Example `.env` File

```env
# Reddit API Credentials
REDDIT_CLIENT_ID=abc123def456ghi789
REDDIT_CLIENT_SECRET=xyz789_secret_abc123
REDDIT_USER_AGENT=SocialTrendsBot/1.0

# Subreddits to monitor (comma-separated)
SUBREDDITS=technology,programming,python,webdev

# Elasticsearch
ES_HOST=localhost
ES_PORT=9200

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Token (change in production!)
API_TOKEN=dev-token-change-in-prod
```

## Need Help?

- Reddit API Documentation: https://www.reddit.com/dev/api
- Reddit API Subreddit: https://www.reddit.com/r/redditdev
- PRAW Documentation: https://praw.readthedocs.io/

