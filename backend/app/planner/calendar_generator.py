"""
30-day content calendar generator using Claude.
Takes research data + campaign brief → structured 30-day plan per platform.
"""

import json
import logging
from datetime import date, timedelta

import anthropic

from app.config import settings
from app.planner.platform_rules import PLATFORM_RULES

logger = logging.getLogger(__name__)

CONTENT_MIX_RATIOS = {
    "instagram": {
        "image_post": 0.35,
        "carousel": 0.25,
        "reel": 0.30,
        "story": 0.10,
    },
    "facebook": {
        "image_post": 0.40,
        "video": 0.30,
        "link_post": 0.20,
        "carousel": 0.10,
    },
    "xiaohongshu": {
        "image_post": 0.65,
        "video": 0.35,
    },
}

POSTING_SCHEDULE = {
    "instagram": 5,   # posts/week
    "facebook": 4,
    "xiaohongshu": 4,
}


def _build_calendar_prompt(
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    platforms: list[str],
    research_summary: str,
    start_date: date,
) -> tuple[str, str]:
    platform_details = ""
    for p in platforms:
        rules = PLATFORM_RULES.get(p, {})
        platform_details += f"\n**{rules.get('display_name', p)}:**\n"
        platform_details += f"  - Posting frequency: {rules.get('posting_frequency', 'N/A')}\n"
        platform_details += f"  - Content types: {', '.join(rules.get('content_types', []))}\n"
        platform_details += f"  - Content pillars: {', '.join(rules.get('content_pillars', []))}\n"
        platform_details += f"  - Language: {rules.get('language_notes', '')}\n"

    system = """你是顶级社交媒体内容策略师，专精小红书、Instagram 和 Facebook 的内容规划。
你必须：
1. 严格遵守每个平台的内容规则和社区准则
2. 基于提供的调研热点数据制定计划
3. 确保内容类型多样化（教育型、娱乐型、产品型、互动型）
4. 所有文案结构遵循 AIDA 模型（Attention → Interest → Desire → Action）
5. 输出严格的 JSON 格式

输出 JSON 数组，每个元素代表一个日历条目：
{
  "day_number": 1,
  "platform": "instagram",
  "content_type": "reel",
  "theme": "内容主题描述",
  "aida_brief": {
    "attention": "标题/开头 hook 的方向",
    "interest": "核心内容方向",
    "desire": "情感/价值诉求",
    "action": "具体 CTA"
  },
  "suggested_hooks": ["hook 1", "hook 2", "hook 3"],
  "suggested_hashtags": ["#tag1", "#tag2"],
  "content_format": "9:16 竖版视频",
  "content_pillar": "lifestyle"
}"""

    user = f"""为品牌「{campaign_name}」制定30天内容日历。

**品牌信息：**
- 品牌声音/调性：{brand_voice or '专业、温暖、真实'}
- 目标受众：{target_audience or '25-35岁都市女性'}
- 目标平台：{', '.join(platforms)}

**平台规范：**
{platform_details}

**调研热点数据摘要（近期高互动内容趋势）：**
{research_summary}

**日历起始日期：** {start_date.strftime('%Y-%m-%d')}

**要求：**
- 覆盖30天
- 按每个平台的最佳发布频次分配（Instagram: 约5次/周，Facebook: 4次/周，小红书: 4次/周）
- 内容类型按以下比例混合：
  - Instagram: 35% 图文 + 25% 轮播 + 30% Reel + 10% Story
  - Facebook: 40% 图文 + 30% 视频 + 20% 链接帖 + 10% 轮播
  - 小红书: 65% 图文笔记 + 35% 视频笔记
- 前7天侧重话题热点追踪，8-14天产品/服务深度展示，15-21天用户共鸣/UGC风，22-30天互动+复盘+预告
- 每个条目提供3个候选 hook（标题/开头）

输出完整的 JSON 数组，包含每个平台30天内所有帖子条目。"""

    return system, user


async def generate_30_day_calendar(
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    platforms: list[str],
    research_posts: list[dict],
    start_date: date | None = None,
) -> list[dict]:
    """Call Claude to generate a 30-day content calendar."""
    if start_date is None:
        start_date = date.today()

    research_summary = _summarize_research(research_posts)
    system_prompt, user_prompt = _build_calendar_prompt(
        campaign_name, brand_voice, target_audience, platforms, research_summary, start_date
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

    entries = json.loads(raw.strip())

    # Attach actual scheduled_date to each entry
    for entry in entries:
        day_offset = entry.get("day_number", 1) - 1
        entry["scheduled_date"] = (start_date + timedelta(days=day_offset)).isoformat()

    logger.info("Generated %d calendar entries for campaign '%s'", len(entries), campaign_name)
    return entries


def _summarize_research(research_posts: list[dict]) -> str:
    """Convert research post records into a concise summary for Claude."""
    if not research_posts:
        return "暂无调研数据，请基于通用的行业趋势和最佳实践进行规划。"

    by_platform: dict[str, list[dict]] = {}
    for post in research_posts:
        p = post.get("platform", "unknown")
        by_platform.setdefault(p, []).append(post)

    summary_parts = []
    for platform, posts in by_platform.items():
        top5 = sorted(posts, key=lambda x: x.get("engagement_score", 0), reverse=True)[:5]
        platform_summary = f"\n**{platform.upper()} 热门内容（按互动率排序）：**"
        for i, post in enumerate(top5, 1):
            caption_snippet = (post.get("caption") or "")[:100]
            tags = ", ".join((post.get("hashtags") or [])[:5])
            score = post.get("engagement_score", 0)
            platform_summary += f"\n{i}. [{score:.2%} 互动率] {caption_snippet}... 标签: {tags}"
        summary_parts.append(platform_summary)

    return "\n".join(summary_parts)
