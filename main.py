import requests
import os
from dotenv import load_dotenv
from pyquery import PyQuery as pq
import argparse


def get_csrf_from_response(response):
    # Sometimes csrf from cookie is not enough and the server needs a second csrf from the form
    csrf = pq(response.text)('input[name="rackhost-csrf"]').val()
    if not csrf:
        # Sometimes it's in a meta tag
        csrf = pq(response.text)('meta[name="csrf-key"]').attr('content')

    return csrf


def login(session, rackhost_url, email, password):
    r1 = session.get(f'{rackhost_url}/site/login')

    csrf = get_csrf_from_response(r1)

    session.post(
        f'{rackhost_url}/site/login',
        data={
            'LoginForm[username]': email,
            'LoginForm[password]': password,
            # Get csrf from cookie
            'rackhost-csrf': csrf,
        },
    )


def get_dns_zone_id(session, rackhost_url, domain):
    r1 = session.get(f'{rackhost_url}/dnsZone')

    # <a href="/dnsZone/{dnsZone}">{domain}</a>
    for a in pq(r1.text)('a'):
        if pq(a).text() == domain:
            return pq(a).attr('href').split('/')[-1]


def get_dns_record_id(session, rackhost_url, dns_zone_id, dns_record):
    r1 = session.get(f'{rackhost_url}/dnsZone/{dns_zone_id}')

    # tr
    #  td {dns_record}
    #  td
    #  a href="/dnsRecord/updateOther/{dnsRecord}"
    for tr in pq(r1.text)('tr'):
        if pq(tr)('td').eq(0).text() == dns_record:
            return pq(tr)('a').attr('href').split('/')[-1]


def update_dns_record(session, rackhost_url, dns_record_id, name=None, type=None, ttl=None, target=None):
    r1 = session.get(f'{rackhost_url}/dnsRecord/updateOther/{dns_record_id}')

    csrf = get_csrf_from_response(r1)

    if not name:
        name = pq(r1.text)('input[name="DnsRecordForm[name]"]').val()
    if not type:
        type = pq(r1.text)('input[name="DnsRecordForm[type]"]').val()
    if not ttl:
        ttl = pq(r1.text)('input[name="DnsRecordForm[ttl]"]').val()
    if not target:
        target = pq(r1.text)('input[name="DnsRecordForm[target]"]').val()

    session.post(
        f'{rackhost_url}/dnsRecord/updateOther/{dns_record_id}',
        data={
            'DnsRecordForm[name]': name,
            'DnsRecordForm[type]': type,
            'DnsRecordForm[ttl]': ttl,
            'DnsRecordForm[target]': target,
            'rackhost-csrf': csrf,
        },
    )


def create_dns_record(session, rackhost_url, dns_zone_id, name, type, ttl, target):
    r1 = session.get(f'{rackhost_url}/dnsRecord/createOther?dnsZoneId={dns_zone_id}')

    csrf = get_csrf_from_response(r1)

    session.post(
        f'{rackhost_url}/dnsRecord/createOther?dnsZoneId={dns_zone_id}',
        data={
            'DnsRecordForm[name]': name,
            'DnsRecordForm[type]': type,
            'DnsRecordForm[ttl]': ttl,
            'DnsRecordForm[target]': target,
            'rackhost-csrf': csrf,
        },
    )


def delete_dns_record(session, rackhost_url, dns_record_id):
    r1 = session.get(f'{rackhost_url}/dnsZone/{dns_record_id}')

    csrf = get_csrf_from_response(r1)

    session.post(
        f'{rackhost_url}/dnsRecord/delete/{dns_record_id}',
        data={
            'rackhost-csrf': csrf,
        },
    )


def finalize_dns_zone(session, rackhost_url, dns_zone_id):
    session.get(f'{rackhost_url}/dnsZone/finalize/{dns_zone_id}')


def main():
    # Load environment variables from .env file
    load_dotenv()
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    rackhost_url = os.getenv('RACKHOST_URL')
    http_proxy = os.getenv('HTTP_PROXY')
    https_proxy = os.getenv('HTTPS_PROXY')

    # Check if all mandatory environment variables are set
    if not email or not password or not rackhost_url:
        raise Exception('Missing mandatory environment variables')

    ttl_choices = [300, 600, 900, 1800, 3600, 7200, 14400,
                   21600, 43200, 86400, 172800, 432000, 604800]

    # Get parameters from command line parameters
    parser = argparse.ArgumentParser()

    parser.add_argument('domain', help='DNS zone domain')

    subparsers = parser.add_subparsers(dest='action')

    create_parser = subparsers.add_parser('create', help='Create DNS record')
    create_parser.add_argument('--name', help='DNS record name')
    create_parser.add_argument('--type', help='DNS record type', required=True, choices=[
                               'A', 'AAAA', 'CNAME', 'TXT'])
    create_parser.add_argument(
        '--ttl', help='DNS record TTL', required=True, choices=ttl_choices, type=int)
    create_parser.add_argument(
        '--target', help='DNS record target', required=True)

    update_parser = subparsers.add_parser('update', help='Update DNS record')
    update_parser.add_argument('--name', help='DNS record name')
    update_parser.add_argument('--type', help='DNS record type', choices=[
                               'A', 'AAAA', 'CNAME', 'TXT'])
    update_parser.add_argument(
        '--ttl', help='DNS record TTL', choices=ttl_choices, type=int)
    update_parser.add_argument('--target', help='DNS record target')

    delete_parser = subparsers.add_parser('delete', help='Delete DNS record')
    delete_parser.add_argument('--name', help='DNS record name', required=True)

    action = parser.parse_args().action
    domain = parser.parse_args().domain
    name = parser.parse_args().name

    dns_record = name + '.' + domain if name else domain

    # Create a session
    session = requests.Session()
    if http_proxy:
        session.proxies.update({'http': http_proxy})
    if https_proxy:
        session.proxies.update({'https': https_proxy})

    login(session, rackhost_url, email, password)
    dns_zone_id = get_dns_zone_id(session, rackhost_url, domain)
    dns_record_id = get_dns_record_id(
        session, rackhost_url, dns_zone_id, dns_record)
    
    if action == 'update':
        type = parser.parse_args().type
        ttl = parser.parse_args().ttl
        target = parser.parse_args().target
        update_dns_record(session, rackhost_url,
                          dns_record_id, name, type, ttl, target)
    elif action == 'create':
        type = parser.parse_args().type
        ttl = parser.parse_args().ttl
        target = parser.parse_args().target
        create_dns_record(session, rackhost_url, dns_zone_id,
                          name, type, ttl, target)
    elif action == 'delete':
        delete_dns_record(session, rackhost_url, dns_record_id)

    finalize_dns_zone(session, rackhost_url, dns_zone_id)


if __name__ == '__main__':
    main()
