"""
AIDA-structured copywriter using Claude.
Supports Malay / English / Chinese with platform-specific rules.

Two modes:
- Full mode: generates 3 complete variants (hook + body) when no hook is pre-selected
- Body-only mode: hook already chosen by user, generates 2 body variants ([I][D][A] only)
  → ~40% cheaper in tokens
"""

import json
import logging

import anthropic

from app.config import settings
from app.planner.platform_rules import PLATFORM_RULES, check_compliance

logger = logging.getLogger(__name__)

LANGUAGE_SYSTEM_PROMPTS = {
    "english": (
        "You are an expert social media copywriter. Write in natural, conversational English. "
        "No corporate speak. Every post MUST follow the AIDA framework:\n"
        "- [A] Attention: First line stops the scroll in 3 seconds — bold claim, surprising stat, or emotional hook\n"
        "- [I] Interest: Address the core pain point or key benefit — make them want to keep reading\n"
        "- [D] Desire: Paint a vivid, specific picture of the value — make them feel they need this\n"
        "- [A] Action: End with a clear, direct CTA that tells them exactly what to do\n"
        "Output JSON only."
    ),
    "malay": (
        "Anda adalah pakar penulis kandungan media sosial. Tulis dalam Bahasa Melayu yang semasa dan santai. "
        "Boleh campur sedikit Bahasa Inggeris (Manglish) untuk gaya Malaysia yang natural. "
        "Setiap post MESTI ikut model AIDA:\n"
        "- [A] Perhatian: Baris pertama hentikan pengguna tatal dalam 3 saat — dakwaan berani, fakta mengejutkan, atau hook emosi\n"
        "- [I] Minat: Tuju titik kesakitan atau manfaat utama — buat mereka mahu terus baca\n"
        "- [D] Keinginan: Lukiskan gambaran spesifik nilai produk — buat mereka rasa perlu ini\n"
        "- [A] Tindakan: Akhiri dengan CTA yang jelas (Simpan / Kongsi / Komen / Klik link)\n"
        "Output JSON sahaja."
    ),
    "chinese": (
        "你是专业社交媒体文案师。用自然、有亲和力的中文写作（简体）。不要企业化语言，要像真实的人在说话。"
        "每篇内容必须严格遵循AIDA模型：\n"
        "- [A] 吸引注意：第一句在3秒内让用户停止滑动——大胆主张、意外数据或情感钩子\n"
        "- [I] 激发兴趣：触及核心痛点或关键卖点——让他们想继续阅读\n"
        "- [D] 引发欲望：描绘价值的具体生动画面——让他们感到需要这个\n"
        "- [A] 行动号召：以清晰直接的CTA结尾（收藏/分享/评论/点击）\n"
        "只输出JSON。"
    ),
}

PLATFORM_COPY_RULES = {
    "instagram": {
        "max_chars": 2200,
        "optimal_chars": 150,
        "max_hashtags": 5,
        "notes": "First 150 chars are visible before 'more'. Use emojis to break up text. Hashtags at the end only.",
    },
    "facebook": {
        "max_chars": 400,
        "optimal_chars": 200,
        "max_hashtags": 2,
        "notes": "Conversational tone. Designed to generate comments. End with a question to boost engagement.",
    },
    "xiaohongshu": {
        "max_chars": 1000,
        "title_max": 20,
        "max_hashtags": 5,
        "notes": "Title ≤20 Chinese chars. Personal, authentic diary-style tone. No external links. Use emojis and line breaks.",
    },
}


async def generate_aida_copy(
    platform: str,
    theme: str,
    aida_brief: dict,
    content_style: str,
    language: str = "english",
    brand_voice: str = "",
    target_audience: str = "",
    selected_hook: str | None = None,
) -> dict:
    """
    Generate AIDA copy. If selected_hook is provided, only generates body ([I][D][A])
    using that hook as the fixed [A] Attention — saves ~40% tokens.
    """
    language = language.lower() if language else "english"
    if language not in LANGUAGE_SYSTEM_PROMPTS:
        language = "english"

    system = LANGUAGE_SYSTEM_PROMPTS[language]
    platform_rules = PLATFORM_COPY_RULES.get(platform, PLATFORM_COPY_RULES["instagram"])

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    if selected_hook:
        # Body-only mode: hook is already chosen, generate 2 body variants
        # Safely escape the hook for JSON embedding
        escaped_hook = json.dumps(selected_hook)[1:-1]  # Remove surrounding quotes

        user = f"""The user has already selected this opening hook for their {platform.upper()} post:

CHOSEN HOOK (copy_attention): "{selected_hook}"

Now write 2 body variations that follow from this hook.
Platform: {platform.upper()} — max {platform_rules.get("max_chars", 2200)} chars, max {platform_rules.get("max_hashtags", 5)} hashtags. {platform_rules.get("notes", "")}

Brand voice: {brand_voice or "Warm, authentic, trustworthy"}
Target audience: {target_audience or "General audience"}
Post theme: {theme}
Content style: {content_style}

AIDA direction:
- [I] Interest: {aida_brief.get("interest", "Highlight the key benefit")}
- [D] Desire: {aida_brief.get("desire", "Create desire for the product")}
- [A] Action: {aida_brief.get("action", "Clear CTA")}

Output JSON with exactly 2 body variants. The chosen hook must be the opening of full_copy:
{{
  "variants": [
    {{
      "copy_attention": "{escaped_hook}",
      "copy_interest": "<[I] body — pain point or benefit>",
      "copy_desire": "<[D] value, scene, or emotion>",
      "copy_action": "<[A] CTA>",
      "full_copy": "<chosen hook>\\n\\n<interest>\\n<desire>\\n\\n<action>",
      "hashtags": ["#tag1", "#tag2"]
    }},
    {{
      "copy_attention": "{escaped_hook}",
      "copy_interest": "<[I] alternative approach — different angle or framing>",
      "copy_desire": "<[D] alternative value proposition or emotional appeal>",
      "copy_action": "<[A] different CTA>",
      "full_copy": "<chosen hook>\\n\\n<alternative interest>\\n<alternative desire>\\n\\n<alternative action>",
      "hashtags": ["#tag3", "#tag4"]
    }}
  ]
}}

IMPORTANT: Write ALL body copy in {language.upper()}. Make the 2 variants distinctly different in their body approach. Return valid JSON only."""

        max_tokens = 3000

    else:
        # Full mode: generate 3 complete variants (hook + body)
        style_note = f"Content style for this post: **{content_style}** — make the approach and hook match this style."

        user = f"""Generate 3 copy variants for this social media post.

Platform: {platform.upper()}
Platform rules: max {platform_rules.get("max_chars", 2200)} chars, max {platform_rules.get("max_hashtags", 5)} hashtags. {platform_rules.get("notes", "")}

Brand voice: {brand_voice or "Warm, authentic, trustworthy"}
Target audience: {target_audience or "General audience"}
Post theme: {theme}
{style_note}

AIDA direction (use these as your creative brief):
- [A] Attention: {aida_brief.get("attention", "Create a scroll-stopping hook")}
- [I] Interest: {aida_brief.get("interest", "Highlight the key benefit")}
- [D] Desire: {aida_brief.get("desire", "Create desire for the product")}
- [A] Action: {aida_brief.get("action", "Clear CTA")}

Output JSON with exactly 3 variants. Each variant must have a DIFFERENT hook type and approach:
{{
  "variants": [
    {{
      "hook_type": "question|statistic|contrast|story|bold_claim",
      "copy_attention": "<[A] hook — first 1-2 lines>",
      "copy_interest": "<[I] body — pain point or benefit>",
      "copy_desire": "<[D] value, scene, or emotion>",
      "copy_action": "<[A] CTA>",
      "full_copy": "<complete formatted post ready to publish>",
      "hashtags": ["#tag1", "#tag2"]
    }}
  ]
}}

IMPORTANT: Write ALL copy in {language.upper()}. Make the 3 variants distinctly different from each other."""

        max_tokens = 3000

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    raw = message.content[0].text.strip()
    for prefix in ["```json", "```"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    if raw.endswith("```"):
        raw = raw[:-3]

    try:
        result = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.error("JSON parse error in copywriter response: %s. Raw response: %s", e, raw[:500])
        raise ValueError(f"Invalid JSON from Claude: {e}") from e
    variants = result.get("variants", [])

    if not variants:
        raise ValueError("No copy variants returned from Claude")

    primary = variants[0]

    return {
        "copy_attention": primary.get("copy_attention", ""),
        "copy_interest": primary.get("copy_interest", ""),
        "copy_desire": primary.get("copy_desire", ""),
        "copy_action": primary.get("copy_action", ""),
        "copy_text": primary.get("full_copy", ""),
        "hashtags": primary.get("hashtags", []),
        "copy_variants": variants,
        "language": language,
        "content_style": content_style,
    }
