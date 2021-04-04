# greeter-osm

This script utilizes [newesttoosm](https://neis-one.org/2012/04/where-are-the-new-openstreetmap-contributors/) feed and sends a welcome message to a user.

The status is stored in `statusgreeter` file, therefore it is safe to call it daily. E.g., in cron.
```
usage: greeter_osm.py [-h] [-d] [-l logfile] [-n] [-u user]

send OSM welcome message to a user with the first changeset made in a region

optional arguments:
  -h, --help  show this help message and exit
  -d          debug mode
  -l logfile  log to file (implies -d)
  -n          do NOT send the actual message
  -u user     send message to USER
```

The configuration is stored in `greeter-osm.conf`.

# License

[WTFPL](LICENSE)
