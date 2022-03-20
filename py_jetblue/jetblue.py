from dataclasses import dataclass
from datetime import datetime
from typing import List, Union, Dict
import asyncio
from pyppeteer import launch


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
    def __init__(self) -> None:
        self.browser = None

    async def get_fares_json(self) -> dict:
        if not self.browser:
            self.browser = await launch()
        page = await self.browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36')
        try:
            await page.goto('https://www.jetblue.com/booking/flights?from=NYC&to=MIA&depart=2022-06-02&return=2022-06-06&isMultiCity=false&noOfRoute=1&lang=en&adults=1&children=0&infants=0&sharedMarket=false&roundTripFaresFlag=false&usePoints=false')
            resp = await page.waitForResponse(lambda r: 'outboundLFS' in r.url, timeout=30000)
            content = await resp.text()
            with open('example1.json', 'w') as f:
                f.write(content)
        finally:
            await page.screenshot({'path': 'example1.png'})
            await self.browser.close()

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()


async def main():
    async with JetBluePuppet() as client:
        await client.get_fares_json()

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