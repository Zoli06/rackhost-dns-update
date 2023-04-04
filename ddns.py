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
        # Get myip and hostname from get parameter
        myip = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['myip'][0]
        hostname = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['hostname'][0]
        
        # Get domain and name from hostname
        domain = hostname.split('.')[-2] + '.' + hostname.split('.')[-1]
        # Consider nth level domain and root domain
        name = hostname.split('.')[0] if len(hostname.split('.')) > 2 else ''
        
        # Get auth token from header
        # Authorization: Basic base64({username}:{password})
        auth = self.headers['Authorization']
        print(auth)
        auth_decoded = base64.b64decode(auth.split(' ')[1]).decode('utf-8')
        print(auth_decoded)
        given_username = auth_decoded.split(':')[0]
        given_password = auth_decoded.split(':')[1]
        
        print(f'Update {name}.{domain} to {myip}')
        
        rackhost_username = os.getenv('DDNS_USERNAME')
        rackhost_password = os.getenv('DDNS_USERNAME')
        
        print(f'Given username: {given_username}')
        print(f'Given password: {given_password}')
        print(f'Rackhost username: {rackhost_username}')
        print(f'Rackhost password: {rackhost_password}')
        
        if (given_username != rackhost_username) or (given_password != rackhost_password):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Rackhost DDNS"')
            self.end_headers()
            print('Unauthorized')
            return
        
        print('Authorized')
        rackhost_main([domain, name, 'update', '--target', myip])
        print('Done')
        
        self.send_response(200)        
        
        return

def main(server_class=http.server.HTTPServer, handler_class=http.server.BaseHTTPRequestHandler):
    load_dotenv()
    
    server_address = ('', 8245)
    httpd = server_class(server_address, MyHandler)
    httpd.serve_forever()
    
if __name__ == '__main__':
    main()