# logparser

This script parses logs in the Apache Common Log Format (CLF) used by Apache and NGINX and stores as JSON, CSV or in a database table. It is also able to filter then before.

## Setup

The tool can be installed via pip. Usually you want to create a virtual environment first, but this is optional.

```bash
# optional virtual env
python3 -m venv env
source env/bin/activate

pip install git+https://github.com/jochenklar/logparser
```

In order to resolve countries from IP addresses, goto <https://dev.maxmind.com/geoip/geoip2/geolite2/>, create an account, and download the `GeoLite2-Country.mmdb` database.

## Usage

The tool has several options which can be inspected using the help option `-h, --help`:

```
usage: logparser [-h] [--format {raw,json,csv,sql}] [--host HOST] [--database DATABASE]
                 [--geoip2-database GEOIP2_DATABASE] [--ignore-host IGNORE_HOST]
                 [--ignore-method IGNORE_METHOD] [--ignore-path IGNORE_PATH]
                 [--ignore-status IGNORE_STATUS] [--chunking CHUNKING] [--log-level LOG_LEVEL]
                 [--log-file LOG_FILE]
                 path [path ...]

positional arguments:
  path                  Paths to the files to process, can be a pattern using *

optional arguments:
  -h, --help            show this help message and exit
  --format {raw,json,csv,sql}
                        Output format, default: raw
  --host HOST           Host for this log, useful if logs of multiple hosts are aggregated in one
                        place, default: localhost
  --database DATABASE   Database connection string, e.g.
                        postgresql+psycopg2://username:password@host:port/dbname
  --geoip2-database GEOIP2_DATABASE
                        Path to the geoip2 database
  --ignore-host IGNORE_HOST
                        Host in the logs to be ignored, useful for internal ips, can be repeated
  --ignore-method IGNORE_METHOD
                        Methods in the logs to be ignored, useful for HEAD, OPTIONS, can be
                        repeated
  --ignore-path IGNORE_PATH
                        Path in the logs to be ignored, useful for recurring API calls, can be
                        repeated
  --ignore-status IGNORE_STATUS
                        Status in the logs to be ignored, useful for 206, 404, can be repeated
  --chunking CHUNKING   Optional chunking used to process the logfiles on low memory machines.
  --log-level LOG_LEVEL
                        Log level (ERROR, WARN, INFO, or DEBUG)
  --log-file LOG_FILE   Path to the log file
```

The only mandatory argument is the `path` to the logfile to process. The optional arguments can be provided on the command line, but also:

* (in upper case) as environment variables, e.g. `FORMAT=csv`
* from `.env` file in the directory from where the script is called (with the same syntax)

In order to connect to a database connection string `DATABASE` has to be provided and `psycopg2-binary` or `mysqlclient` have to be installed.

Examples:

```
logparser /var/log/apache2/access.log
logparser /var/log/apache2/access.log --format=json
logparser /var/log/apache2/access.log --format=sql --log-level=info --host=example.com
```

The `LogParser` class can also be used programatically to parse lines of logs from custom scripts, e.g.

```python
from logparser.parser import LogParser
from logparser.utils import open_log_file

with open_log_file(log_path) as fp:
  for line in fp.readlines():
    log_entry = parser.parse_line(line)
    ...
```
