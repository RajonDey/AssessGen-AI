"""Embedding-based dedup against our own content bank."""

from __future__ import annotations

import uuid

from app.config import Settings
from app.infrastructure.db.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.profiles import resolve_model
from app.infrastructure.llm.types import LLMRole
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.vector.types import DedupReport, SimilarityHit


class DedupService:
    def __init__(
        self,
        *,
        settings: Settings,
        gateway: LLMGateway,
        embeddings: EmbeddingRepository,
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._embeddings = embeddings
        self._log = get_logger("app.dedup")

    async def check_passage(
        self,
        *,
        run_id: uuid.UUID,
        text: str,
        exclude_target_id: uuid.UUID | None = None,
    ) -> DedupReport:
        model = resolve_model(self._settings.llm_profile, LLMRole.EMBEDDING)
        vector = await self._gateway.embed(run_id=run_id, text=text)
        hits = await self._embeddings.find_similar(
            vector=vector,
            kind="passage_body",
            model_name=model.model_name,
        )

        threshold = self._settings.dedup_reject_similarity
        blocking: list[SimilarityHit] = []
        for target_id, target_type, similarity in hits:
            if exclude_target_id is not None and target_id == exclude_target_id:
                continue
            if similarity >= threshold:
                blocking.append(
                    SimilarityHit(
                        target_id=target_id,
                        target_type=target_type,
                        similarity=similarity,
                    )
                )

        passed = not blocking
        if not passed:
            self._log.warning(
                "quality.dedup.blocked",
                hits=[
                    {
                        "target_id": str(hit.target_id),
                        "target_type": hit.target_type,
                        "similarity": hit.similarity,
                    }
                    for hit in blocking
                ],
                threshold=threshold,
            )
        return DedupReport(passed=passed, hits=tuple(blocking), threshold=threshold)
