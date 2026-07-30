from database.vectorstore import VectorStore
from typing import List, Union, Optional

vectorstore = VectorStore()

def search_again_tool(query: str):
    """
    Perform a new hybrid search over the legal knowledge base.

    This tool is intended for use when the currently available search results
    do not contain sufficient information to answer the user's question.
    It searches both the external legal reference database and the internal
    case knowledge database, returning the highest-ranked results from each.

    Args:
        query: A refined or alternative search query describing the legal
            information to retrieve.

    Returns:
        CompleteSearchResponse: A structured response containing the original
        query along with separate ranked search results from the external and
        internal knowledge sources.
    """
    results = vectorstore.complete_search(query=query)
    return results


def read_chunks_tool(
    ids: Union[str, List[str]],
    table_type: str = "external",
    include_neighbors: Optional[bool] = False,
):
    """
    Retrieve the full contents of one or more document chunks.

    Use this tool after identifying relevant chunks from a search. It expands
    the brief search previews into their complete text so the model can inspect
    the full legal context before answering.

    Args:
        ids: One or more unique chunk IDs returned by the search tool.
        table_type: The source database containing the chunks. Must be either
            "external" or "internal".
        include_neighbors: If True, also retrieves the chunks immediately
            before and after each requested chunk to provide additional
            contextual information.

    Returns:
        List[Dict[str, Any]]: A list of retrieved chunk records, including the
        chunk ID, full contents, metadata, and embedding.
    """
    results = vectorstore.get_chunks(
        ids=ids,
        table_type=table_type,
        include_neighbors=include_neighbors,
    )
    return results