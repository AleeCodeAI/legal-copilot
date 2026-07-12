import json
from pathlib import Path
from typing import List
from pydantic import BaseModel
from uuid import uuid4

from docling.chunking import HybridChunker
from docling_core.types.doc import DoclingDocument
from tokenizer import OpenAITokenizerWrapper


# =============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ChunkMetadata(BaseModel):
    page_number: str | None = None
    headings: List[str] = []
    filename: str


class Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata


# =============================================================================
# CONFIGURATION
# ============================================================================

MAX_TOKENS = 900


# =============================================================================
# PROCESSING FUNCTIONS
# ============================================================================

def process_document(json_path: Path, filename: str) -> List[Chunk]:
    """Load, chunk, and extract metadata from a Docling document."""
    
    doc = DoclingDocument.load_from_json(json_path)
    
    tokenizer = OpenAITokenizerWrapper()
    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=MAX_TOKENS,
        merge_peers=True
    )
    chunks = list(chunker.chunk(dl_doc=doc))
    
    processed = []
    for _, chunk in enumerate(chunks):
        # Get page number
        page = None
        if chunk.meta and chunk.meta.doc_items:
            for item in chunk.meta.doc_items:
                if item.prov:
                    page = str(item.prov[0].page_no)
                    break
        
        # Get headings
        headings = chunk.meta.headings if chunk.meta and chunk.meta.headings else []
        
        processed.append(
            Chunk(
            chunk_id=f"chunk_{uuid4()}",
            text=chunk.text,
            metadata=ChunkMetadata(
                page_number=page,
                headings=headings,
                filename=filename
            )
        )
        )
    
    return processed


# =============================================================================
# SAVING FUNCTION
# ============================================================================

def save_chunks(chunks: List[Chunk], output_path: Path) -> None:
    """Save chunks to JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([c.model_dump() for c in chunks], f, indent=2, ensure_ascii=False)
    print(f"Saved {len(chunks)} chunks to {output_path}")


if __name__ == "__main__":
    # Paths
    data_dir = Path(__file__).parents[3] / "data"
    input_path = data_dir / "data.json"
    output_path = data_dir / "chunks.json"
    
    # Process
    chunks = process_document(input_path, "2025_Landlord_Tenant_Guide.pdf")
    print(f"Original chunks: {len(chunks)}")
    print(chunks[0].model_dump_json(indent=2, ensure_ascii=False))

    # Save
    save_chunks(chunks, output_path)
    
    # Preview
    if chunks:
        print("\nFirst chunk preview:")
        print(f"  ID: {chunks[0].chunk_id}")
        print(f"  Page: {chunks[0].metadata.page_number}")
        print(f"  Headings: {chunks[0].metadata.headings}")
        print(f"  Text: {chunks[0].text[:100]}...")