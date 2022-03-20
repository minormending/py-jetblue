from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Union, Dict
import asyncio
from pyppeteer.browser import Browser
from pyppeteer.page import Page
from pyppeteer import launch
from urllib.parse import urlencode
from enum import Enum


@dataclass
class PassengerInfo:
    adults: int
    children: int = 0
    infants: int = 0


@dataclass
class JetBluePuppetResponse:
    currency: str
    countryCode: str
    fareGroup: List[Dict]
    itinerary: List[Dict]
    isTransatlanticRoute: bool
    dategroup: str  # ignore
    stopsFilter: str  # ignore
    programName: str  # ignore
    sessionId: str  # ignore


@dataclass
class FlightLeg:
    departureAirport: str
    arrivalAirport: str
    departureTerminal: str


@dataclass
class Segment:
    id: str
    source: str
    destination: str
    aircraft: str
    aircraftCode: str
    stops: int
    depart: datetime
    arrive: datetime
    flightno: str
    operatingAirlineCode: str
    operatingAirlineName: str
    throughFlightLegs: List[Dict]  # FlightLeg


@dataclass
class Itinerary:
    id: str
    source: str
    destination: str
    depart: datetime
    arrive: datetime
    isOverNightFlight: bool
    segments: List[Dict]  # Segment


class FareStatus(Enum):
    unknown = 0
    not_offered = 1
    available = 2


@dataclass
class FareInfo:
    itineraryID: str
    price: float
    cabinclass: str
    refundable: bool
    status: FareStatus


@dataclass
class JetBlueResponse:
    fares: Dict[str, List[FareInfo]]
    intineraries: List[Itinerary]


class JetBluePuppet:
    browser: Browser = None
    debug: bool = False

    def __init__(self, debug=False) -> None:
        self.debug = debug

    async def _get_page(self) -> Page:
        if not self.browser:
            self.browser: Browser = await launch()
        page: Page = await self.browser.newPage()
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36"
        )
        return page

    async def get_fares_json(
        self,
        source: str,
        destination: str,
        departure_date: datetime,
        return_date: datetime,
        passengers: PassengerInfo,
        timeout: timedelta = None,
    ) -> JetBluePuppetResponse:
        payload = {
            "from": source.upper(),
            "to": destination.upper(),
            "depart": f"{departure_date:%Y-%m-%d}",
            "return": f"{return_date:%Y-%m-%d}",
            "isMultiCity": False,
            "noOfRoute": 1,
            "lang": "en",
            "adults": passengers.adults,
            "children": passengers.children,
            "infants": passengers.infants,
            "sharedMarket": False,
            "roundTripFaresFlag": False,
            "usePoints": False,
        }
        url = "https://www.jetblue.com/booking/flights?" + urlencode(payload)

        try:
            timeout = timeout or timedelta(seconds=30)
            page: Page = await self._get_page()
            await page.goto(url)
            resp = await page.waitForResponse(
                lambda r: "outboundLFS" in r.url, timeout=timeout.seconds * 1000
            )
            contents = await resp.json()
            return JetBluePuppetResponse(**contents)
        except Exception as ex:
            if self.debug:
                debug_filename = "error_page_load_url.png"
                await page.screenshot(path=debug_filename)
            raise ex

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()


class JetBlueParser:
    @classmethod
    def parse(self, payload: JetBluePuppetResponse) -> JetBlueResponse:
        result: JetBlueResponse = JetBlueResponse(fares={}, intineraries=[])
        for fareGroup in payload.fareGroup:
            code = fareGroup.get("fareCode", "")
            for fare in fareGroup.get("bundleList", []):
                id = fare.get("itineraryID")
                if not id in result.fares:
                    result.fares[id] = {}

                price = (
                    float(price) if (price := fare.get("price")).isnumeric() else None
                )
                cabin = (
                    cabin
                    if (cabin := fare.get("cabinclass")).lower() != "n/a"
                    else None
                )
                status = (
                    FareStatus[status.lower()]
                    if (status := fare.get("status"))
                    else FareStatus.unknown
                )

                result.fares[id][code] = FareInfo(
                    itineraryID=fare.get("itineraryID"),
                    price=price,
                    cabinclass=cabin,
                    refundable=bool(fare.get("refundable")),
                    status=status,
                )

        result.intineraries.extend(
            Itinerary(
                id=i.get("id"),
                source=i.get("from"),
                destination=i.get("to"),
                depart=datetime.strptime(depart, "%Y-%m-%dT%H:%M:%S%z")
                if (depart := i.get("depart"))
                else None,
                arrive=datetime.strptime(arrive, "%Y-%m-%dT%H:%M:%S%z")
                if (arrive := i.get("arrive"))
                else None,
                isOverNightFlight=bool(overnight)
                if (overnight := i.get("isOverNightFlight"))
                else None,
                segments=[],
            )
            for i in payload.itinerary
        )

        return result


async def main() -> None:
    """
    passengers = PassengerInfo(adults=1)
    async with JetBluePuppet(debug=True) as client:
        resp = await client.get_fares_json("JFK", "MIA", datetime(2022, 6, 2), datetime(2022, 6, 6), passengers)
    """
    with open("example.json", "r") as f:
        contents = f.read()
        import json

        jc = json.loads(contents)
        resp = JetBluePuppetResponse(**jc)
    j = JetBlueParser.parse(resp)
    from pprint import pprint

    pprint(j)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

    """import argparse

    parser = argparse.ArgumentParser(description="Get JetBlue airline prices.")
    parser.add_argument("origin", help="Origin airport.")
    parser.add_argument(
        "departure_date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help="Departure date from origin airport. YYYY-mm-dd",
    )
    parser.add_argument("destination", help="Destination airport.")
    parser.add_argument(
        "return_date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help="Return date from destination airport. YYYY-mm-dd",
    )
    parser.add_argument(
        "--passengers", type=int, default=1, help="Number of adult passengers. default=1"
    )
    parser.add_argument(
        "--children", type=int, default=0, help="Number of child passengers. default=0"
    )

    args = parser.parse_args()

    passengers = PassengerInfo(Adults=args.passengers, Children=args.children)

    client = JetBlue()
    departure_info = client.get_departure_info_for(
        args.origin, args.destination, passengers, args.departure_date
    )
    if departure_info:
        print(departure_info)
        return_info = client.get_return_info_for(
            args.origin,
            args.destination,
            passengers,
            args.departure_date,
            args.return_date,
        )
        if return_info:
            print(return_info)
            print(
                f"Total price: ${departure_info.price + return_info.price} " +
                f"for {departure_info.day} to {return_info.day} " + 
                f"from {departure_info.departure_airport} to {return_info.departure_airport}"
            )"""
