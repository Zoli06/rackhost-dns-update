# Router will send request when ip address changes
# Create a server to receive the request

import http.server

def main(server_class=http.server.HTTPServer, handler_class=http.server.BaseHTTPRequestHandler):
    server_address = ('', 8245)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()
    
    # Log the request
    print('Request received')
    print('Request headers:')
    print(httpd.headers)
    print('Request body:')
    print(httpd.body)
    print('Request method:')
    print(httpd.method)
    print('Request path:')
    print(httpd.path)
    print('Request version:')
    print(httpd.version)
    print('Request command:')
    print(httpd.command)
    print('Request requestline:')
    print(httpd.requestline)
    print('Request client_address:')
    print(httpd.client_address)
    print('----------------------------------------')
    print('----------------------------------------')
    
if __name__ == '__main__':
    main()