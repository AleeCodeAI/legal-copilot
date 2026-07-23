import pandas as pd 
from database.vectorstore import VectorStore
from pathlib import Path
from timescale_vector.client import uuid_from_time 
from datetime import datetime

# Initialize VectorStore
vec = VectorStore()

data_path = Path(__file__).parents[3] / "data" / "internal_data.json"

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
    metadata = row["metadata"] 
    
    content = row["case_summary"]
    embedding = vec.get_embedding(content)
    return pd.Series(
        {
            "id": str(uuid_from_time(datetime.now())), 
            "metadata": metadata,  
            "contents": content,
            "embedding": embedding,
        }
    )

result = prepare_record(data.iloc[0])  # Test the function with the first row
print(result.metadata) # Print the metadata to verify that the preview is included if it exists

records_df = data.apply(prepare_record, axis=1)
print(records_df.iloc[0]["metadata"])  

# Create tables and insert data
vec.create_tables(table_type="internal")
vec.create_index(table_type="internal")  # DiskAnnIndex
vec.create_keyword_search_index(table_type="internal")  # GIN Index
vec.upsert(records_df, table_type="internal")