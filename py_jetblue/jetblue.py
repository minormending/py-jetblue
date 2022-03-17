from dataclasses import dataclass
from datetime import datetime
import requests
from typing import List, Union, Dict
import asyncio
from pyppeteer import launch


@dataclass
class PassengerInfo:
    Adults: int
    Children: int = 0
    Infants: int = 0


class JetBlue:
        def __init__(self) -> None:
            self.session = requests.Session()

async def main():
    browser = await launch({
    'ignoreDefaultArgs': ['--disable-extensions'],
    })
    page = await browser.newPage()
    await page.goto('https://www.jetblue.com/booking/flights?from=NYC&to=MIA&depart=2022-06-02&return=2022-06-06&isMultiCity=false&noOfRoute=1&lang=en&adults=1&children=0&infants=0&sharedMarket=false&roundTripFaresFlag=false&usePoints=false')
    await page.screenshot({'path': 'example.png'})
    await browser.close()

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