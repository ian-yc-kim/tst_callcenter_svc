import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from tst_callcenter_svc.app import app
from tst_callcenter_svc.models.base import Base, get_db

from alembic import command
from alembic.config import Config


# DO NOT MODIFY SECTION START
# modifying this section will cause many tests to fail.
# this section is protected by the system.
@pytest.fixture
def session_local():
    # Create an in-memory SQLite database engine
    engine = create_engine('sqlite:///:memory:',
                           connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    # Establish a connection that will be kept open for the duration of the tests
    connection = engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()

    # Run migrations using Alembic on the same connection
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes['connection'] = connection
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        # If migrations fail, fallback to creating tables directly
        connection.execute("PRAGMA foreign_keys=OFF")
        Base.metadata.create_all(bind=connection)
    else:
        # Ensure tables exist even if migrations ran
        Base.metadata.create_all(bind=connection)

    # Return a sessionmaker bound to the connection
    SessionLocal = sessionmaker(bind=connection)
    yield SessionLocal

    # Rollback the transaction and close the connection after tests
    transaction.rollback()
    connection.close()


@pytest.fixture
def db_session(session_local):
    session = session_local()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(session_local):
    def override_session():
        session = session_local()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides[get_db] = get_db
# DO NOT MODIFY SECTION END
