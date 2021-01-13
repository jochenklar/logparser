# logparser

This script parses logs in the Apache Common Log Format (CLF) used by Apache and NGINX and stores them without personal information as JSON, CSV or in a database table.

## Setup

The tool can be installed via pip. Usually you want to create a virtual environment first, but this is optional.

```bash
# optional virtual env
python3 -m venv env
source env/bin/activate

pip install git+https://github.com/jochenklar/logs
```

In order to resolve countries from IP addresses, goto <https://dev.maxmind.com/geoip/geoip2/geolite2/>, create an account, and download the `GeoLite2-Country.mmdb` database.

## Usage

The tool has several options which can be inspected using the help option `-h, --help`:

```
usage: logparser [-h] [--format {json,csv,sql}] [--host HOST]
                 [--database DATABASE] [--geoip2-database GEOIP2_DATABASE]
                 [--ignore-host IGNORE_HOST] [--ignore-path IGNORE_PATH]
                 [--log-level LOG_LEVEL] [--log-file LOG_FILE]
                 [--config-file CONFIG_FILE]
                 path

positional arguments:
  path                  Path to the file to process, can be a pattern using *

optional arguments:
  -h, --help            show this help message and exit
  --format {json,csv,sql}
                        Output format, default: json
  --host HOST           Host for this log, useful if logs of multiple hosts
                        are aggregated in one place, default: localhost
  --database DATABASE   Database connection string, e.g. postgresql+psycopg2:/
                        /username:password@host:port/dbname
  --geoip2-database GEOIP2_DATABASE
                        Path to the geoip2 database
  --ignore-host IGNORE_HOST
                        Host in the logs to be ignored, useful for internal
                        ips, can be repeated
  --ignore-path IGNORE_PATH
                        Path in the logs to be ignored, useful for recurring
                        API calls, can be repeated
  --log-level LOG_LEVEL
                        Log level (ERROR, WARN, INFO, or DEBUG)
  --log-file LOG_FILE   Path to the log file
  --config-file CONFIG_FILE
                        File path of the config file
```

The only mandatory argument is the `PATH` to the logfile to process. The optional arguments can be provided on the command line, but also:

* (in upper case) as environment variables, e.g. `FORMAT=csv`
* from `.env` file in the directory from where the script is called (with the same syntax)
* in a config file given by `--config-file`, or located at `logparser.conf`, `~/.logparser.conf`, or `/etc/logparser.conf`.

In order to connect to a database connection string `DATABASE` has to be provided and `psycopg2-binary` or `mysqlclient` have to be installed.

Examples:

```
logparser /var/log/apache2/access.log
logparser /var/log/apache2/access.log --format=json
logparser /var/log/apache2/access.log --format=sql --log-level=info --host=example.com
```

## Logrotate

The script is intended to be used with [logrotate](https://linux.die.net/man/8/logrotate). With the following setup logs are parsed and ingested into the database before they are rotated. Lets assume a Apache2 setup on Ubuntu/Debian with two virtual hosts, producing `example1.com.access.log` and `example2.com.access.log`, and the following `/etc/logrotate.d/apache2`:

```
/var/log/apache2/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 640 root adm
    sharedscripts
    postrotate
                if invoke-rc.d apache2 status > /dev/null 2>&1; then \
                    invoke-rc.d apache2 reload > /dev/null 2>&1; \
                fi;
    endscript
    prerotate
        if [ -d /etc/logrotate.d/httpd-prerotate ]; then \
            run-parts /etc/logrotate.d/httpd-prerotate; \
        fi; \
    endscript
}
```

This configuration calls all executables in `/etc/logrotate.d/httpd-prerotate` before rotating the logs. `logparser` can be used by adding an executable bash script:

```
# as root
mkdir /etc/logrotate.d/httpd-prerotate
touch /etc/logrotate.d/httpd-prerotate/logparser
chmod +x /etc/logrotate.d/httpd-prerotate/logparser
```

with the following content of `/etc/logrotate.d/httpd-prerotate/logparser`:

```
#!/bin/bash
/path/to/logparser/env/bin/logparser /var/log/example1.com.access.log --host=example1.com
/path/to/logparser/env/bin/logparser /var/log/example2.com.access.log --host=example2.com
```

and the following `/etc/logparser.conf`:

```
[default]
database = postgresql+psycopg2://username:password@host:port/dbname
format = sql
geoip2-database = /path/to/GeoLite2-Country.mmdb
```
