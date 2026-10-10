import logging
import os

from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..images import generate_image, image_api_key, image_prompt, size_for, slot_for
from ..prompts import ILLUSTRATOR_PROMPT
from ..rendering import strip_citations
from ..schemas import IllustrationBrief
from ..state import ArticleState
from .common import chat_model, emit, slugify

logger = logging.getLogger(__name__)


async def illustrator_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    """Commission an illustration in the house style. Any failure falls back to the source photo."""
    ctx = runtime.context
    if not ctx.image_style:
        return {}
    api_key = image_api_key(ctx.image_model, ctx.model, ctx.api_key, ctx.image_api_key)
    if not api_key:
        emit(state, "design", "No OpenAI key for illustrations, using the news photo")
        return {}

    emit(state, "design", "The art director is commissioning an illustration")
    brief: IllustrationBrief = await (ILLUSTRATOR_PROMPT | chat_model(ctx, IllustrationBrief)).ainvoke(
        {"title": state["title"], "summary": strip_citations(state["summary"]), "language": ctx.language}
    )

    slot = slot_for(state.get("layout"), state.get("index", 0))
    try:
        image = await generate_image(
            ctx.image_model,
            image_prompt(brief.prompt, ctx.image_style, slot),
            size_for(ctx.image_model, slot),
            api_key,
            ctx.image_quality,
        )
    except Exception as e:
        logger.warning("Illustration failed for %r", state.get("query"), exc_info=True)
        emit(state, "design", f"Illustration unavailable ({type(e).__name__}), using the news photo")
        return {}

    filename = f"{state.get('index', 0) + 1:02d}-{slugify(state['query'])}.webp"
    os.makedirs(ctx.output_dir, exist_ok=True)
    with open(os.path.join(ctx.output_dir, filename), "wb") as f:
        f.write(image)
    return {"image": filename, "image_alt": brief.alt_text.strip(), "illustrated": True}
