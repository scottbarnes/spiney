from typing import Final

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Coords, CoordsDB

DB_URI: Final = "sqlite:///:memory:"

test_engine = create_engine(DB_URI)
Base.metadata.create_all(test_engine)
TestSession = sessionmaker(bind=test_engine)

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


def test_insert_coords_db_item() -> None:
    """
    These tests are fairly pointless and mostly test functionality already
    tested by SQLAlchemy's own tests.
    """
    session = TestSession()
    session.add(test_coords_db_google)
    session.add(test_coords_db_washington_dc)
    session.commit()

    all_items = session.query(CoordsDB).all()
    print(vars(all_items[0]))
    assert all_items[0] == test_coords_db_google
    assert all_items[1] == test_coords_db_washington_dc


def test_covert_from_coords_db_to_coords() -> None:
    assert test_coords_db_google.to_dataclass() == test_coords_google
