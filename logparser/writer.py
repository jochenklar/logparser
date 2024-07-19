import csv
import json
import sys
from datetime import datetime


class Writer:

    fieldnames = [
        'sha1',
        'host',
        'remote_host',
        'remote_country',
        'remote_user',
        'time',
        'request_method',
        'request_path',
        'request_query',
        'request_version',
        'status',
        'size',
        'referrer_scheme',
        'referrer_host',
        'referrer_path',
        'referrer_query',
        'user_agent',
        'user_agent_device',
        'user_agent_os',
        'user_agent_browser'
    ]

    def __init__(self, format='raw', chunking=None, output_path=None, database_settings=None):
        self.format = format
        self.chunking = chunking
        self.output_path = output_path
        self.database_settings = database_settings

        self.log_lines = []
        self.log_entries = []

        self.current_date = None
        self.current_records = set()

    def open(self):
        if self.format in ['raw', 'json']:
            self.fp = open(self.output, 'w') if self.output_path else sys.stdout

        elif self.format == 'csv':
            self.fp = open(self.output, 'w') if self.output_path else sys.stdout
            self.writer = csv.DictWriter(self.fp, fieldnames=self.fieldnames)
            self.writer.writeheader()

        elif self.format == 'sql':
            from .database import create_session
            self.session = create_session(self.database_settings)

    def append(self, log_line, log_entry):
        self.log_lines.append(log_line)
        self.log_entries.append(log_entry)

    def chunk(self):
        return (self.chunking and len(self.log_entries) >= self.chunking)

    def write(self):
        if self.format == 'raw':
            self.fp.writelines(self.log_lines)
        elif self.format == 'json':
            json.dump(self.log_entries, self.fp, indent=2)
        elif self.format == 'csv':
            self.writer.writerows(self.log_entries)
        elif self.format == 'sql':
            self.session.bulk_save_objects(self.get_records())
            self.session.commit()

    def close(self):
        if self.format in ['raw', 'json', 'csv']:
            self.fp.close()
        elif self.format == 'sql':
            self.session.close()

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
