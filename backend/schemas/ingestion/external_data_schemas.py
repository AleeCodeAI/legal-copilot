from typing import List

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    page_number: str | None = Field(
        default=None,
        description="Page number where the chunk originates."
    )
    headings: List[str] = Field(
        default_factory=list,
        description="Hierarchy of headings associated with the chunk."
    )
    filename: str = Field(
        description="Name of the source document."
    )


class Chunk(BaseModel):
    chunk_id: str = Field(
        description="Unique identifier for the chunk."
    )
    text: str = Field(
        description="Text content of the chunk."
    )
    metadata: ChunkMetadata = Field(
        description="Metadata associated with the chunk."
    )