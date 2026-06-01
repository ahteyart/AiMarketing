"""
Aggregates and scores research posts across all platforms.
Normalizes engagement scores for cross-platform comparison.
"""

import logging
from collections import defaultdict

from app.research.base import RawPost

logger = logging.getLogger(__name__)


def score_and_rank(posts: list[RawPost]) -> list[RawPost]:
    """Compute engagement_score for each post and sort descending."""
    for post in posts:
        score = post.engagement_score()
        post.raw_metadata["computed_engagement_score"] = score
    return sorted(posts, key=lambda p: p.engagement_score(), reverse=True)


def extract_trending_topics(posts: list[RawPost], top_n: int = 10) -> list[dict]:
    """
    Extract the most common hashtags/topics across all posts,
    weighted by post engagement.
    """
    topic_scores: dict[str, float] = defaultdict(float)
    topic_counts: dict[str, int] = defaultdict(int)

    for post in posts:
        score = post.engagement_score()
        for tag in post.hashtags or []:
            tag = tag.lower().strip().lstrip("#")
            if tag and len(tag) > 1:
                topic_scores[tag] += score
                topic_counts[tag] += 1

    topics = [
        {
            "hashtag": tag,
            "total_engagement_score": round(score, 4),
            "post_count": topic_counts[tag],
            "avg_engagement": round(score / topic_counts[tag], 4),
        }
        for tag, score in topic_scores.items()
    ]
    topics.sort(key=lambda x: x["total_engagement_score"], reverse=True)
    return topics[:top_n]


def deduplicate(posts: list[RawPost]) -> list[RawPost]:
    """Remove duplicate posts by (platform, external_id)."""
    seen = set()
    unique = []
    for post in posts:
        key = (post.platform, post.external_id)
        if key not in seen:
            seen.add(key)
            unique.append(post)
    return unique
