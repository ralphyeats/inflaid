import pytest
from datetime import datetime, timedelta


def make_posts(n=20, likes=500, comments=25, days_apart=3, hashtags=None, captions=None):
    """Generate n fake posts with consistent timestamps."""
    posts = []
    base = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": captions[i] if captions and i < len(captions) else "skincare routine #skincare",
            "hashtags": hashtags[i] if hashtags and i < len(hashtags) else ["skincare", "beauty"],
            "latestComments": [
                {"text": "Love this product!", "ownerUsername": "user1"},
                {"text": "Where can I buy this?", "ownerUsername": "user2"},
            ],
        })
    return posts


@pytest.fixture
def clean_profile():
    """A healthy beauty influencer profile."""
    return {
        "handle": "@testuser",
        "name": "Test User",
        "followers": 50000,
        "following": 500,
        "posts": make_posts(n=24, likes=1500, comments=75, days_apart=3),
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }


@pytest.fixture
def ghost_profile():
    """A profile with ghost followers (very low engagement for follower count)."""
    return {
        "handle": "@ghostuser",
        "name": "Ghost User",
        "followers": 500000,
        "following": 300,
        "posts": make_posts(n=24, likes=50, comments=2, days_apart=3),
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }
