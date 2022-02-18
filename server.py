"""Main thread which spawns a web server and a browser, and starts the sensor reading thread"""

import io
import os
import sys
import threading
import http.server
import socketserver
import json
import webbrowser

import raspberry


PORT = 8000

# Write errors to a log file
file_path = './logs/errors.txt'
os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create logs directory if not exist
sys.stderr = open(file_path, 'w')

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

        action = json_content["action"]
        payload = json_content["payload"] if "payload" in json_content else None

        print("Action: %s" % action)
        print("Payload: %s" % payload)

        response = raspberry.do_action( action, payload )

        json_response_string = json.dumps(response)

        self._set_headers()
        self.wfile.write(json_response_string.encode(encoding='utf-8'))


def is_raspberrypi():
    """Check whether this code is running on a Raspberry Pi or not"""
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            file_content = m.read().lower()
            if 'raspberry pi' in file_content: return True
    except Exception: pass
    return False


def open_browser():
    """Start a browser showing the dashboard after waiting for half a second."""
    def _open_browser():
        if is_raspberrypi() == True:
            os.system('chromium-browser --noerrdialogs --disable-infobars --check-for-update-interval=31536000 --kiosk "http://localhost:%s/" & ' % (PORT))
        else:
            webbrowser.open('http://localhost:%s/' % (PORT))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()
 

def start_server():
    """Start the server."""
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()


def init_raspberry():
    """Initialize the Raspberry Pi sensors"""
    thread = threading.Timer(0.5, raspberry.init)
    thread.start()


if __name__ == "__main__":
    init_raspberry()
    open_browser()
    start_server()