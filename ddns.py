# Router will send request when ip address changes
# Create a server to receive the request

import http.server
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
            myip = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['myip'][0]
            hostname = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['hostname'][0]
            
            if not myip or not hostname:
                raise Exception('Neccessary parameters not set')
            
            # Get domain and name from hostname
            domain = hostname.split('.')[-2] + '.' + hostname.split('.')[-1]
            # Consider nth level domain and root domain
            name = hostname.split('.')[0] if len(hostname.split('.')) > 2 else ''

            # Get auth token from header
            # Authorization: Basic base64({username}:{password})
            auth = self.headers['Authorization']
            
            if not auth:
                raise Exception('No auth token')
            
            auth_decoded = base64.b64decode(auth.split(' ')[1]).decode('utf-8')
            given_username = auth_decoded.split(':')[0]
            given_password = auth_decoded.split(':')[1]
            
            rackhost_username = os.getenv('DDNS_USERNAME')
            rackhost_password = os.getenv('DDNS_USERNAME')

            if (given_username != rackhost_username) or (given_password != rackhost_password):
                raise Exception('Wrong auth token')

            print(f'Update {name}.{domain} to {myip}')
            rackhost_main([domain, name, 'update', '--target', myip])
            print('Done')
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes('Done', 'utf-8'))
            return

        # Filter out exceptions and return error code respectively
        # Neccessary parameters not set -> 400
        # No auth token -> 401
        # Wrong auth token -> 403
        # Other exceptions -> 500
        except Exception as e:
            print(e)
            if str(e) == 'Neccessary parameters not set':
                self.send_response(400)
            elif str(e) == 'No auth token':
                self.send_response(401)
            elif str(e) == 'Wrong auth token':
                self.send_response(403)
            else:
                self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(str(e), 'utf-8'))
        
        return

def main(server_class=http.server.HTTPServer, handler_class=http.server.BaseHTTPRequestHandler):
    load_dotenv()
    
    # Check necessary environment variables
    if not os.getenv('DDNS_USERNAME') or not os.getenv('DDNS_PASSWORD'):
        raise Exception('DDNS_USERNAME or DDNS_PASSWORD not set')

    server_address = ('', 8245)
    httpd = server_class(server_address, MyHandler)
    
    print("Server started")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    print("Server stopped")


if __name__ == '__main__':
    main()
