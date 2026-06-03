import asyncio
import logging
from typing import Any

import aiohttp

from config import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    AI_TIMEOUT,
    AI_MAX_TOKENS,
)

logger = logging.getLogger("ai")

SYSTEM_PROMPT = """You are Ruxy, a Discord bot assistant for the Rux programming language.
You answer concisely with code snippets using Discord formatting: **bold**, *italic*, __underline__, `code`, ```code blocks```.
For `/what-is <concept>`: explain the Rux equivalent of the concept with a small code snippet.
For `/how-to <task>`: show how to accomplish the task in Rux with code.
Keep responses under 1900 characters. If the concept doesn't exist in Rux, explain the closest alternative."""


async def _openai(prompt: str) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": AI_MAX_TOKENS,
                    "temperature": 0.3,
                },
                timeout=aiohttp.ClientTimeout(total=AI_TIMEOUT),
            ) as resp:
                if resp.status == 429:
                    logger.warning("OpenAI rate-limited")
                    return None
                if resp.status != 200:
                    logger.warning("OpenAI returned %d", resp.status)
                    return None
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except asyncio.TimeoutError:
        logger.warning("OpenAI timed out")
        return None
    except Exception as e:
        logger.warning("OpenAI error: %s", e)
        return None


async def _anthropic(prompt: str) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": AI_MAX_TOKENS,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=aiohttp.ClientTimeout(total=AI_TIMEOUT),
            ) as resp:
                if resp.status == 429:
                    logger.warning("Anthropic rate-limited")
                    return None
                if resp.status != 200:
                    logger.warning("Anthropic returned %d", resp.status)
                    return None
                data = await resp.json()
                return data["content"][0]["text"].strip()
    except asyncio.TimeoutError:
        logger.warning("Anthropic timed out")
        return None
    except Exception as e:
        logger.warning("Anthropic error: %s", e)
        return None


async def _gemini(prompt: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}],
                    "generationConfig": {"maxOutputTokens": AI_MAX_TOKENS, "temperature": 0.3},
                },
                timeout=aiohttp.ClientTimeout(total=AI_TIMEOUT),
            ) as resp:
                if resp.status == 429:
                    logger.warning("Gemini rate-limited")
                    return None
                if resp.status != 200:
                    logger.warning("Gemini returned %d", resp.status)
                    return None
                data = await resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text.strip() or None
    except asyncio.TimeoutError:
        logger.warning("Gemini timed out")
        return None
    except Exception as e:
        logger.warning("Gemini error: %s", e)
        return None


PROVIDERS = [
    ("OpenAI", _openai),
    ("Anthropic", _anthropic),
    ("Gemini", _gemini),
]


async def ask(prompt: str) -> str:
    """Try each AI provider in order until one returns a response. Raises if all fail."""
    errors: list[str] = []
    for name, provider_fn in PROVIDERS:
        result = await provider_fn(prompt)
        if result is not None:
            logger.info("AI response from %s", name)
            return result
        errors.append(name)
    raise RuntimeError(f"All AI providers failed: {', '.join(errors)}")
