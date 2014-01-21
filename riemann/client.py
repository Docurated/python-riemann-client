"""Riemann protocol buffer client"""

from __future__ import absolute_import

import socket

import riemann.riemann_pb2
import riemann.transport


class Client(object):
    """An abstract Riemann client"""

    def __init__(self, transport=None):
        if transport is None:
            transport = riemann.transport.TCPTransport()
        self.transport = transport

    def __enter__(self):
        self.transport.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.transport.disconnect()

    @staticmethod
    def create_event(data):
        """Creates an Event from a dictionary"""
        data.setdefault('host', socket.gethostname())
        data.setdefault('tags', list())
        event = riemann.riemann_pb2.Event()
        event.tags.extend(data.pop('tags'))
        for name, value in data.items():
            if value is not None:
                setattr(event, name, value)
        return event

    def send_event(self, event):
        """Wraps an event in a message and sends it to Riemann"""
        message = riemann.riemann_pb2.Msg()
        message.events.extend([event])
        self.transport.send(message)
        return event

    def event(self, **data):
        """Sends an event"""
        return self.send_event(self.create_event(data))

    @staticmethod
    def create_dict(event):
        """Creates a dict from an Event"""
        return {
            'time': event.time,
            'state': event.state,
            'host': event.host,
            'description': event.description,
            'service': event.service,
            'tags': list(event.tags),
            'ttl': event.ttl,
            'metric_f': event.metric_f,
            'metric_d': event.metric_d,
            'metric_sint64': event.metric_sint64
        }

    def send_query(self, query):
        message = riemann.riemann_pb2.Msg()
        message.query.string = query
        self.transport.send(message)
        return self.transport.recv()

    def query(self, query):
        response = self.send_query(query)
        return [self.create_dict(e) for e in response.events]


class QueuedClient(Client):
    """A queued Riemann client"""

    def __init__(self, *args, **kwargs):
        super(QueuedClient, self).__init__(*args, **kwargs)
        self.queue = riemann.riemann_pb2.Msg()

    def flush(self):
        """Sends the waiting message to Riemann"""
        self.transport.send(self.queue)
        self.queue = riemann.riemann_pb2.Msg()

    def send_event(self, event):
        self.queue.events.extend([event])
        return event
