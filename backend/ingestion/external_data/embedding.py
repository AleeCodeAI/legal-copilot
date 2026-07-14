import pandas as pd 
from database.vectorstore import VectorStore
from pathlib import Path 

# Initialize VectorStore
vec = VectorStore()

data_path = Path(__file__).parents[3] / "data" / "chunks.json"

data = pd.read_json(data_path)

def prepare_record(row):
    """Prepare a record for insertion into the vector store.

    Args:
        row (pandas.Series): A row from the dataset containing a 'text' column.

    Returns:
        pandas.Series: A series containing the prepared record for insertion.

    Note:
        This function uses the current time for the UUID. To use a specific time,
        create a datetime object and use uuid_from_time(your_datetime).
    """
    chunk_id = row["chunk_id"]
    metadata = row["metadata"]
    content = row["text"]
    embedding = vec.get_embedding(content)
    return pd.Series(
        {
            "id": chunk_id,
            "metadata": metadata,
            "contents": content,
            "embedding": embedding,
        }
    )


records_df = data.apply(prepare_record, axis=1)

# Create tables and insert data
vec.create_tables()
vec.create_index()  # DiskAnnIndex
vec.create_keyword_search_index()  # GIN Index
vec.upsert(records_df)