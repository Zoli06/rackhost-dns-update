# Router will send request when ip address changes
# Create a server to receive the request

import http.server

class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Log url parameters
        print(self.path)
        print(self.headers)
        print(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
        
        self.send_response(200)        
        
        return

def main(server_class=http.server.HTTPServer, handler_class=http.server.BaseHTTPRequestHandler):
    server_address = ('', 8245)
    httpd = server_class(server_address, MyHandler)
    httpd.serve_forever()
    
if __name__ == '__main__':
    main()