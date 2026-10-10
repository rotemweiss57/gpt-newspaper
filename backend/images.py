"""AI illustrations in the newspaper's house style.

LangChain has no cross-provider image-generation interface, so the art direction (the brief) is
written by the run's LangChain chat model, and the pixels come from an image provider below.
Add a provider by extending `generate_image`.
"""

import base64
import os

from .llm import infer_provider

PHOTOS = "photos"  # use the source's news photo instead of an illustration

# style id -> (label for the UI, art direction for the image model)
IMAGE_STYLES: dict[str, tuple[str, str]] = {
    "ink": (
        "Ink",
        "Editorial ink illustration for a modern broadsheet newspaper: confident hand-drawn linework and "
        "crosshatching, black ink on warm cream paper, a single vermilion red accent, subtle print grain.",
    ),
    "engraving": (
        "Engraving",
        "Classic newspaper engraving: fine stipple and line work like a wood engraving or hedcut, "
        "black ink on cream paper, rich crosshatched shading, timeless and precise.",
    ),
    "risograph": (
        "Risograph",
        "Risograph print: two-color overprint in vermilion and deep blue on cream paper, bold flat shapes, "
        "visible halftone texture and slight misregistration.",
    ),
}

HOUSE_RULES = (
    "A conceptual, symbolic editorial illustration, clearly not a photograph. "
    "No text, letters, numbers, logos or watermarks. No likenesses of real, identifiable people."
)

# Aspect ratio of each image slot in the layouts (width, height)
SLOTS = {"lead": (1536, 960), "wide": (1536, 1024), "thumb": (1024, 768)}


def slot_for(layout: str | None, index: int) -> str:
    if layout == "layout_3" and index == 0:
        return "lead"
    if layout == "layout_2":
        return "thumb"
    return "wide"


def size_for(model: str, slot: str) -> str:
    """gpt-image-2 renders any size (multiples of 16); older models only offer fixed sizes."""
    width, height = SLOTS[slot]
    name = model.split(":", 1)[-1]
    if name.startswith("gpt-image-1") or name.startswith("dall-e"):
        return "1536x1024"
    return f"{width}x{height}"


def image_prompt(brief: str, style: str, slot: str) -> str:
    framing = "wide landscape" if slot != "thumb" else "landscape"
    return (
        f"{brief}\n\nStyle: {IMAGE_STYLES[style][1]}\n{HOUSE_RULES}\n"
        f"Composition: {framing} framing, main subject near the center so it survives cropping."
    )


def image_api_key(image_model: str, chat_model: str, chat_api_key: str | None, image_key: str | None) -> str | None:
    """The key for the image provider: an explicit one, the chat key if it's the same provider, or the env."""
    provider = infer_provider(image_model) or "openai"
    if image_key:
        return image_key
    if chat_api_key and infer_provider(chat_model) == provider:
        return chat_api_key
    return os.getenv("OPENAI_API_KEY") if provider == "openai" else None


async def generate_image(model: str, prompt: str, size: str, api_key: str | None, quality: str = "medium") -> bytes:
    """Render an image and return WebP bytes."""
    provider, _, name = model.rpartition(":")
    if (provider or "openai") != "openai":
        raise ValueError(f"Unsupported image provider “{provider}”. Supported: openai")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, timeout=180, max_retries=2)
    result = await client.images.generate(
        model=name,
        prompt=prompt,
        size=size,
        quality=quality,
        output_format="webp",
        output_compression=85,
        n=1,
    )
    return base64.b64decode(result.data[0].b64_json)
