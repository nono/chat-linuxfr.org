#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import daemon
import hashlib
import logging
import os.path
import sys
import string
import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web
import uuid


class Application(tornado.web.Application):
    def __init__(self, debug):
        handlers = [
            (r"/chat/new", NewMessageHandler),
            (r"/chat/chan/([^/]+)", ChanHandler),
        ]
        settings = dict(
            debug=debug,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static")
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MessageMixin(object):
    waiters = collections.defaultdict(list)
    cache = []
    cache_size = 20

    def wait_for_messages(self, chan, callback, cursor):
        mm = MessageMixin
        if cursor:
            index = 0
            for i in xrange(len(mm.cache)):
                index = len(mm.cache) - i - 1
                if mm.cache[index]["id"] == cursor: break
            recent = [msg for msg in mm.cache[index + 1:] if msg["chan"] == chan]
            if recent:
                callback(recent)
                return
        mm.waiters[chan].append(callback)

    def new_message(self, chan, message):
        mm = MessageMixin
        for callback in mm.waiters[chan]:
            try:
                callback([message])
            except:
                logging.error("Error in waiter callback", exc_info=True)
        mm.waiters[chan] = []
        mm.cache.append(message)
        if len(mm.cache) > self.cache_size:
            mm.cache = mm.cache[-self.cache_size:]


class NewMessageHandler(tornado.web.RequestHandler, MessageMixin):
    def post(self):
        chan = self.get_argument("chan")
        sha1 = hashlib.sha1(chan).hexdigest()
        message = {
                "id":   self.get_argument("id"),
                "type": self.get_argument("type"),
                "msg":  self.get_argument("msg"),
                "chan": sha1
        }
        self.new_message(sha1, message)
        self.write("OK")


class ChanHandler(tornado.web.RequestHandler, MessageMixin):
    @tornado.web.asynchronous    
    def post(self, chan):
        self.wait_for_messages(chan,
                               self.async_callback(self.on_new_messages),
                               self.get_argument("cursor", None))

    def on_new_messages(self, messages):
        if not self.request.connection.stream.closed():
            self.finish(dict(messages=messages))


if __name__ == "__main__":
    port = 8000
    debug = True
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        debug = False
        log = open('tornado.' + str(port) + '.log', 'a+')
        ctx = daemon.DaemonContext(
                stdout=log,
                stderr=log,
                working_directory='.'
        )
        ctx.open()
    http_server = tornado.httpserver.HTTPServer(Application(debug))
    http_server.listen(port, '127.0.0.1')
    tornado.ioloop.IOLoop.instance().start()

