# -*- coding: utf-8 -*-
# WakeOnLAN-API
# Project by https://github.com/rix1337

"""WakeOnLAN-API.

Usage:
  web.py        [--port=<PORT>]

Options:
  --port=<PORT>             Set the listen port
"""

from docopt import docopt
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from wakeonlan import send_magic_packet

devices = {
    'philip': {'mac': '58:11:22:C9:06:69', 'ip_address': '192.168.0.75'}
}


def wake_device(device_name):
    if device_name in devices:
        mac, ip = devices[device_name].values()
        send_magic_packet(mac, ip_address=ip)
        print('Magic Packet Sent')
        return True
    else:
        print('Device Not Found')
        return False


def app_container(port):
    app = Flask(__name__)

    @app.route("/wol/<device>", methods=['GET'])
    def myjd_stop(device):
        if request.method == 'GET':
            try:
                wake_device(device)
                return "Success", 200
            except:
                return "Failed", 400
        else:
            return "Failed", 405

    http_server = WSGIServer(('0.0.0.0', port), app)
    http_server.serve_forever()


def main():
    arguments = docopt(__doc__, version='WakeOnLAN-API')

    if arguments['--port']:
        port = int(arguments['--port'])
    else:
        port = 8080
    app_container(port)
