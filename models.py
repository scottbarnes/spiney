from dataclasses import dataclass


@dataclass
class Coords:
    """Represents latitude and longitude coordinates."""

    latitude: float
    longitude: float
