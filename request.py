import re

def http_request_parser(string=''):
    if not string:
        return {}

    m = re.match('GET|HEAD', string)
    return m.group()

