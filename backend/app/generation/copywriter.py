"""
AIDA-structured copywriter using Claude.
Every generated copy follows: Attention → Interest → Desire → Action.
Each platform has specific constraints enforced at generation time.
"""

import json
import logging

import anthropic

from app.config import settings
from app.planner.platform_rules import PLATFORM_RULES, check_compliance

logger = logging.getLogger(__name__)

BASE_AIDA_SYSTEM = """你是资深社交媒体文案师，所有内容必须严格遵循 AIDA 模型结构：
- [A] Attention（吸引注意）：第一句/标题必须在3秒内抓住用户注意力，引发好奇或强烈共鸣
- [I] Interest（激发兴趣）：点出用户痛点或产品核心亮点，让用户想继续读
- [D] Desire（引发欲望）：描述具体使用场景、效果、情感价值，让用户产生渴望
- [A] Action（行动号召）：结尾明确告诉用户下一步该做什么

语气自然真实，避免硬广感。输出 JSON 格式。"""

PLATFORM_COPY_PROMPTS = {
    "instagram": """生成一条 Instagram 帖子文案，严格遵循 AIDA 结构和平台规范。

平台规范：
- 总字数 ≤ 2200 字符
- 开头150字内包含核心信息（超出部分被折叠）
- 最多 5 个高度相关标签（不要堆砌无关标签）
- 可使用英中双语
- 禁止帖子中放链接

AIDA 要求：
[A] 开头1-2行：爆炸性 hook，让用户停止滑动（反常识、数字、强烈问题）
[I] 中段：用 emoji 分点，展开痛点或亮点
[D] 具体场景/效果/情感，有画面感
[A] 结尾 CTA：「保存备用 👇」「你试过吗？评论告诉我」「关注获取更多」

输出 JSON（3个变体）：
{
  "variants": [
    {
      "copy_attention": "[A] hook 内容",
      "copy_interest": "[I] 正文内容",
      "copy_desire": "[D] 欲望描述",
      "copy_action": "[A] CTA",
      "full_copy": "完整文案（含换行和emoji）",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
      "hook_type": "question|statistic|contrast|story"
    }
  ]
}""",

    "facebook": """生成一条 Facebook 帖子文案，严格遵循 AIDA 结构和平台规范。

平台规范：
- 最佳长度 ≤ 400 字符（更长内容需点击展开）
- 最多 2 个相关标签
- 对话化语气，引发评论互动
- 可以包含号召性问题

AIDA 要求：
[A] 前2行（折叠前可见）：引人好奇的反常识陈述或强烈问题
[I] 简短故事或数据，引发共鸣
[D] 具体价值主张，可感可想象
[A] 引发互动的 CTA：「你觉得呢？」「留言分享你的经历」「点赞如果你也有同感」

输出 JSON（3个变体）：
{
  "variants": [
    {
      "copy_attention": "[A] hook 内容",
      "copy_interest": "[I] 正文内容",
      "copy_desire": "[D] 欲望描述",
      "copy_action": "[A] CTA",
      "full_copy": "完整文案",
      "hashtags": ["#tag1", "#tag2"],
      "hook_type": "question|statistic|contrast|story"
    }
  ]
}""",

    "xiaohongshu": """生成一篇小红书笔记，严格遵循 AIDA 结构和平台规范。

平台规范：
- 标题 ≤ 20 字（中文）
- 正文 ≤ 1000 字
- 3-5 个中文话题标签（#话题格式）
- 禁止任何第三方链接
- 语气个人化：「我」「姐妹们」「宝子」等亲切称呼
- 使用 emoji 增加可读性和分段感

AIDA 要求：
[A] 标题（≤20字）：数字/疑问/反转，如「我用了1个月才发现这件事...」「同款你买了吗？」
[I] 开篇：引出使用场景或发现契机，「我真的没想到」「姐妹们，这个真的绝了」
[D] 核心内容：具体效果/步骤/感受，有图有真相的文字描述，配合 emoji 分段
[A] 结尾：自然 CTA「先收藏不亏⭐」「你们有同款吗？评论区见」

输出 JSON（3个变体）：
{
  "variants": [
    {
      "title": "标题（≤20字）",
      "copy_attention": "[A] 开篇 hook",
      "copy_interest": "[I] 正文兴趣段",
      "copy_desire": "[D] 欲望/效果段",
      "copy_action": "[A] 结尾 CTA",
      "full_copy": "完整正文（不含标题）",
      "hashtags": ["#话题1", "#话题2", "#话题3"],
      "hook_type": "question|statistic|contrast|personal_story"
    }
  ]
}""",
}


async def generate_copy(
    platform: str,
    theme: str,
    aida_brief: dict | None,
    brand_voice: str,
    target_audience: str,
    research_context: str = "",
    content_type: str = "image_post",
) -> dict:
    """Generate AIDA-structured copy variants for a given platform."""
    platform_prompt = PLATFORM_COPY_PROMPTS.get(platform)
    if not platform_prompt:
        raise ValueError(f"Unsupported platform: {platform}")

    rules = PLATFORM_RULES.get(platform, {})
    aida_guide = ""
    if aida_brief:
        aida_guide = f"""
基于以下 AIDA 方向创作：
- [A] Attention 方向: {aida_brief.get('attention', '')}
- [I] Interest 方向: {aida_brief.get('interest', '')}
- [D] Desire 方向: {aida_brief.get('desire', '')}
- [A] Action 方向: {aida_brief.get('action', '')}
"""

    user_content = f"""内容主题：{theme}
内容类型：{content_type}
品牌调性：{brand_voice or '专业、真实、有温度'}
目标受众：{target_audience or '25-35岁都市女性'}
{aida_guide}
{"相关调研热点：" + research_context if research_context else ""}

{platform_prompt}"""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=BASE_AIDA_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

    result = json.loads(raw.strip())
    variants = result.get("variants", [])

    # Run compliance check on each variant
    for variant in variants:
        copy_text = variant.get("full_copy", "")
        hashtags = variant.get("hashtags", [])
        title = variant.get("title")
        variant["compliance"] = check_compliance(platform, copy_text, hashtags, title)

    logger.info("Generated %d copy variants for platform=%s theme='%s'", len(variants), platform, theme)
    return {"variants": variants, "platform": platform, "theme": theme}
