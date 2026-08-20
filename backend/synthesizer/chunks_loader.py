from database.vectorstore import VectorStore

store = VectorStore()

def get_chunks(ids: list[str]):

     internal_chunks: list[dict] = []
     external_chunks: list[dict] = []

     for id in ids:
          if id.startswith("internal_"):
               chunk = store.get_chunks(ids=[id], table_type="internal")
               internal_chunks.append(
                    {
                         "id": str(chunk[0]["id"]),
                         "content": chunk[0]["contents"],
                         "case_id": chunk[0]["metadata"]["case_id"],
                         "attorneys": chunk[0]["metadata"]["attorneys"],
                         "date": chunk[0]["metadata"]["date"]
                    }
               )

          elif id.startswith("external_"):
               chunk = store.get_chunks(ids=[id], table_type="external")
               external_chunks.append(
                    {
                         "id": str(chunk[0]["id"]),
                         "content": chunk[0]["contents"],
                         "headings": chunk[0]["metadata"]["headings"],
                         "page_number": chunk[0]["metadata"]["page_number"],
                    }
               )

     return internal_chunks, external_chunks