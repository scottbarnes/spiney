from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


@dataclass
class Coords:
    """Represents latitude and longitude coordinates."""

    address: str
    latitude: float
    longitude: float
    query: str

    def to_sqlalchemy(self) -> "CoordsDB":
        return CoordsDB(
            address=self.address,
            latitude=self.latitude,
            longitude=self.longitude,
            query=self.query,
        )


class CoordsDB(Base):
    __tablename__ = "coords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    query = Column(String, nullable=False, index=True)
    created = Column(DateTime, default=datetime.now(timezone.utc))
    modified = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dataclass(self) -> Coords:
        """
        Convert the SQLAlchemy model instance to a Coords dataclass
        """
        return Coords(
            address=str(self.address),
            latitude=float(str(self.latitude)),
            longitude=float(str(self.longitude)),
            query=str(self.query),
        )

    def __str__(self) -> str:
        return f"CoordsDB(id={self.id}, query={self.query}, latitude={self.latitude}, longitude={self.longitude})"
