# Router will send request when ip address changes
# Create a server to receive the request

import http.server
import json
import traceback
import urllib.parse
import base64
from dotenv import load_dotenv
import os
from rackhost import main as rackhost_main


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print(self.path)
            # Get myip and hostname from get parameter
            # Throw exception if not set
            myip = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)[
                "myip"
            ][0]
            hostname = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)[
                "hostname"
            ][0]

            if not myip or not hostname:
                raise Exception("Neccessary parameters not set")

            # Get domain and name from hostname
            domain = hostname.split(".")[-2] + "." + hostname.split(".")[-1]
            # Consider nth level domain and root domain
            name = hostname.split(".")[0] if len(hostname.split(".")) > 2 else ""

            # Get auth token from header
            # Authorization: Basic base64({username}:{password})
            auth = self.headers["Authorization"]

            if not auth:
                raise Exception("No auth token")

            auth_decoded = base64.b64decode(auth.split(" ")[1]).decode("utf-8")
            given_username = auth_decoded.split(":")[0]
            given_password = auth_decoded.split(":")[1]

            ddns_username = os.getenv("DDNS_USERNAME")
            ddns_password = os.getenv("DDNS_PASSWORD")

            if (given_username != ddns_username) or (given_password != ddns_password):
                print(f"Given username: {given_username}, password: {given_password}")
                print(f"Correct username: {ddns_username}, password: {ddns_password}")
                print(given_username != ddns_username)
                print(given_password != ddns_password)
                raise Exception("Wrong auth token")

            record = f"{name}.{domain}" if name else domain

            cache = None
            # read cache from file
            with open("cache.json", "r") as f:
                cache = json.loads(f.read())

                # search for record in cache
                for r in cache:
                    if r["name"] == record:
                        if r["target"] == myip:
                            print(f"{record} is already {myip}")
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(
                                bytes(f"{record} is already {myip}", "utf-8")
                            )
                            return
                        else:
                            break

            print(f"Update {record} to {myip}")
            rackhost_main(
                ["record", "--zone", domain, "update", "--name", name, "--target", myip]
            )
            with open("cache.json", "w") as f:
                # search for record in cache
                for r in cache:
                    if r["name"] == record:
                        r["target"] = myip

                f.write(json.dumps(cache))
                print("Cache updated")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("Done", "utf-8"))
            return

        # Filter out exceptions and return error code respectively
        # Neccessary parameters not set -> 400
        # No auth token -> 401
        # Wrong auth token -> 403
        # Other exceptions -> 500
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            if str(e) == "Neccessary parameters not set":
                self.send_response(400)
            elif str(e) == "No auth token":
                self.send_response(401)
            elif str(e) == "Wrong auth token":
                self.send_response(403)
            else:
                self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(str(e), "utf-8"))

        return


def main(
    server_class=http.server.HTTPServer,
    handler_class=http.server.BaseHTTPRequestHandler,
):
    print("Starting server")

    load_dotenv()

    # Check necessary environment variables
    if not os.getenv("DDNS_USERNAME") or not os.getenv("DDNS_PASSWORD"):
        raise Exception("DDNS_USERNAME or DDNS_PASSWORD not set")

    server_address = ("", 80)
    httpd = server_class(server_address, MyHandler)

    if not os.path.exists("cache.json"):
        zones = json.loads(rackhost_main(["zone", "list", "--style", "json"]))
        records = []
        for zone in zones:
            records.extend(
                json.loads(
                    rackhost_main(
                        ["record", "--zone", zone["domain"], "list", "--style", "json"]
                    )
                )
            )

        # cache to file
        with open("cache.json", "w") as f:
            f.write(json.dumps(records))

    print("Server started")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    print("Server stopped")


if __name__ == "__main__":
    main()
