from dataclasses import dataclass

@dataclass
class PassengerInfo:
    adults: int
    children: int = 0
    infants: int = 0
