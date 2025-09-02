import pytest
from pathlib import Path
from tradingagents.utils.database import Database

@pytest.fixture
def db():
    base_dir = Path(__file__).resolve().parents[1]
    db_dir = base_dir / "data" / "sqlite"
    db_dir.mkdir(parents=True, exist_ok=True)
    path = str(db_dir / "app_email.db")
    db = Database(path)
    yield db
    db.close()

def test_add_users(db):
    db.execute([
        {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
        {"id": 2, "name": "Jane Doe", "email": "jane.doe@example.com"},
    ])

