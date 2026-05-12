"""
Shared pytest fixtures for the Bookstore API test suite.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.auth import hash_password
from app import models

# ── In-memory SQLite for tests ────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_bookstore.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(setup_database):
    """Provide a transactional DB session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable data factories ───────────────────────────────────────────────────

@pytest.fixture()
def test_user(db_session) -> models.User:
    """Create and persist a test user."""
    user = models.User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def second_user(db_session) -> models.User:
    user = models.User(
        username="seconduser",
        email="second@example.com",
        hashed_password=hash_password("password456"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client, test_user) -> dict:
    """Return Authorization headers for the test user."""
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_book(db_session, test_user) -> models.Book:
    """Create and persist a sample book."""
    book = models.Book(
        title="Clean Code",
        author="Robert C. Martin",
        isbn="9780132350884",
        price=35.99,
        genre="Programming",
        published_year=2008,
        in_stock=True,
        owner_id=test_user.id,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


@pytest.fixture()
def sample_books(db_session, test_user) -> list[models.Book]:
    """Create a batch of books for list/filter tests."""
    books_data = [
        {"title": "The Pragmatic Programmer", "author": "David Thomas", "isbn": "9780135957059",
         "price": 49.99, "genre": "Programming", "published_year": 2019, "in_stock": True},
        {"title": "Design Patterns", "author": "Gang of Four", "isbn": "9780201633610",
         "price": 54.99, "genre": "Programming", "published_year": 1994, "in_stock": True},
        {"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593",
         "price": 12.99, "genre": "Science Fiction", "published_year": 1965, "in_stock": False},
        {"title": "Foundation", "author": "Isaac Asimov", "isbn": "9780553293357",
         "price": 10.99, "genre": "Science Fiction", "published_year": 1951, "in_stock": True},
        {"title": "Refactoring", "author": "Martin Fowler", "isbn": "9780201485677",
         "price": 44.99, "genre": "Programming", "published_year": 1999, "in_stock": True},
    ]
    books = []
    for data in books_data:
        book = models.Book(**data, owner_id=test_user.id)
        db_session.add(book)
        books.append(book)
    db_session.commit()
    for book in books:
        db_session.refresh(book)
    return books
