# py-jetblue
Find JetBlue Airline prices. The current implementation uses puppeteer to load the JetBlue website and capture an XHR response. Puppeteer installs Chromium on first use, so if you don't want to download Chromium locally, build the docker container.

# Usage
```
usage: jetblue.py [-h] [--passengers PASSENGERS] [--children CHILDREN] [--depart-after DEPART_AFTER] [--depart-before DEPART_BEFORE] [--return-after RETURN_AFTER] [--return-before RETURN_BEFORE]
                  origin departure_date destination return_date

Get JetBlue airline prices.

positional arguments:
  origin                Origin airport.
  departure_date        Departure date from origin airport. YYYY-mm-dd
  destination           Destination airport.
  return_date           Return date from destination airport. YYYY-mm-dd

options:
  -h, --help            show this help message and exit
  --passengers PASSENGERS
                        Number of adult passengers. default=1
  --children CHILDREN   Number of child passengers. default=0
  --depart-after DEPART_AFTER
                        Show flights departing after hour.
  --depart-before DEPART_BEFORE
                        Show flights departing before hour.
  --return-after RETURN_AFTER
                        Show flights returning after hour.
  --return-before RETURN_BEFORE
                        Show flights returning before hour.
```

# Example
```
>>> python jetblue.py JFK 2022-06-02 FLL 2022-06-10

```

# Docker

```
>>> docker build -t jetblue .
>>> docker run jetblue JFK 2022-06-02 FLL 2022-06-10

```