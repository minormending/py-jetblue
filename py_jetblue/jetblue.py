from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Union, Dict
import asyncio
from pyppeteer.browser import Browser
from pyppeteer.page import Page
from pyppeteer import launch
from urllib.parse import urlencode


@dataclass
class PassengerInfo:
    adults: int
    children: int = 0
    infants: int = 0

@dataclass
class FareInfo:
    itineraryID: str
    price: float
    cabinclass: str
    refundable: bool
    status: str


class JetBluePuppet:
    browser:Browser = None
    debug: bool = False

    def __init__(self, debug=False) -> None:
        self.debug = debug

    async def _get_page(self) -> Page:
        if not self.browser:
            self.browser: Browser = await launch()
        page: Page = await self.browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36')
        return page

    async def get_fares_json(self, source: str, destination: str, departure_date: datetime, return_date: datetime, passengers: PassengerInfo, timeout: timedelta = None) -> dict:
        payload = {
            'from': source.upper(),
            'to': destination.upper(),
            'depart': f"{departure_date:%Y-%m-%d}",
            'return': f"{return_date:%Y-%m-%d}",
            'isMultiCity': False,
            'noOfRoute': 1,
            'lang': 'en',
            'adults': passengers.adults,
            'children': passengers.children,
            'infants': passengers.infants,
            'sharedMarket': False,
            'roundTripFaresFlag': False,
            'usePoints': False,
        }
        url = 'https://www.jetblue.com/booking/flights?' + urlencode(payload)

        try:
            timeout = timeout or timedelta(seconds=30)
            page: Page = await self._get_page()
            await page.goto(url)
            resp = await page.waitForResponse(lambda r: 'outboundLFS' in r.url, timeout=timeout.seconds * 1000)
            return await resp.json()
        except:
            if self.debug:
                debug_filename = 'error_page_load_url.png'
                await page.screenshot(path=debug_filename)

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()


async def main() -> None:
    passengers = PassengerInfo(adults=1)
    async with JetBluePuppet() as client:
        j = await client.get_fares_json("JFK", "MIA", datetime(2022, 6, 2), datetime(2022, 6, 6), passengers)
        print(j)

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