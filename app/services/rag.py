import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services.embeddings import get_embedding_service
from app.services.text_chunker import estimate_tokens, split_text


class RAGService:
    def __init__(self) -> None:
        self.embeddings = get_embedding_service()

    def index_document(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        title: str,
        text: str,
        metadata: dict | None = None,
    ) -> Document:
        old_ids = db.scalars(
            select(Document.id).where(
                Document.user_id == user_id,
                Document.source_type == source_type,
                Document.source_id == source_id,
            )
        ).all()
        if old_ids:
            db.execute(delete(Document).where(Document.id.in_(old_ids)))
            db.flush()

        document = Document(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            raw_text=text,
            meta_json=metadata or {},
        )
        db.add(document)
        db.flush()

        chunks = split_text(text)
        vectors = self.embeddings.embed_documents(chunks) if chunks else []
        for index, (content, vector) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    user_id=user_id,
                    chunk_index=index,
                    content=content,
                    token_estimate=estimate_tokens(content),
                    meta_json={"source_type": source_type, **(metadata or {})},
                    embedding=vector,
                )
            )
        db.commit()
        return document

    def retrieve(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[dict]:
        query_vector = self.embeddings.embed_query(query)
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(DocumentChunk, Document.title, Document.source_type, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.user_id == user_id, DocumentChunk.embedding.is_not(None))
        )
        if source_types:
            statement = statement.where(Document.source_type.in_(source_types))
        rows = db.execute(statement.order_by(distance).limit(top_k)).all()
        return [
            {
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "title": title,
                "source_type": source_type,
                "similarity": round(1 - float(row_distance), 4),
            }
            for chunk, title, source_type, row_distance in rows
        ]
