"""ORM model registry — import all models so Alembic sees metadata."""

from app.infrastructure.db.models.content import Item, ItemVersion, Passage, PassageVersion
from app.infrastructure.db.models.embedding import Embedding
from app.infrastructure.db.models.organization import Organization, User
from app.infrastructure.db.models.prompt import PromptVersion
from app.infrastructure.db.models.provenance import AgentInvocation, GenerationRun
from app.infrastructure.db.models.quality import QualityCheck, Review
from app.infrastructure.db.models.reference import ReferenceDocument
from app.infrastructure.db.models.topic import Tag, Topic

__all__ = [
    "AgentInvocation",
    "Embedding",
    "GenerationRun",
    "Item",
    "ItemVersion",
    "Organization",
    "Passage",
    "PassageVersion",
    "PromptVersion",
    "QualityCheck",
    "ReferenceDocument",
    "Review",
    "Tag",
    "Topic",
    "User",
]
