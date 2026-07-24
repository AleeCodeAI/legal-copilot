import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import cohere
import pandas as pd
import psycopg
from configs.settings import get_settings
from openai import OpenAI
from timescale_vector import client

from schemas import CompleteSearchResponse, SearchResultItem

# Define the allowed table types for type hinting
TableType = Literal["internal", "external"]


class VectorStore:
    """A class for managing vector operations and database interactions across internal and external tables."""

    def __init__(self):
        """Initialize the VectorStore with settings, OpenAI client, and Timescale Vector clients."""
        self.settings = get_settings()
        self.openrouter_client = OpenAI(
            api_key=self.settings.openrouter.api_key,
            base_url=self.settings.openrouter.base_url,
        )
        self.embedding_model = self.settings.openrouter.embedding_model
        self.cohere_client = cohere.ClientV2(api_key=self.settings.cohere.api_key)
        self.vector_settings = self.settings.vector_store

        # Initialize clients for both external and internal tables
        self.clients = {
            "external": client.Sync(
                self.settings.database.service_url,
                self.vector_settings.external_table_name,
                self.vector_settings.embedding_dimensions,
                time_partition_interval=self.vector_settings.time_partition_interval,
            ),
            "internal": client.Sync(
                self.settings.database.service_url,
                self.vector_settings.internal_table_name,
                self.vector_settings.embedding_dimensions,
                time_partition_interval=self.vector_settings.time_partition_interval,
            ),
        }

    def _get_vec_client(self, table_type: TableType) -> client.Sync:
        """
        Helper method to resolve the target Timescale Vector client.

        Args:
            table_type: The target table ("internal" or "external").

        Returns:
            The corresponding Timescale Vector client instance.
        """
        if table_type not in self.clients:
            raise ValueError(
                f"Invalid table_type: {table_type}. Choose 'internal' or 'external'."
            )
        return self.clients[table_type]

    def _get_table_name(self, table_type: TableType) -> str:
        """
        Helper method to resolve the target table name from settings.

        Args:
            table_type: The target table ("internal" or "external").

        Returns:
            The string name of the table in the database.
        """
        return (
            self.vector_settings.internal_table_name
            if table_type == "internal"
            else self.vector_settings.external_table_name
        )

    def create_keyword_search_index(self, table_type: TableType = "external"):
        """
        Create a GIN index for keyword search if it doesn't exist.

        Args:
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
        """
        table_name = self._get_table_name(table_type)
        index_name = f"idx_{table_name}_contents_gin"
        create_index_sql = f"""
        CREATE INDEX IF NOT EXISTS {index_name}
        ON {table_name} USING gin(to_tsvector('english', contents));
        """
        try:
            with psycopg.connect(self.settings.database.service_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(create_index_sql)
                    conn.commit()
                    logging.info(
                        f"GIN index '{index_name}' created or already exists on '{table_name}'."
                    )
        except Exception as e:
            logging.error(f"Error while creating GIN index on {table_name}: {str(e)}")

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.

        Args:
            text: The input text to generate an embedding for.

        Returns:
            A list of floats representing the embedding.
        """
        text = text.replace("\n", " ")
        start_time = time.time()
        embedding = (
            self.openrouter_client.embeddings.create(
                input=[text],
                model=self.embedding_model,
            )
            .data[0]
            .embedding
        )
        elapsed_time = time.time() - start_time
        logging.info(f"Embedding generated in {elapsed_time:.3f} seconds")
        return embedding

    def create_tables(self, table_type: TableType = "external") -> None:
        """
        Create the necessary tables in the database.

        Args:
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
        """
        self._get_vec_client(table_type).create_tables()

    def create_index(self, table_type: TableType = "external") -> None:
        """
        Create the StreamingDiskANN index to speed up similarity search.

        Args:
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
        """
        self._get_vec_client(table_type).create_embedding_index(client.DiskAnnIndex())

    def drop_index(self, table_type: TableType = "external") -> None:
        """
        Drop the StreamingDiskANN index in the database.

        Args:
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
        """
        self._get_vec_client(table_type).drop_embedding_index()

    def upsert(self, df: pd.DataFrame, table_type: TableType = "external") -> None:
        """
        Insert or update records in the database from a pandas DataFrame.

        Args:
            df: A pandas DataFrame containing the data to insert or update.
                Expected columns: id, metadata, contents, embedding
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
        """
        records = df.to_records(index=False)
        vec_client = self._get_vec_client(table_type)
        table_name = self._get_table_name(table_type)

        vec_client.upsert(list(records))
        logging.info(f"Inserted {len(df)} records into {table_name}")

    def semantic_search(
        self,
        query: str,
        table_type: TableType = "external",
        limit: int = 5,
        metadata_filter: Union[dict, List[dict]] = None,
        predicates: Optional[client.Predicates] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        return_dataframe: bool = True,
    ) -> Union[List[Tuple[Any, ...]], pd.DataFrame]:
        """
        Query the vector database for similar embeddings based on input text.

        More info:
            https://github.com/timescale/docs/blob/latest/ai/python-interface-for-pgvector-and-timescale-vector.md

        Args:
            query: The input text to search for.
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
            limit: The maximum number of results to return.
            metadata_filter: A dictionary or list of dictionaries for equality-based metadata filtering.
            predicates: A Predicates object for complex metadata filtering.
            time_range: A tuple of (start_date, end_date) to filter results by time.
            return_dataframe: Whether to return results as a DataFrame (default: True).

        Returns:
            Either a list of tuples or a pandas DataFrame containing the search results.
        """
        query_embedding = self.get_embedding(query)

        start_time = time.time()

        search_args = {
            "limit": limit,
        }

        if metadata_filter:
            search_args["filter"] = metadata_filter

        if predicates:
            search_args["predicates"] = predicates

        if time_range:
            start_date, end_date = time_range
            search_args["uuid_time_filter"] = client.UUIDTimeRange(start_date, end_date)

        vec_client = self._get_vec_client(table_type)
        results = vec_client.search(query_embedding, **search_args)
        elapsed_time = time.time() - start_time

        self._log_search_time(f"Vector ({table_type})", elapsed_time)

        if return_dataframe:
            return self._create_dataframe_from_results(results)
        else:
            return results

    def _create_dataframe_from_results(
        self,
        results: List[Tuple[Any, ...]],
    ) -> pd.DataFrame:
        """
        Create a pandas DataFrame from the search results, preserving the full metadata dictionary.

        Args:
            results: A list of tuples containing the search results.

        Returns:
            A pandas DataFrame containing the formatted search results.
        """
        if not results:
            return pd.DataFrame(
                columns=["id", "metadata", "content", "embedding", "distance"]
            )

        df = pd.DataFrame(
            results, columns=["id", "metadata", "content", "embedding", "distance"]
        )

        # Convert id to string for better readability
        df["id"] = df["id"].astype(str)

        return df

    def delete(
        self,
        table_type: TableType = "external",
        ids: List[str] = None,
        metadata_filter: dict = None,
        delete_all: bool = False,
    ) -> None:
        """Delete records from the vector database.

        Args:
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
            ids (List[str], optional): A list of record IDs to delete.
            metadata_filter (dict, optional): A dictionary of metadata key-value pairs to filter records for deletion.
            delete_all (bool, optional): A boolean flag to delete all records.

        Raises:
            ValueError: If no deletion criteria are provided or if multiple criteria are provided.
        """
        if sum(bool(x) for x in (ids, metadata_filter, delete_all)) != 1:
            raise ValueError(
                "Provide exactly one of: ids, metadata_filter, or delete_all"
            )

        vec_client = self._get_vec_client(table_type)
        table_name = self._get_table_name(table_type)

        if delete_all:
            vec_client.delete_all()
            logging.info(f"Deleted all records from {table_name}")
        elif ids:
            vec_client.delete_by_ids(ids)
            logging.info(f"Deleted {len(ids)} records from {table_name}")
        elif metadata_filter:
            vec_client.delete_by_metadata(metadata_filter)
            logging.info(f"Deleted records matching metadata filter from {table_name}")

    def _log_search_time(self, search_type: str, elapsed_time: float) -> None:
        """
        Log the time taken for a search operation.

        Args:
            search_type: The type of search performed (e.g., 'Vector', 'Keyword').
            elapsed_time: The time taken for the search operation in seconds.
        """
        logging.info(f"{search_type} search completed in {elapsed_time:.3f} seconds")

    def keyword_search(
        self,
        query: str,
        table_type: TableType = "external",
        limit: int = 5,
        return_dataframe: bool = True,
    ) -> Union[List[Tuple[str, str, float]], pd.DataFrame]:
        """
        Perform a keyword search on the contents of the vector store, preserving the full metadata dictionary.

        Args:
            query: The search query string.
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
            limit: The maximum number of results to return. Defaults to 5.
            return_dataframe: Whether to return results as a DataFrame. Defaults to True.

        Returns:
            Either a list of tuples or a pandas DataFrame containing the search results.

        Example:
            results = vector_store.keyword_search("shipping options", table_type="external")
        """
        table_name = self._get_table_name(table_type)

        search_sql = f"""
        SELECT id, contents, metadata, ts_rank_cd(to_tsvector('english', contents), query) as rank
        FROM {table_name}, websearch_to_tsquery('english', %s) query
        WHERE to_tsvector('english', contents) @@ query
        ORDER BY rank DESC
        LIMIT %s
        """

        start_time = time.time()

        # Create a new connection using psycopg3
        with psycopg.connect(self.settings.database.service_url) as conn:
            with conn.cursor() as cur:
                cur.execute(search_sql, (query, limit))
                results = cur.fetchall()

        elapsed_time = time.time() - start_time
        self._log_search_time(f"Keyword ({table_type})", elapsed_time)

        if return_dataframe:
            if not results:
                return pd.DataFrame(columns=["id", "content", "metadata", "rank"])

            df = pd.DataFrame(results, columns=["id", "content", "metadata", "rank"])
            df["id"] = df["id"].astype(str)

            return df
        else:
            return results

    def hybrid_search(
        self,
        query: str,
        table_type: TableType = "external",
        keyword_k: int = 5,
        semantic_k: int = 5,
        rerank: bool = False,
        top_n: int = 5,
    ) -> pd.DataFrame:
        """
        Perform a hybrid search combining keyword and semantic search results,
        with optional reranking using Cohere.

        Args:
            query: The search query string.
            table_type (TableType, optional): The target table ("internal" or "external"). Defaults to "external".
            keyword_k: The number of results to return from keyword search. Defaults to 5.
            semantic_k: The number of results to return from semantic search. Defaults to 5.
            rerank: Whether to apply Cohere reranking. Defaults to True.
            top_n: The number of top results to return after reranking. Defaults to 5.

        Returns:
            A pandas DataFrame containing the combined search results with a 'search_type' column.

        Example:
            results = vector_store.hybrid_search("shipping options", table_type="internal", keyword_k=3, semantic_k=3, rerank=True, top_n=5)
        """
        # Perform keyword search
        keyword_results = self.keyword_search(
            query, table_type=table_type, limit=keyword_k, return_dataframe=True
        )
        keyword_results["search_type"] = "keyword"
        keyword_results = keyword_results[["id", "content", "metadata", "search_type"]]

        # Perform semantic search
        semantic_results = self.semantic_search(
            query, table_type=table_type, limit=semantic_k, return_dataframe=True
        )
        semantic_results["search_type"] = "semantic"
        semantic_results = semantic_results[["id", "content", "metadata", "search_type"]]

        # Combine results
        combined_results = pd.concat(
            [keyword_results, semantic_results], ignore_index=True
        )

        # Remove duplicates, keeping the first occurrence (which maintains the original order)
        combined_results = combined_results.drop_duplicates(subset=["id"], keep="first")

        if rerank:
            return self._rerank_results(query, combined_results, top_n)

        return combined_results

    def _rerank_results(
        self, query: str, combined_results: pd.DataFrame, top_n: int
    ) -> pd.DataFrame:
        """
        Rerank the combined search results using Cohere, preserving metadata dictionaries.

        Args:
            query: The original search query.
            combined_results: DataFrame containing the combined keyword and semantic search results.
            top_n: The number of top results to return after reranking.

        Returns:
            A pandas DataFrame containing the reranked results.
        """
        documents = combined_results["content"].tolist()

        # Call Cohere rerank API
        rerank_response = self.cohere_client.v2.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=documents,
            top_n=top_n,
        )

        # Build reranked results
        reranked_results = []
        for result in rerank_response.results:
            idx = result.index
            reranked_results.append(
                {
                    "id": combined_results.iloc[idx]["id"],
                    "content": documents[idx],
                    "metadata": combined_results.iloc[idx]["metadata"],
                    "search_type": combined_results.iloc[idx]["search_type"],
                    "relevance_score": result.relevance_score,
                }
            )

        reranked_df = pd.DataFrame(reranked_results)
        return reranked_df.sort_values("relevance_score", ascending=False)

    def complete_search(self, query: str) -> CompleteSearchResponse:
        """
        Perform a complete hybrid search across external and internal tables,
        returning separate result lists wrapped in a structured Pydantic model.

        Args:
            query (str): The search query string.

        Returns:
            CompleteSearchResponse: A Pydantic object containing separated
            and validated results for both 'external' and 'internal' sources.
        """
        # 1. Execute hybrid searches on both tables
        external_df = self.hybrid_search(
            query=query,
            table_type="external",
            keyword_k=5,
            semantic_k=5,
            rerank=True,
            top_n=5,
        )

        internal_df = self.hybrid_search(
            query=query,
            table_type="internal",
            keyword_k=5,
            semantic_k=5,
            rerank=True,
            top_n=5,
        )

        # 2. Safely parse external results
        external_items: List[SearchResultItem] = []
        if not external_df.empty:
            for record in external_df.to_dict(orient="records"):
                try:
                    external_items.append(SearchResultItem(**record))
                except Exception as e:
                    logging.warning(f"Failed to parse external search record: {e}")

        # 3. Safely parse internal results
        internal_items: List[SearchResultItem] = []
        if not internal_df.empty:
            for record in internal_df.to_dict(orient="records"):
                try:
                    internal_items.append(SearchResultItem(**record))
                except Exception as e:
                    logging.warning(f"Failed to parse internal search record: {e}")

        # 4. Return structured response
        return CompleteSearchResponse(
            query=query,
            external_results=external_items,
            internal_results=internal_items,
        )