import csv
import json
from datetime import datetime

from .models import LogEntry
from .utils import open_log_file


class Writer:

    def __init__(self, format=None, chunking=None, path=None, database_settings=None):
        self.format = format
        self.chunking = chunking
        self.path = path
        self.database_settings = database_settings

        self.rows = []

        self.current_date = None
        self.current_records = set()

    def open(self):
        if self.format == 'sql':
            from .database import create_session
            self.session = create_session(self.database_settings)

        else:
            self.fp = open_log_file(self.path, 'wt')

            if self.format in ['csv', 'csv.gz', 'csv.xz']:
                self.writer = csv.DictWriter(self.fp, fieldnames=LogEntry.get_fields())
                self.writer.writeheader()


    def append(self, row):
        self.rows.append(row)

    def chunk(self):
        return (self.chunking and len(self.rows) >= int(self.chunking))

    def write(self):
        if self.format == 'sql':
            self.session.bulk_save_objects(self.get_records())
            self.session.commit()

        elif self.format in ['json', 'json.gz', 'json.xz']:
            self.fp.writelines([
                json.dumps(row.serialize()) + '\n' for row in self.rows
            ])
        elif self.format in ['csv', 'csv.gz', 'csv.xz']:
            self.writer.writerows([
                row.serialize() for row in self.rows
            ])
        else:
            self.fp.writelines(self.rows)

        # reset row buffer
        self.rows = []

    def close(self):
        if self.format == 'sql':
            self.session.close()
        else:
            self.fp.close()

    def get_records(self):
        from .database import Record, get_current_records

        driver = self.session.get_bind().driver

        for log_entry in self.log_entries:
            entry_date = datetime.fromisoformat(log_entry['time']).date()
            if entry_date != self.current_date:
                self.current_date = entry_date
                self.current_records = get_current_records(self.session, entry_date)

            if log_entry['sha1'] not in self.current_records:
                self.current_records.add(log_entry['sha1'])

                if driver in ['sqlite']:
                    log_entry['date'] = datetime.strptime(log_entry['date'], '%Y-%m-%d')
                elif driver in ['mysqldb']:
                    for char_field in ['host', 'path', 'query', 'referrer_scheme', 'referrer_host',
                                       'referrer_path', 'referrer_query', 'agent']:
                        log_entry[char_field] = \
                            log_entry[char_field][:384] if log_entry.get(char_field) else log_entry.get(char_field)

                yield Record(**log_entry)
