from dataclasses import dataclass
from datetime import datetime
from typing import List
from urllib.parse import urlencode
import requests

from py_jetblue.util import PassengerInfo


@dataclass
class FareEstimate:
    date: datetime
    amount: int
    tax: int # garbage info
    seats: int # never trust this


@dataclass
class JetBlueEstimateResponse:
    currencyCode: str
    outboundFares: List[FareEstimate]
    inboundFares: List[FareEstimate]


class JetBlueEstimate:
    def get_fares(self, source: str, destination: str, departure_month: datetime, passengers: PassengerInfo) -> JetBlueEstimateResponse:
        payload = {
            "origin": source,
            "destination": destination,
            "month": f"{departure_month:%B} {departure_month:%Y}",
            "fareType": "LOWEST",
            "tripType": "RETURN",
            "adult": passengers.adults,
            "child": passengers.children,
            "infant": passengers.infants,
        }
        url = "https://jbrest.jetblue.com/bff/bff-service/bestFares?" + urlencode(payload)
        resp = requests.get(url)
        result = JetBlueEstimateResponse(**resp.json())
        result.outboundFares = [self._make_fare_estimate(i) for i in result.outboundFares]
        result.inboundFares = [self._make_fare_estimate(i) for i in result.inboundFares]
        return result
    
    def _make_fare_estimate(self, obj: dict) -> FareEstimate:
        fare = FareEstimate(**obj)
        fare.date = datetime.strptime(fare.date, "%Y-%m-%d")
        return fare


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Get JetBlue airline prices.")
    parser.add_argument("origin", help="Origin airport.")
    parser.add_argument("destination", help="Destination airport.")
    parser.add_argument(
        "departure_month",
        type=lambda s: datetime.strptime(s, "%Y-%m"),
        help="Departure date from origin airport. YYYY-mm",
    )
    parser.add_argument(
        "--passengers",
        type=int,
        default=1,
        help="Number of adult passengers. default=1",
    )
    parser.add_argument(
        "--children", type=int, default=0, help="Number of child passengers. default=0"
    )

    args = parser.parse_args()
    
    passengers = PassengerInfo(adults=args.passengers, children=args.children)    
    client = JetBlueEstimate()
    resp = client.get_fares(args.origin, args.destination, args.departure_month, passengers)
    
    outbound = {
        fare.date: fare 
        for fare in resp.outboundFares
    }
    inbound = {
        fare.date: fare 
        for fare in resp.inboundFares
    }
    print(f"date \toutbound \tinbound")
    for k,v in outbound.items():
        inbound_amount = inbound[k].amount if k in inbound else '--'
        print(f"{k:%Y-%m-%d} \t${v.amount} \t${inbound_amount}")