"""
Content calendar generator using Claude.
Generates N-day content plan with 14 rotating styles — no repeated approach.
Each entry is AIDA-structured. Supports Malay / English / Chinese.
"""

import json
import logging
from datetime import date, timedelta

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# 14 distinct content styles — rotated to guarantee variety
CONTENT_STYLES = [
    {
        "id": "educational",
        "name": "Educational How-to",
        "approach": "Share practical knowledge, steps, or tips. Use numbered format. Teach something valuable.",
    },
    {
        "id": "storytelling",
        "name": "Personal Story",
        "approach": "Tell a relatable mini-story: beginning → challenge → transformation. First-person voice, emotional.",
    },
    {
        "id": "problem_solution",
        "name": "Problem → Solution",
        "approach": "Open with a specific pain point the audience recognizes. Present the product as the direct answer.",
    },
    {
        "id": "social_proof",
        "name": "Results & Transformation",
        "approach": "Showcase a realistic customer journey or before/after result. Focus on the measurable outcome.",
    },
    {
        "id": "behind_scenes",
        "name": "Behind the Scenes",
        "approach": "Reveal the authentic process, craft, or team. Builds trust, humanizes the brand.",
    },
    {
        "id": "feature_spotlight",
        "name": "Feature Deep Dive",
        "approach": "Focus on ONE specific product feature. Go deep with specifics — not a broad overview.",
    },
    {
        "id": "question_debate",
        "name": "Question & Conversation",
        "approach": "Lead with a thought-provoking question designed to spark comments. End by asking for opinions.",
    },
    {
        "id": "lifestyle",
        "name": "Lifestyle & Aspiration",
        "approach": "Paint the ideal life or identity associated with the product. Visual, emotive, aspirational.",
    },
    {
        "id": "before_after",
        "name": "Before vs After",
        "approach": "Dramatically contrast life before and after using the product. Crystal clear transformation.",
    },
    {
        "id": "tips_hacks",
        "name": "Quick Tips & Hacks",
        "approach": "Share 3-5 fast, actionable tips or unexpected product uses. People love saving these posts.",
    },
    {
        "id": "myth_busting",
        "name": "Myth Busting",
        "approach": "Challenge a common misconception. Hook: 'Stop doing X' or 'The truth about Y that nobody tells you'.",
    },
    {
        "id": "emotional",
        "name": "Emotional & Inspirational",
        "approach": "Tap into deeper feelings — belonging, achievement, love, identity. Sincere and motivating.",
    },
    {
        "id": "ugc_authentic",
        "name": "Authentic User Voice",
        "approach": "Write as a real happy customer sharing genuine experience. Casual, unscripted, full of personality.",
    },
    {
        "id": "comparison",
        "name": "Why We're Different",
        "approach": "Compare to the old way or common alternatives. Show the unique advantage clearly.",
    },
]

LANGUAGE_CONFIGS = {
    "english": {
        "system_instruction": "Write in English. Use natural, conversational social media language. No corporate speak.",
        "aida_labels": {
            "attention": "Attention hook (stops the scroll in 3 seconds)",
            "interest": "Interest (pain point or key benefit)",
            "desire": "Desire (specific value, scene, or emotion)",
            "action": "Action (clear CTA)",
        },
        "cta_examples": "Save this / Share with a friend / Comment below / Click the link in bio",
    },
    "malay": {
        "system_instruction": (
            "Tulis dalam Bahasa Melayu. Gaya media sosial Malaysia yang semasa — santai, mesra, autentik. "
            "Boleh campur sedikit Bahasa Inggeris (Manglish) untuk gaya semula jadi. "
            "Gunakan 'anda' atau 'korang' mengikut nada jenama."
        ),
        "aida_labels": {
            "attention": "Perhatian (hentikan tatal dalam 3 saat)",
            "interest": "Minat (titik kesakitan atau manfaat utama)",
            "desire": "Keinginan (nilai spesifik, senario, atau emosi)",
            "action": "Tindakan (CTA yang jelas)",
        },
        "cta_examples": "Simpan dulu / Kongsi dengan kawan / Komen di bawah / Klik link di bio",
    },
    "chinese": {
        "system_instruction": (
            "用中文写作（简体）。使用自然、有亲和力的社交媒体语言风格。"
            "避免企业化语言，要像真实的人在说话。"
            "根据品牌调性选择正式或轻松的语气。"
        ),
        "aida_labels": {
            "attention": "吸引注意（3秒内让用户停止滑动）",
            "interest": "激发兴趣（痛点或核心卖点）",
            "desire": "引发欲望（具体价值、场景或情感）",
            "action": "行动号召（明确CTA）",
        },
        "cta_examples": "收藏备用 / 分享给朋友 / 评论告诉我 / 点击主页链接",
    },
}

CONTENT_TYPE_MIX = {
    "instagram": ["reel", "image_post", "carousel", "image_post", "reel"],
    "facebook": ["video", "image_post", "image_post", "video"],
    "xiaohongshu": ["image_post", "image_post", "video", "image_post"],
}

POSTING_DAYS_PER_WEEK = {
    "instagram": 5,
    "facebook": 4,
    "xiaohongshu": 4,
}


def _assign_styles_for_days(days: int) -> list[str]:
    """Assign a non-repeating rotating style to each day."""
    styles = [s["id"] for s in CONTENT_STYLES]
    result = []
    for i in range(days):
        result.append(styles[i % len(styles)])
    return result


def _get_posting_schedule(platforms: list[str], days: int) -> list[dict]:
    """Generate a schedule of platform posts across N days."""
    schedule = []
    platform_counters = {p: 0 for p in platforms}

    for day in range(1, days + 1):
        for platform in platforms:
            posts_per_week = POSTING_DAYS_PER_WEEK.get(platform, 4)
            day_in_week = (day - 1) % 7
            posts_this_week = posts_per_week

            # Spread posts evenly across the week
            post_days_in_week = [round(7 * i / posts_this_week) for i in range(posts_this_week)]
            if day_in_week in post_days_in_week:
                content_types = CONTENT_TYPE_MIX.get(platform, ["image_post"])
                content_type = content_types[platform_counters[platform] % len(content_types)]
                schedule.append({
                    "day": day,
                    "platform": platform,
                    "content_type": content_type,
                })
                platform_counters[platform] += 1

    return schedule


def _build_prompt(
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    keywords: list[str],
    language: str,
    days: int,
    platforms: list[str],
    start_date: date,
    schedule: list[dict],
    style_assignments: dict,
) -> tuple[str, str]:
    lang_config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["english"])

    styles_map = {s["id"]: s for s in CONTENT_STYLES}

    system = f"""You are an expert social media content strategist. {lang_config["system_instruction"]}

ALL content must strictly follow the AIDA model:
- [{lang_config["aida_labels"]["attention"]}]
- [{lang_config["aida_labels"]["interest"]}]
- [{lang_config["aida_labels"]["desire"]}]
- [{lang_config["aida_labels"]["action"]}] Examples: {lang_config["cta_examples"]}

Critical rules:
1. Every day MUST use the assigned content style — DO NOT repeat the same style approach
2. Each day's content must feel completely different from other days
3. Content for the same platform on different days must NOT repeat themes or angles
4. All copy must be platform-appropriate (Instagram: visual/short hook; Facebook: conversational; XHS: personal/authentic)
5. Output ONLY valid JSON array — no extra text"""

    # Build the day-by-day schedule with style assignments
    schedule_text = ""
    for slot in schedule:
        day = slot["day"]
        style_id = style_assignments.get(day, "educational")
        style = styles_map.get(style_id, CONTENT_STYLES[0])
        scheduled_date = (start_date + timedelta(days=day - 1)).strftime("%Y-%m-%d")
        schedule_text += f"\n- Day {day} ({scheduled_date}) | {slot['platform']} | {slot['content_type']} | STYLE: {style['name']} — {style['approach']}"

    keywords_str = ", ".join(keywords) if keywords else "general brand content"

    user = f"""Create a {days}-day content calendar for brand: "{campaign_name}"

Brand Info:
- Brand voice/tone: {brand_voice or "Professional, warm, authentic"}
- Target audience: {target_audience or "General audience"}
- Key topics/keywords: {keywords_str}
- Content language: {language.upper()}
- Platforms: {", ".join(platforms)}

Day-by-day schedule (you MUST follow each day's assigned style):
{schedule_text}

For EACH entry in the schedule above, output a JSON object:
{{
  "day_number": <number>,
  "scheduled_date": "<YYYY-MM-DD>",
  "platform": "<platform>",
  "content_type": "<type>",
  "content_style": "<style_id>",
  "theme": "<specific topic/theme for this post — must be unique across all days>",
  "aida_brief": {{
    "attention": "<specific hook direction in {language}>",
    "interest": "<what pain point or benefit to address>",
    "desire": "<what value/scene/emotion to evoke>",
    "action": "<specific CTA in {language}>"
  }},
  "suggested_hooks": ["<hook 1 in {language}>", "<hook 2 in {language}>", "<hook 3 in {language}>"],
  "suggested_hashtags": ["#tag1", "#tag2", "#tag3"],
  "content_format": "<e.g. 9:16 vertical video / 1:1 square / 4:5 portrait>"
}}

Output a JSON array of ALL {len(schedule)} entries. Every entry must have completely different theme and hooks from other entries."""

    return system, user


async def generate_calendar(
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    keywords: list[str],
    language: str,
    days: int,
    platforms: list[str],
    start_date: date | None = None,
) -> list[dict]:
    """Generate an N-day AIDA content calendar with non-repeating styles."""
    if start_date is None:
        start_date = date.today()

    language = language.lower() if language else "english"
    if language not in LANGUAGE_CONFIGS:
        language = "english"

    schedule = _get_posting_schedule(platforms, days)

    # Assign rotating styles to each unique day
    unique_days = sorted(set(slot["day"] for slot in schedule))
    style_list = _assign_styles_for_days(len(unique_days))
    style_assignments = {day: style_list[i] for i, day in enumerate(unique_days)}

    system_prompt, user_prompt = _build_prompt(
        campaign_name=campaign_name,
        brand_voice=brand_voice,
        target_audience=target_audience,
        keywords=keywords,
        language=language,
        days=days,
        platforms=platforms,
        start_date=start_date,
        schedule=schedule,
        style_assignments=style_assignments,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    for prefix in ["```json", "```"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    if raw.endswith("```"):
        raw = raw[:-3]

    entries = json.loads(raw.strip())
    logger.info(
        "Generated %d calendar entries for '%s' (%s, %d days)",
        len(entries), campaign_name, language, days,
    )
    return entries


# Backwards-compatible alias used by existing code
async def generate_30_day_calendar(
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    platforms: list[str],
    research_posts: list[dict],
    start_date: date | None = None,
    language: str = "english",
    days: int = 30,
) -> list[dict]:
    return await generate_calendar(
        campaign_name=campaign_name,
        brand_voice=brand_voice,
        target_audience=target_audience,
        keywords=[],
        language=language,
        days=days,
        platforms=platforms,
        start_date=start_date,
    )
