from http.server import HTTPServer, SimpleHTTPRequestHandler
port = 3000
httpd = HTTPServer(('', port), SimpleHTTPRequestHandler)
print(f'Serving at port {port}')
httpd.serve_forever()
