from database.session import SessionLocal
from database.models.history_table import HistoryTable

def delete_history(history_id: str) -> bool:
    """
    Delete a history by history_id.
    Returns True if deleted, False if not found.
    """
    with SessionLocal() as db:
        history = db.query(HistoryTable).filter(HistoryTable.history_id == history_id).first()

        if not history:
            return False

        db.delete(history)
        db.commit()
        return True

if __name__ == "__main__":
    history_id = "2c0e72a9-c831-40d8-b3d2-9d3df466f55f"
    did_delete = delete_history(history_id)
    if did_delete:
        print(f"email: {history_id} deleted successfully.")
    else:
        print(f"email: {history_id} not found.")