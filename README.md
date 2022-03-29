# py-jetblue
Find JetBlue Airline prices. The current implementation uses puppeteer to load the JetBlue website and capture an XHR response. Puppeteer installs Chromium on first use, so if you don't want to download Chromium locally, build the docker container.

Alternatively, if you do not want to build the docker container youself, you can download the prebuilt containers from:
https://hub.docker.com/repository/docker/minormending/pyjetblue

# CLI Output Format
```
source_airport source_departure_time ✈ total_time_from_source_to_destination ✈ destination_airport destination_arrival_time [ price_for_tier tier_name ] [ ... ]
    source_airport source_departure_time ✈ flight_duration ✈ stop_airport [ layover_duration ] stop_departure_time ✈ flight_duration ✈ destination_arrival_time destination_airport

JFK 15:30 ✈  15:30 ✈  KEF 6:05 [ $782.9 BLUE ]
    JFK 2022-06-02 03:30 PM ✈  1:30 ✈  05:00 PM  BOS [ 3:50 ] 08:50 PM ✈  5:15 ✈  2022-06-03 06:05 AM  KEF
```

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
>>> python py_jetblue/puppet.py JFK 2022-06-02 FRA 2022-06-12

JFK 15:30 ✈  15:30 ✈  FRA 13:00 [ $782.9 BLUE ]
        JFK 2022-06-02 03:30 PM ✈  1:30 ✈  05:00 PM  BOS [ 3:50 ] 08:50 PM ✈  5:15 ✈  2022-06-03 06:05 AM  KEF [ 1:20 ] 07:25 AM ✈  3:35 ✈  2022-06-03 01:00 PM  FRA
JFK 20:25 ✈  10:35 ✈  FRA 13:00 [ $700.4 BLUE ]
        JFK 2022-06-02 08:25 PM ✈  5:50 ✈  2022-06-03 06:15 AM  KEF [ 1:10 ] 07:25 AM ✈  3:35 ✈  2022-06-03 01:00 PM  FRA

FRA 14:15 ✈  10:55 ✈  JFK 19:10 [ $883.37 BLUE ]
        FRA 2022-06-12 02:15 PM ✈  3:35 ✈  03:50 PM  KEF [ 1:10 ] 05:00 PM ✈  6:10 ✈  2022-06-12 07:10 PM  JFK
FRA 14:15 ✈  13:43 ✈  JFK 21:58 [ $1027.47 BLUE ]
        FRA 2022-06-12 02:15 PM ✈  3:35 ✈  03:50 PM  KEF [ 1:25 ] 05:15 PM ✈  5:35 ✈  06:50 PM  BOS [ 1:55 ] 08:45 PM ✈  1:13 ✈  2022-06-12 09:58 PM  JFK

```

# Docker

```
>>> docker build -t jetblue .
>>> docker run jetblue JFK 2022-06-02 FRA 2022-06-12

JFK 15:30 ✈  15:30 ✈  FRA 13:00 [ $782.9 BLUE ]
        JFK 2022-06-02 03:30 PM ✈  1:30 ✈  05:00 PM  BOS [ 3:50 ] 08:50 PM ✈  5:15 ✈  2022-06-03 06:05 AM  KEF [ 1:20 ] 07:25 AM ✈  3:35 ✈  2022-06-03 01:00 PM  FRA
JFK 20:25 ✈  10:35 ✈  FRA 13:00 [ $700.4 BLUE ]
        JFK 2022-06-02 08:25 PM ✈  5:50 ✈  2022-06-03 06:15 AM  KEF [ 1:10 ] 07:25 AM ✈  3:35 ✈  2022-06-03 01:00 PM  FRA

FRA 14:15 ✈  10:55 ✈  JFK 19:10 [ $883.37 BLUE ]
        FRA 2022-06-12 02:15 PM ✈  3:35 ✈  03:50 PM  KEF [ 1:10 ] 05:00 PM ✈  6:10 ✈  2022-06-12 07:10 PM  JFK
FRA 14:15 ✈  13:43 ✈  JFK 21:58 [ $1027.47 BLUE ]
        FRA 2022-06-12 02:15 PM ✈  3:35 ✈  03:50 PM  KEF [ 1:25 ] 05:15 PM ✈  5:35 ✈  06:50 PM  BOS [ 1:55 ] 08:45 PM ✈  1:13 ✈  2022-06-12 09:58 PM  JFK

```