"""Perform an over-the-air update if internet is available"""

import subprocess
import socket

def has_internet(host="8.8.8.8", port=53, timeout=3):
    """Check if we have a working internet connection
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        #print(ex)
        return False


def run():
    """Try running an over-the-air update"""
    if (has_internet()):
        try:
            process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
            output = process.communicate()[0]
            return True
        except Exception: pass
    return False
    