from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlencode
from enum import Enum

import asyncio
from webbrowser import get
from pyppeteer.browser import Browser
from pyppeteer.page import Page
from pyppeteer import launch
from util import PassengerInfo


@dataclass
class InOutBoundResponse:
    currency: str
    fareGroup: List[Dict]
    itinerary: List[Dict]
    isTransatlanticRoute: bool
    countryCode: str = None  # missing from inbound
    dategroup: str = None  # ignore
    stopsFilter: str = None  # ignore
    programName: str = None  # ignore
    sessionId: str = None  # ignore


@dataclass
class JetBluePuppetResponse:
    outbound: InOutBoundResponse
    inbound: InOutBoundResponse


@dataclass
class FlightLeg:
    departureAirport: str
    arrivalAirport: str
    departureTerminal: str
    arrivalTerminal: str


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
    duration: timedelta
    layover: timedelta
    flightno: str
    operatingAirlineCode: str
    operatingAirlineName: str
    throughFlightLegs: List[FlightLeg]  # FlightLeg


class FareStatus(Enum):
    unknown = 0
    not_offered = 1
    available = 2
    sold_out = 3


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
    segments: List[Segment]

    # custom properties
    fares: List[FareInfo]


class JetBluePuppet:
    browser: Browser = None
    debug: bool = False
    save_json: bool = False

    def __init__(self, debug=False, save_json=False) -> None:
        self.debug = debug
        self.save_json = save_json

    async def _get_page(self) -> Page:
        if not self.browser:
            self.browser: Browser = await launch(headless=True, args=["--no-sandbox"])
        page: Page = await self.browser.newPage()
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36"
        )
        return page

    async def _get_outbound_flights(
        self, page: Page, timeout=None
    ) -> InOutBoundResponse:
        try:
            timeout = timeout or timedelta(seconds=30)
            resp = await page.waitForResponse(
                lambda r: "outboundLFS" in r.url, timeout=timeout.seconds * 1000
            )
            contents = await resp.json()
            if self.save_json:
                with open("outbound.json", "w") as f:
                    f.write(json.dumps(contents, indent=4, sort_keys=True))
            return InOutBoundResponse(**contents)
        except Exception as ex:
            if self.debug:
                debug_filename = "error_page_wait_outbound.png"
                await page.screenshot(path=debug_filename)
            raise ex

    async def _get_inbound_flights(
        self, page: Page, timeout=None
    ) -> InOutBoundResponse:
        try:
            # there might be popups on the page, so use JS to click the first outbound flight
            await page.evaluate(
                "document.getElementById('auto-flight-quickest-or-lowest-0').click();"
            )

            timeout = timeout or timedelta(seconds=30)
            resp = await page.waitForResponse(
                lambda r: "inboundLFS" in r.url and r.request.method != "OPTIONS",
                timeout=timeout.seconds * 1000,
            )
            contents = await resp.json()
            if self.save_json:
                with open("inbound.json", "w") as f:
                    f.write(json.dumps(contents, indent=4, sort_keys=True))
            return InOutBoundResponse(**contents)
        except Exception as ex:
            if self.debug:
                debug_filename = "error_page_wait_inbound.png"
                await page.screenshot(path=debug_filename)
            raise ex

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

        page: Page = await self._get_page()
        try:
            await page.goto(url)
        except Exception as ex:
            if self.debug:
                debug_filename = "error_page_load_url.png"
                await page.screenshot(path=debug_filename)
            raise ex

        outbound: InOutBoundResponse = await self._get_outbound_flights(page, timeout)
        inbound: InOutBoundResponse = await self._get_inbound_flights(page, timeout)
        return JetBluePuppetResponse(outbound=outbound, inbound=inbound)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()


class JetBluePuppetParser:
    @classmethod
    def parse(self, payload: InOutBoundResponse) -> List[Itinerary]:
        result: List[Itinerary] = []

        # isnumeric() doesn't detect floats, so try/fail instead
        def tofloat(num: str) -> Tuple[bool, Optional[float]]:
            try:
                return (True, float(num))
            except:
                return (False, None)

        def parse_duartion(val: str) -> Optional[timedelta]:
            match = re.match("PT(?P<hour>\d+)H(?P<minutes>\d+)M", val or "")
            if match:
                return timedelta(
                    hours=int(match.group("hour")), minutes=int(match.group("minutes"))
                )
            return None

        fares: Dict[str, List[FareInfo]] = defaultdict(list)
        all_fares = [
            fare for group in payload.fareGroup for fare in group.get("bundleList", [])
        ]
        for fare in all_fares:
            status = (
                FareStatus[status.lower()]
                if (status := fare.get("status"))
                else FareStatus.unknown
            )
            if status != FareStatus.available:
                continue  # fare is not purchaseble, ignore.

            id = fare.get("itineraryID")
            valid_price, price = tofloat(fare.get("price"))
            cabin = (
                cabin if (cabin := fare.get("cabinclass")).lower() != "n/a" else None
            )
            refundable = True if fare.get("refundable", "").lower() == "true" else False
            fares[id].append(
                FareInfo(
                    itineraryID=id,
                    price=price if valid_price else None,
                    code=fare.get("code"),
                    cabinclass=cabin,
                    refundable=refundable,
                    status=status,
                )
            )

        for itinerary in payload.itinerary:
            id = itinerary.get("id")
            if not id in fares or len(fares[id]) == 0:
                continue  # itinerary is not purchaseble

            depart = (
                datetime.strptime(depart, "%Y-%m-%dT%H:%M:%S%z")
                if (depart := itinerary.get("depart"))
                else None
            )
            arrive = (
                datetime.strptime(arrive, "%Y-%m-%dT%H:%M:%S%z")
                if (arrive := itinerary.get("arrive"))
                else None
            )

            segments: List[Segment] = []
            for segment in itinerary.get("segments", []):
                segment_depart = (
                    datetime.strptime(segment_depart, "%Y-%m-%dT%H:%M:%S%z")
                    if (segment_depart := segment.get("depart"))
                    else None
                )
                segment_arrive = (
                    datetime.strptime(segment_arrive, "%Y-%m-%dT%H:%M:%S%z")
                    if (segment_arrive := segment.get("arrive"))
                    else None
                )
                legs = [
                    FlightLeg(
                        departureAirport=leg.get("departureAirport"),
                        arrivalAirport=leg.get("arrivalAirport"),
                        departureTerminal=leg.get("departureTerminal"),
                        arrivalTerminal=leg.get("arrivalTerminal"),
                    )
                    for leg in segment.get("throughFlightLegs", [])
                ]
                segments.append(
                    Segment(
                        id=segment.get("id"),
                        source=segment.get("from"),
                        destination=segment.get("to"),
                        aircraft=segment.get("aircraft"),
                        aircraftCode=segment.get("aircraftCode"),
                        stops=int(segment.get("stops", "0")),
                        depart=segment_depart,
                        arrive=segment_arrive,
                        duration=parse_duartion(segment.get("duration")),
                        layover=parse_duartion(segment.get("layover")),
                        flightno=segment.get("flightno"),
                        operatingAirlineCode=segment.get("operatingAirlineCode"),
                        operatingAirlineName=segment.get("operatingAirlineName"),
                        throughFlightLegs=legs,
                    )
                )

            result.append(
                Itinerary(
                    id=id,
                    source=itinerary.get("from"),
                    destination=itinerary.get("to"),
                    depart=depart,
                    arrive=arrive,
                    isOverNightFlight=itinerary.get("isOverNightFlight"),
                    segments=segments,
                    fares=fares[id],
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
        "--passengers",
        type=int,
        default=1,
        help="Number of adult passengers. default=1",
    )
    parser.add_argument(
        "--children", type=int, default=0, help="Number of child passengers. default=0"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the outbound and inbound json to files.",
    )

    parser.add_argument(
        "--depart-after",
        type=int,
        default=None,
        help="Show flights departing after hour.",
    )
    parser.add_argument(
        "--depart-before",
        type=int,
        default=None,
        help="Show flights departing before hour.",
    )
    parser.add_argument(
        "--return-after",
        type=int,
        default=None,
        help="Show flights returning after hour.",
    )
    parser.add_argument(
        "--return-before",
        type=int,
        default=None,
        help="Show flights returning before hour.",
    )

    args = parser.parse_args()

    if (
        args.depart_after
        and args.depart_before
        and args.depart_before < args.depart_after
    ):
        raise argparse.ArgumentError(
            None, message="departure-before hour cannot be before departure-after hour."
        )
    if (
        args.return_after
        and args.return_before
        and args.return_before < args.return_after
    ):
        raise argparse.ArgumentError(
            None, message="return-before hour cannot be before return-after hour."
        )

    async def main() -> None:
        passengers = PassengerInfo(adults=args.passengers, children=args.children)
        async with JetBluePuppet(debug=True, save_json=args.save) as client:
            resp = await client.get_fares_json(
                args.origin,
                args.destination,
                args.departure_date,
                args.return_date,
                passengers,
            )
        outbound: List[Itinerary] = JetBluePuppetParser.parse(resp.outbound)
        inbound: List[Itinerary] = JetBluePuppetParser.parse(resp.inbound)

        def print_itinerary(itineraries: List[Itinerary]) -> None:
            year_format: str = "%Y-%m-%d %I:%M %p"
            hour_format: str = "%I:%M %p"
            for itinerary in itineraries:
                flight_times = ""
                total_time = timedelta(hours=0)
                for idx, segment in enumerate(itinerary.segments):
                    source = segment.source if idx == 0 else ""
                    src_format = year_format if idx == 0 else hour_format
                    dst_format = (
                        year_format
                        if segment.depart.date() != segment.arrive.date()
                        or (idx == len(itinerary.segments) - 1)
                        else hour_format
                    )
                    duration = f"\N{airplane}  {int(segment.duration.seconds / 60 / 60)}:{int(segment.duration.seconds / 60) % 60:02d} \N{airplane} "
                    duration = f"{segment.depart.strftime(src_format)} {duration} {segment.arrive.strftime(dst_format)} "
                    layover = (
                        f"[ {int(segment.layover.seconds / 60 / 60)}:{int(segment.layover.seconds / 60) % 60} ]"
                        if segment.layover
                        else ""
                    )
                    flight_times += (
                        f"{source} {duration} {segment.destination} {layover}"
                    )
                    total_time += (segment.duration or timedelta(hours=0)) + (
                        segment.layover or timedelta(hours=0)
                    )

                duration = f"\N{airplane}  {int(total_time.seconds / 60 / 60)}:{int(total_time.seconds / 60) % 60:02d} \N{airplane} "
                flight_overall = (
                    f"{itinerary.source} {itinerary.depart:%H:%M} {duration} {itinerary.destination} {itinerary.arrive:%H:%M} "
                    + " ".join(
                        f"[ ${fare.price} {fare.code} {'REFUNDABLE' if fare.refundable else ''}]"
                        for fare in itinerary.fares
                    )
                )
                print(flight_overall)
                print("\t" + flight_times)

        trips = []
        for itinerary in outbound:
            if args.depart_after and itinerary.depart.hour < args.depart_after:
                continue
            if args.depart_before and itinerary.depart.hour > args.depart_before:
                continue
            trips.append(itinerary)
        trips = sorted(trips, key=lambda i: i.depart)
        print_itinerary(trips)

        trips = []
        for itinerary in inbound:
            if args.return_after and itinerary.arrive.hour < args.return_after:
                continue
            if args.return_before and itinerary.arrive.hour > args.return_before:
                continue
            trips.append(itinerary)
        trips = sorted(trips, key=lambda i: i.depart)
        print()
        print_itinerary(trips)

    asyncio.get_event_loop().run_until_complete(main())
