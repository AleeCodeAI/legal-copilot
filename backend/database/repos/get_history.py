from database.session import SessionLocal
from database.models.history_table import HistoryTable


def get_history() -> list[dict]:
    """
    Function to get all history of searches
    """
    with SessionLocal() as db:
        results = db.query(HistoryTable).all()

        return [
            {
                "history_id": str(history.history_id),
                "query": history.query,
                "answer": history.answer,
                "citations": history.citations
            }
            for history in results
        ]


if __name__ == "__main__":
    import json

    histories = get_history()
    print(json.dumps(histories, indent=2))