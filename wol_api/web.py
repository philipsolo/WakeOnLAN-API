# -*- coding: utf-8 -*-
# !/usr/bin/env python3
import datetime
import json
from collections import Counter
import transmissionrpc
from docopt import docopt
from flask import Flask, make_response, request
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from wakeonlan import send_magic_packet

METRIC_PREFIX = 'transmission'
PORT = 29091
# RPC direct query to obtain only torrents status
TORRENTS_QUERY = json.dumps({"method": "torrent-get", "arguments": {"fields": ["status"]}})
# the possible states a torrent can have
# source: https://github.com/transmission/transmission/blob/master/libtransmission/transmission.h#L1649-L1659
STATUS = {
    0: 'paused',
    1: 'queued_to_check',
    2: 'checking',
    3: 'queued_to_download',
    4: 'downloading',
    5: 'queued_to_seed',
    6: 'seeding',
}

TRANSMISSION_HOST = '192.168.0.18'
TRANSMISSION_PORT = '9091'
TRANSMISSION_USERNAME = 'root'
TRANSMISSION_PASSWORD = 'solomon1'

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

    @app.route('/')
    def homepage():
        """
        https://prometheus.io/docs/instrumenting/writing_exporters/#landing-page
        """
        landing_page = f"""A simple Prometheus exporter for Transmission
    https://github.com/sandrotosi/simple-transmission-exporter

    metric page: {request.host_url}metrics
    """
        response = make_response(landing_page, 200)
        response.mimetype = "text/plain"
        return response

    @app.route('/metrics')
    def metrics():
        _return = []
        start = datetime.datetime.now()
        tc = transmissionrpc.Client(address=TRANSMISSION_HOST, port=TRANSMISSION_PORT, user=TRANSMISSION_USERNAME,
                                    password=TRANSMISSION_PASSWORD)
        stats = tc.session_stats()

        for metric in ['downloadSpeed', 'download_dir_free_space', 'uploadSpeed']:
            _metric_name = f'{METRIC_PREFIX}_{metric}'
            _return.append((f'# TYPE {_metric_name}', 'gauge'))
            _return.append((_metric_name, stats._fields[metric].value))

        for metric in ['cumulative_stats', 'current_stats']:
            for item in ['downloadedBytes', 'filesAdded', 'secondsActive', 'sessionCount', 'uploadedBytes']:
                _metric_name = f'{METRIC_PREFIX}_{metric}_{item}'
                _return.append((f'# TYPE {_metric_name}', 'counter'))
                _return.append((_metric_name, stats._fields[metric].value[item]))

        # obtain torrents status counters
        # we need to query directly the RPC endpoint (still using transmissionrpc module for actually running the query)
        # as `get_torrents()` gets extremely slow for if the number of torrent is too high
        torrents = json.loads(tc._http_query(TORRENTS_QUERY))
        # initialize a counter with all the possible statuses
        status = Counter({1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0})
        status.update(y['status'] for y in torrents['arguments']['torrents'])
        for status_id, status_text in STATUS.items():
            _metric_name = f'{METRIC_PREFIX}_status_{status_text}'
            _return.append((f'# TYPE {_metric_name}', 'gauge'))
            _return.append((_metric_name, status[status_id]))

        # https://prometheus.io/docs/instrumenting/writing_exporters/#metrics-about-the-scrape-itself
        _metric_name = f'{METRIC_PREFIX}_scrape_duration_seconds'
        _return.append((f'# TYPE {_metric_name}', 'gauge'))
        _return.append((_metric_name, (datetime.datetime.now() - start).total_seconds()))

        response = make_response('\n'.join([f'{x[0]} {x[1]}' for x in _return]), 200)
        response.mimetype = "text/plain"
        return response

    @app.route("/wol/<device>", methods=['GET'])
    def myjd_stop(device):
        if request.method == 'GET':
            try:
                if wake_device(device):
                    return "Success", 200
            except Exception as e:
                print(e)
            return "Failed", 500
        else:
            return "Failed", 405

    http_server = WSGIServer(('0.0.0.0', port), app)
    http_server.serve_forever()


def main():
    arguments = docopt(__doc__, version='WakeOnLAN-API')

    if arguments['--port']:
        port = int(arguments['--port'])
    else:
        port = 8081
    app_container(port)
