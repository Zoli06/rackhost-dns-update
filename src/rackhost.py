import json
import requests
import os
from dotenv import load_dotenv
from pyquery import PyQuery as pq
import argparse
from tabulate import tabulate


def get_csrf_from_response(response):
    # Sometimes csrf from cookie is not enough and the server needs a second csrf from the form
    csrf = pq(response.text)('input[name="rackhost-csrf"]').val()
    if not csrf:
        # Sometimes it's in a meta tag
        csrf = pq(response.text)('meta[name="csrf-key"]').attr("content")

    return csrf


def login(session, rackhost_url, email, password):
    r1 = session.get(f"{rackhost_url}/site/login")

    csrf = get_csrf_from_response(r1)

    session.post(
        f"{rackhost_url}/site/login",
        data={
            "LoginForm[username]": email,
            "LoginForm[password]": password,
            # Get csrf from cookie
            "rackhost-csrf": csrf,
        },
    )


def get_dns_zone_id(session, rackhost_url, domain):
    r1 = session.get(f"{rackhost_url}/dnsZone")

    # <a href="/dnsZone/{dnsZone}">{domain}</a>
    for a in pq(r1.text)("#dns-zone-grid-view tbody td:first-child a"):
        if pq(a).text() == domain:
            return pq(a).attr("href").split("/")[-1]


def get_dns_record_id(session, rackhost_url, dns_zone_id, dns_record):
    r1 = session.get(f"{rackhost_url}/dnsZone/{dns_zone_id}")

    # #dns-record-grid-0
    #  tbody
    #   tr
    #    td {dns_record}
    #    td
    #    a href="/dnsRecord/updateOther/{dnsRecord}"
    for tr in pq(r1.text)("#dns-record-grid-0 tbody tr"):
        if pq(tr)("td").eq(0).text() == dns_record:
            return pq(tr)("a").attr("href").split("/")[-1]


def get_dns_zone_name(session, rackhost_url, dns_zone_id):
    r1 = session.get(f"{rackhost_url}/dnsZone")

    for a in pq(r1.text)("#dns-zone-grid-view tbody td:first-child a"):
        if pq(a).attr("href").split("/")[-1] == dns_zone_id:
            return pq(a).text()


def get_dns_record_name(session, rackhost_url, dns_zone_id, dns_record_id):
    r1 = session.get(f"{rackhost_url}/dnsZone/{dns_zone_id}")

    for tr in pq(r1.text)("#dns-record-grid-0 tbody tr"):
        if pq(tr)("a").attr("href").split("/")[-1] == dns_record_id:
            return pq(tr)("td").eq(0).text()


def get_all_dns_zones(session, rackhost_url):
    r1 = session.get(f"{rackhost_url}/dnsZone")

    dns_zones = []
    for a in pq(r1.text)("#dns-zone-grid-view tbody td:first-child a"):
        dns_zones.append(
            {
                "domain": pq(a).text(),
                "id": pq(a).attr("href").split("/")[-1],
            }
        )

    return dns_zones


def get_all_dns_records(session, rackhost_url, dns_zone_id):
    r1 = session.get(f"{rackhost_url}/dnsZone/{dns_zone_id}")

    dns_records = []
    for tr in pq(r1.text)("#dns-record-grid-0 tbody tr"):
        dns_records.append(
            {
                "name": pq(tr)("td").eq(0).text(),
                "id": pq(tr)("a").attr("href").split("/")[-1],
                "type": pq(tr)("td").eq(1).text(),
                "target": pq(tr)("td").eq(2).text(),
                "ttl": pq(tr)("td").eq(3).text(),
            }
        )

    return dns_records


def update_dns_record(
    session, rackhost_url, dns_record_id, name=None, type=None, ttl=None, target=None
):
    r1 = session.get(f"{rackhost_url}/dnsRecord/updateOther/{dns_record_id}")

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
        f"{rackhost_url}/dnsRecord/updateOther/{dns_record_id}",
        data={
            "DnsRecordForm[name]": name,
            "DnsRecordForm[type]": type,
            "DnsRecordForm[ttl]": ttl,
            "DnsRecordForm[target]": target,
            "rackhost-csrf": csrf,
        },
    )


def create_dns_record(session, rackhost_url, dns_zone_id, name, type, ttl, target):
    r1 = session.get(f"{rackhost_url}/dnsRecord/createOther?dnsZoneId={dns_zone_id}")

    csrf = get_csrf_from_response(r1)

    session.post(
        f"{rackhost_url}/dnsRecord/createOther?dnsZoneId={dns_zone_id}",
        data={
            "DnsRecordForm[name]": name,
            "DnsRecordForm[type]": type,
            "DnsRecordForm[ttl]": ttl,
            "DnsRecordForm[target]": target,
            "rackhost-csrf": csrf,
        },
    )


def delete_dns_record(session, rackhost_url, dns_record_id):
    r1 = session.get(f"{rackhost_url}/dnsZone/{dns_record_id}")

    csrf = get_csrf_from_response(r1)

    session.post(
        f"{rackhost_url}/dnsRecord/delete/{dns_record_id}",
        data={
            "rackhost-csrf": csrf,
        },
    )


def finalize_dns_zone(session, rackhost_url, dns_zone_id):
    session.get(f"{rackhost_url}/dnsZone/finalize/{dns_zone_id}")


def main(raw_args=None):
    output = ""

    # Load environment variables from .env file
    load_dotenv()
    email = os.getenv("RACKHOST_EMAIL")
    password = os.getenv("RACKHOST_PASSWORD")
    rackhost_url = os.getenv("RACKHOST_URL")
    http_proxy = os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("HTTPS_PROXY")

    # Check if all mandatory environment variables are set
    if not email or not password or not rackhost_url:
        raise Exception("Missing mandatory environment variables")

    ttl_choices = [
        300,
        600,
        900,
        1800,
        3600,
        7200,
        14400,
        21600,
        43200,
        86400,
        172800,
        432000,
        604800,
    ]

    table_style_choices = [
        "plain",
        "simple",
        "github",
        "grid",
        "simple_grid",
        "rounded_grid",
        "heavy_grid",
        "mixed_grid",
        "double_grid",
        "fancy_grid",
        "outline",
        "simple_outline",
        "rounded_outline",
        "heavy_outline",
        "mixed_outline",
        "double_outline",
        "fancy_outline",
        "pipe",
        "orgtbl",
        "asciidoc",
        "jira",
        "presto",
        "pretty",
        "psql",
        "rst",
        "mediawiki",
        "moinmoin",
        "youtrack",
        "html",
        "unsafehtml",
        "latex",
        "latex_raw",
        "latex_booktabs",
        "latex_longtable",
        "textile",
        "tsv",
        "json",
    ]

    # Get parameters from command line parameters
    parser = argparse.ArgumentParser()

    context_subparsers = parser.add_subparsers(help="Context", dest="context")

    zone_parser = context_subparsers.add_parser("zone", help="DNS zone actions")
    zone_subparsers = zone_parser.add_subparsers(
        help="DNS zone actions", dest="zone_action"
    )
    zone_list_parser = zone_subparsers.add_parser("list", help="List DNS zones")
    zone_list_parser.add_argument(
        "--style", help="Output style", choices=table_style_choices, default="simple"
    )

    record_parser = context_subparsers.add_parser("record", help="DNS record actions")
    record_parser.add_argument("--zone", help="DNS zone name", required=True)
    record_subparsers = record_parser.add_subparsers(
        help="DNS record actions", dest="record_action"
    )

    create_parser = record_subparsers.add_parser("create", help="Create DNS record")
    create_parser.add_argument("--name", help="DNS record name")
    create_parser.add_argument(
        "--type",
        help="DNS record type",
        required=True,
        choices=["A", "AAAA", "CNAME", "TXT"],
    )
    create_parser.add_argument(
        "--ttl", help="DNS record TTL", required=True, choices=ttl_choices, type=int
    )
    create_parser.add_argument("--target", help="DNS record target", required=True)

    update_parser = record_subparsers.add_parser("update", help="Update DNS record")
    update_parser.add_argument("--name", help="DNS record name")
    update_parser.add_argument(
        "--type", help="DNS record type", choices=["A", "AAAA", "CNAME", "TXT"]
    )
    update_parser.add_argument(
        "--ttl", help="DNS record TTL", choices=ttl_choices, type=int
    )
    update_parser.add_argument("--target", help="DNS record target")
    update_parser.add_argument("--newname", help="DNS record new name")

    delete_parser = record_subparsers.add_parser("delete", help="Delete DNS record")
    delete_parser.add_argument("--name", help="DNS record name")

    record_list_parser = record_subparsers.add_parser("list", help="List DNS records")
    record_list_parser.add_argument(
        "--style", help="Output style", choices=table_style_choices, default="simple"
    )

    args = parser.parse_args(raw_args)

    # Create a session
    session = requests.Session()
    if http_proxy:
        session.proxies.update({"http": http_proxy})
    if https_proxy:
        session.proxies.update({"https": https_proxy})

    login(session, rackhost_url, email, password)

    context = args.context

    if context == "zone":
        zone_action = args.zone_action

        if zone_action == "list":
            style = args.style

            dns_zones = get_all_dns_zones(session, rackhost_url)
            if style == "json":
                output = json.dumps(dns_zones, indent=4)
            else:
                output = tabulate(dns_zones, headers="keys", tablefmt=style)

            require_finalization = False
    elif context == "record":
        zone = args.zone
        dns_zone_id = get_dns_zone_id(session, rackhost_url, zone)

        require_finalization = False

        record_action = args.record_action

        if record_action == "update":
            name = args.name
            type = args.type
            ttl = args.ttl
            target = args.target
            newname = args.newname
            if not newname:
                newname = name

            dns_record = name + "." + zone if name else zone
            dns_record_id = get_dns_record_id(
                session, rackhost_url, dns_zone_id, dns_record
            )

            update_dns_record(
                session, rackhost_url, dns_record_id, newname, type, ttl, target
            )

            output = "DNS record updated"

            require_finalization = True
        elif record_action == "create":
            name = args.name
            type = args.type
            ttl = args.ttl
            target = args.target

            dns_record = name + "." + zone if name else zone
            dns_record_id = get_dns_record_id(
                session, rackhost_url, dns_zone_id, dns_record
            )

            create_dns_record(
                session, rackhost_url, dns_zone_id, name, type, ttl, target
            )

            output = "DNS record created"

            require_finalization = True
        elif record_action == "delete":
            name = args.name

            dns_record = name + "." + zone if name else zone
            dns_record_id = get_dns_record_id(
                session, rackhost_url, dns_zone_id, dns_record
            )

            delete_dns_record(session, rackhost_url, dns_record_id)

            output = "DNS record deleted"

            require_finalization = True
        elif record_action == "list":
            dns_records = get_all_dns_records(session, rackhost_url, dns_zone_id)
            style = args.style

            if style == "json":
                output = json.dumps(dns_records, indent=4)
            else:
                output = tabulate(dns_records, headers="keys", tablefmt=style)

            require_finalization = False

    if require_finalization:
        finalize_dns_zone(session, rackhost_url, dns_zone_id)

    print(output)
    return output


if __name__ == "__main__":
    main()
