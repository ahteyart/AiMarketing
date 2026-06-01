"""
Platform-specific content rules and compliance constraints.
Used by the copywriter and calendar generator to enforce limits.
"""

PLATFORM_RULES: dict[str, dict] = {
    "instagram": {
        "display_name": "Instagram",
        "caption_max_chars": 2200,
        "caption_optimal_chars": 150,
        "hashtags_max": 30,
        "hashtags_optimal": 5,
        "title_field": None,
        "formats": {
            "image_post": {"aspect_ratios": ["1:1", "4:5", "1.91:1"], "recommended": "4:5"},
            "carousel": {"aspect_ratios": ["1:1", "4:5"], "max_slides": 10},
            "reel": {"aspect_ratio": "9:16", "max_duration_s": 90},
            "story": {"aspect_ratio": "9:16", "max_duration_s": 15},
        },
        "content_types": ["image_post", "carousel", "reel", "story"],
        "content_pillars": ["lifestyle", "product showcase", "tutorial/how-to", "UGC style", "behind the scenes"],
        "posting_frequency": "4-5 times/week",
        "best_post_times": ["6-9am", "12-2pm", "7-9pm"],
        "language_notes": "Mix of English and Chinese accepted; English for broader reach",
        "compliance": [
            "Sponsored content must be tagged with #ad or #sponsored",
            "No misleading or false claims",
            "No purchasing of engagement metrics",
            "Sensitive content requires content warning labels",
            "Links only allowed in bio (not post captions)",
        ],
        "aida_tips": {
            "attention": "First 150 chars visible before 'more' — make them count. Use a bold statement, question, or number.",
            "interest": "Use bullet points with emoji, address a pain point",
            "desire": "Describe the feeling/result, use social proof",
            "action": "End with: save for later, comment, tag a friend, or visit bio link",
        },
    },
    "facebook": {
        "display_name": "Facebook",
        "caption_max_chars": 63206,
        "caption_optimal_chars": 400,
        "hashtags_max": 10,
        "hashtags_optimal": 2,
        "title_field": None,
        "formats": {
            "image_post": {"aspect_ratios": ["1.91:1", "1:1"], "recommended": "1.91:1"},
            "video": {"max_duration_min": 240, "recommended_duration_s": 60},
            "carousel": {"max_slides": 10},
            "story": {"aspect_ratio": "9:16", "max_duration_s": 20},
        },
        "content_types": ["image_post", "video", "carousel", "link_post"],
        "content_pillars": ["long-form stories", "product showcase", "community posts", "events", "news"],
        "posting_frequency": "3-4 times/week",
        "best_post_times": ["9-11am", "1-3pm"],
        "language_notes": "Conversational tone, questions drive comments",
        "compliance": [
            "Genuine ad disclosures required for paid partnerships",
            "No misleading health claims",
            "No hate speech or harassment",
            "No buying/selling of regulated items without proper permissions",
            "Political ads require authorization",
        ],
        "aida_tips": {
            "attention": "First 2 lines visible before 'See more' — use a counterintuitive statement or question",
            "interest": "Tell a short story or share surprising data point",
            "desire": "Specific benefits, testimonials, or relatable scenario",
            "action": "Ask a question to drive comments: 'What do you think?' or 'Have you tried this?'",
        },
    },
    "xiaohongshu": {
        "display_name": "小红书 (XHS)",
        "title_max_chars": 20,
        "caption_max_chars": 1000,
        "caption_optimal_chars": 500,
        "hashtags_max": 10,
        "hashtags_optimal": 3,
        "title_field": "title",
        "formats": {
            "image_post": {"aspect_ratio": "3:4", "max_images": 9, "recommended_images": 6},
            "video": {"max_duration_min": 15, "recommended_duration_s": 60},
        },
        "content_types": ["image_post", "video"],
        "content_pillars": ["种草测评 (review/recommend)", "生活方式 (lifestyle)", "教程攻略 (tutorial)", "打卡分享 (check-in)"],
        "posting_frequency": "3-5 times/week",
        "best_post_times": ["7-9am", "12-1pm", "9-11pm"],
        "language_notes": "Chinese primary. Authentic, personal tone. Use 'I', 姐妹, 宝子. Avoid corporate language.",
        "compliance": [
            "Commercial content requires brand partnership application 品牌合作申请",
            "No false or exaggerated efficacy claims 禁止虚假夸大效果",
            "Must disclose #广告 or #品牌合作 for paid content",
            "No external links in notes 禁止第三方链接",
            "No selling products without proper merchant setup",
            "Cosmetic/health claims must be factual and verifiable",
        ],
        "aida_tips": {
            "attention": "Title ≤20 chars: use numbers ('我用了30天'), questions ('你也有这个烦恼吗？'), or contrast ('踩雷后的真实反馈')",
            "interest": "Open with personal discovery story, use 姐妹们/宝子们 to create intimacy",
            "desire": "Specific details: textures, feelings, before/after. Use emoji to break paragraphs.",
            "action": "Natural CTA: '先收藏不亏⭐', '有问题评论区见', '你们有用过同款吗？'",
        },
    },
}


def check_compliance(platform: str, copy_text: str, hashtags: list[str], title: str | None = None) -> dict:
    """Check content against platform rules. Returns compliance report."""
    rules = PLATFORM_RULES.get(platform, {})
    issues = []
    warnings = []

    char_count = len(copy_text) if copy_text else 0
    hashtag_count = len(hashtags) if hashtags else 0

    if platform == "xiaohongshu" and title:
        if len(title) > rules.get("title_max_chars", 20):
            issues.append(f"Title exceeds {rules['title_max_chars']} characters (current: {len(title)})")

    max_chars = rules.get("caption_max_chars", 9999)
    optimal_chars = rules.get("caption_optimal_chars", 400)
    if char_count > max_chars:
        issues.append(f"Caption exceeds max {max_chars} characters (current: {char_count})")
    elif char_count > optimal_chars * 2:
        warnings.append(f"Caption is longer than optimal {optimal_chars} chars for engagement")

    max_tags = rules.get("hashtags_max", 30)
    optimal_tags = rules.get("hashtags_optimal", 5)
    if hashtag_count > max_tags:
        issues.append(f"Too many hashtags: {hashtag_count} (max: {max_tags})")
    elif hashtag_count > optimal_tags * 2:
        warnings.append(f"More hashtags than optimal ({optimal_tags}); may reduce reach on this platform")

    return {
        "platform": platform,
        "passed": len(issues) == 0,
        "char_count": char_count,
        "char_limit": max_chars,
        "optimal_chars": optimal_chars,
        "hashtag_count": hashtag_count,
        "hashtag_limit": max_tags,
        "optimal_hashtags": optimal_tags,
        "issues": issues,
        "warnings": warnings,
    }
