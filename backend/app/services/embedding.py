import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
import structlog

logger = structlog.get_logger()

CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP


class EmbeddingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def chunk_text(self, text: str) -> list[str]:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback: simple split
            words = text.split()
            chunks = []
            for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
                chunk = " ".join(words[i:i + CHUNK_SIZE])
                if len(chunk.strip()) > 50:
                    chunks.append(chunk.strip())
            return chunks

        tokens = enc.encode(text)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = enc.decode(chunk_tokens)

            # Try to split at paragraph boundary
            last_para = chunk_text.rfind("\n\n")
            if last_para > CHUNK_SIZE // 2:
                chunk_text = chunk_text[:last_para]

            stripped = chunk_text.strip()
            if len(stripped) > 50:
                chunks.append(stripped)

            used = len(enc.encode(chunk_text))
            start += max(used - CHUNK_OVERLAP, 1)

        return chunks

    async def embed_text(self, text: str) -> list[float] | None:
        model = settings.resolved_embedding_model
        if not model:
            return None
        try:
            import litellm
            response = await litellm.aembedding(model=model, input=[text])
            return response.data[0]["embedding"]
        except Exception as e:
            logger.debug("embedding_failed", model=model, error=str(e))
            return None

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = settings.resolved_embedding_model
        if not model:
            return [[] for _ in texts]
        try:
            import litellm
            response = await litellm.aembedding(model=model, input=texts)
            return [item["embedding"] for item in response.data]
        except Exception as e:
            logger.warning("embed_batch_failed", model=model, error=str(e))
            return [[] for _ in texts]
