import raspberry
import threading
import webbrowser
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

PORT = 8000


class Handler(http.server.SimpleHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()


    def do_POST(self):
        """Handle POST request."""
        request_path = self.path

        # print("\n----- Request Start ----->\n")
        print("request_path: %s", request_path)

        request_headers = self.headers
        content_length = request_headers.get('content-length')
        length = int(content_length) if content_length else 0
        json_content_string = self.rfile.read(length)

        # print("length :", length)

        print("request_headers: %s" % request_headers)
        print("content: %s" % json_content_string)
        # print("<----- Request End -----\n")

        json_content = json.loads(json_content_string) if json_content_string else {}   # Dictionary containing data sent in POST request

        print("action: %s" % json_content["action"])

        sensor_data = raspberry.read_sensors()

        json_response_string = json.dumps(sensor_data)

        self._set_headers()
        self.wfile.write(json_response_string.encode(encoding='utf-8'))

    """
    def do_GET(self):
        request_path = self.path
        query_string = urlparse(request_path).query
        query_object = parse_qs(query_string)  # Dictionary of param name: value

        # print("\n----- Request Start ----->\n")
        print("request_path : %s", request_path)
        print("query_components : %s", query_string)

        request_headers = self.headers

        print("request_headers : %s" % request_headers)
        # print("<----- Request End -----\n")

        sensor_data = raspberry.read_sensors()

        json_string = json.dumps(sensor_data)

        self._set_headers()
        self.wfile.write(json_string.encode(encoding='utf-8'))
    """


def open_browser():
    """Start a browser after waiting for half a second."""
    def _open_browser():
        webbrowser.open('http://localhost:%s/' % (PORT))
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