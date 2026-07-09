import hashlib
import math
from functools import lru_cache

from app.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None

    def _hash_embedding(self, text: str) -> list[float]:
        dimension = self.settings.embedding_dimension
        vector = [0.0] * dimension
        tokens = [text[i : i + 2] for i in range(max(1, len(text) - 1))]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimension
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.settings.embedding_backend == "hash":
            return [self._hash_embedding(text) for text in texts]
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        result = [vector.tolist() for vector in vectors]
        self._check_dimension(result)
        return result

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _check_dimension(self, vectors: list[list[float]]) -> None:
        expected = self.settings.embedding_dimension
        for vector in vectors:
            if len(vector) != expected:
                raise ValueError(f"向量维度不匹配：模型输出 {len(vector)}，数据库要求 {expected}")


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
