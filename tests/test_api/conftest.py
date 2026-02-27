import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.services.user_service import hash_password

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def client():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Ensure all connections share same in-memory DB
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create a default user for audits (id=1)
    db = TestSession()
    user = User(username="admin", email="admin@test.com", hashed_password=hash_password("admin123"), role="admin")
    db.add(user)
    db.commit()
    db.close()

    with TestClient(app, follow_redirects=True) as c:
        # Log in so that protected UI routes are accessible
        c.post("/login", data={"username": "admin", "password": "admin123", "next": "/"})
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
