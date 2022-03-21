# py-jetblue
Find JetBlue Airline prices. The current implementation uses puppeteer to load the JetBlue website and capture an XHR response. Puppeteer installs Chromium on first use, so if you don't want to download Chromium locally, build the docker container.

# Usage
```
usage: jetblue.py [-h] [--passengers PASSENGERS] [--children CHILDREN] origin departure_date destination return_date

Get JetBlue airline prices.

positional arguments:
  origin                Origin airport.
  departure_date        Departure date from origin airport. YYYY-mm-dd
  destination           Destination airport.
  return_date           Return date from destination airport. YYYY-mm-dd

optional arguments:
  -h, --help            show this help message and exit
  --passengers PASSENGERS
                        Number of adult passengers. default=1
  --children CHILDREN   Number of child passengers. default=0
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