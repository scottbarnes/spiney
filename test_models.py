from typing import Final, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Coords, CoordsDB

import pytest

DB_URI: Final = "sqlite:///:memory:"

test_coords_google = Coords(
    address="1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
    latitude=37.4224053,
    longitude=-122.0842161,
    query="1600 Amphitheatre Parkway, Mountain View, CA",
)

test_coords_db_google = CoordsDB(
    address="1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
    latitude=37.4224053,
    longitude=-122.0842161,
    query="1600 Amphitheatre Parkway, Mountain View, CA",
)

test_coords_washington_dc = Coords(
    address="Washington, DC 20001, USA", latitude=38.912068, longitude=-77.0190228, query="20001"
)

test_coords_db_washington_dc = CoordsDB(
    address="Washington, DC 20001, USA", latitude=38.912068, longitude=-77.0190228, query="20001"
)


@pytest.fixture()
def get_db() -> Generator[Session, None, None]:
    test_engine = create_engine(DB_URI)
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)
    yield TestSession()


def test_insert_coords_db_item(get_db) -> None:
    """
    These tests are fairly pointless and mostly test functionality already
    tested by SQLAlchemy's own tests.
    """
    session = get_db
    session.add(test_coords_db_google)
    session.add(test_coords_db_washington_dc)
    session.commit()

    all_items = session.query(CoordsDB).all()
    assert all_items[0] == test_coords_db_google
    assert all_items[1] == test_coords_db_washington_dc


def test_covert_from_coords_db_to_coords() -> None:
    assert test_coords_db_google.to_dataclass() == test_coords_google
