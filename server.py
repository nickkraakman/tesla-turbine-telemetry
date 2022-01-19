import threading
import webbrowser

import http.server
import socketserver
import json

FILE = 'index.html'
PORT = 8000


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        """Handle POST request."""
        request_path = self.path

        # print("\n----- Request Start ----->\n")
        print("request_path : %s", request_path)

        request_headers = self.headers
        content_length = request_headers.get('content-length')
        length = int(content_length[0]) if content_length else 0

        # print("length :", length)

        print("request_headers : %s" % request_headers)
        print("content : %s" % self.rfile.read(length))
        # print("<----- Request End -----\n")

        response = {'hello': 'world', 'received': 'ok'}
        json_string = json.dumps(response)

        self.send_response(200)
        self.send_header("Set-Cookie", "foo=bar")
        self.end_headers()
        self.wfile.write(json_string.encode(encoding='utf-8'))


def open_browser():
    """Start a browser after waiting for half a second."""
    def _open_browser():
        webbrowser.open('http://localhost:%s/%s' % (PORT, FILE))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()
 

def start_server():
    """Start the server."""
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()


if __name__ == "__main__":
    open_browser()
    start_server()