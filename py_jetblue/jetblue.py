from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Union, Dict, Tuple, Optional
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



class FareStatus(Enum):
    unknown = 0
    not_offered = 1
    available = 2


@dataclass
class FareInfo:
    itineraryID: str
    price: float
    code: str
    cabinclass: str
    refundable: bool
    status: FareStatus

@dataclass
class Itinerary:
    id: str
    source: str
    destination: str
    depart: datetime
    arrive: datetime
    isOverNightFlight: bool
    #segments: List[Dict]  # Segment

    # custom properties
    fares: List[FareInfo]



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
    def parse(self, payload: JetBluePuppetResponse) -> List[Itinerary]:
        result: List[Itinerary] = []

        def tofloat(num: str) -> Tuple[bool, Optional[float]]:
            try:
                return (True, float(num))
            except:
                return (False, None)

        fares: Dict[str, List[FareInfo]] = defaultdict(list)
        all_fares = [fare for group in payload.fareGroup for fare in group.get("bundleList", [])]
        for fare in all_fares:
            status = (
                FareStatus[status.lower()]
                if (status := fare.get("status"))
                else FareStatus.unknown
            )
            if status != FareStatus.available:
                continue # fare is not purchaseble, ignore.

            id = fare.get("itineraryID")
            valid_price, price = tofloat(fare.get("price"))
            cabin = (
                cabin
                if (cabin := fare.get("cabinclass")).lower() != "n/a"
                else None
            )
            refundable = True if fare.get("refundable", "").lower() == "true" else False
            fares[id].append(FareInfo(
                itineraryID=id,
                price=price if valid_price else None,
                code=fare.get("code"),
                cabinclass=cabin,
                refundable=refundable,
                status=status,
            ))

        for itinerary in payload.itinerary:
            id = itinerary.get("id")
            if not id in fares or len(fares[id]) == 0:
                continue # itinerary is not purchaseble

            depart = datetime.strptime(depart, "%Y-%m-%dT%H:%M:%S%z") if (depart := itinerary.get("depart")) else None
            arrive = datetime.strptime(arrive, "%Y-%m-%dT%H:%M:%S%z") if (arrive := itinerary.get("arrive")) else None
            result.append(
                Itinerary(
                    id=id,
                    source=itinerary.get("from"),
                    destination=itinerary.get("to"),
                    depart=depart,
                    arrive=arrive,
                    isOverNightFlight=itinerary.get("isOverNightFlight"),
                    #segments=[],
                    fares=fares[id]
                )
            )

        return result


if __name__ == "__main__":
    import argparse

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

    async def main() -> None:
        passengers = PassengerInfo(adults=args.passengers, children=args.children)
        async with JetBluePuppet(debug=True) as client:
            resp = await client.get_fares_json(args.origin, args.destination, args.departure_date, args.return_date, passengers)
        """
        with open("example.json", "r") as f:
            contents = f.read()
            import json

            jc = json.loads(contents)
            resp = JetBluePuppetResponse(**jc)"""
        j = JetBlueParser.parse(resp)
        from pprint import pprint

        pprint(j)

    asyncio.get_event_loop().run_until_complete(main())