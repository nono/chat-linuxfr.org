#!/usr/bin/env python
# -*- coding: utf-8 -*-
import daemon
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
    waiters = []
    cache = []
    cache_size = 200

    def wait_for_messages(self, callback, cursor=None):
        mm = MessageMixin
        if cursor:
            index = 0
            for i in xrange(len(mm.cache)):
                index = len(mm.cache) - i - 1
                if mm.cache[index]["id"] == cursor: break
            recent = mm.cache[index + 1:]
            if recent:
                callback(recent)
                return
        mm.waiters.append(callback)

    def new_messages(self, messages):
        mm = MessageMixin
        logging.info("Sending new message to %r listeners", len(mm.waiters))
        for callback in mm.waiters:
            try:
                callback(messages)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        mm.waiters = []
        mm.cache.extend(messages)
        if len(mm.cache) > self.cache_size:
            mm.cache = mm.cache[-self.cache_size:]



# TODO Protect this handler with a secret
class NewMessageHandler(tornado.web.RequestHandler, MessageMixin):
    def post(self):
        message = {
                "id":   str(uuid.uuid4()),
                "chan": self.get_argument("chan"),
                "type": self.get_argument("type"),
                "user": self.get_argument("user"),
                "msg":  self.get_argument("msg"),
        }
        self.new_messages([message])
        self.write("OK")


class ChanHandler(tornado.web.RequestHandler, MessageMixin):
    @tornado.web.asynchronous    
    def post(self, chan):
        cursor = self.get_argument("cursor", None)
        self.wait_for_messages(self.async_callback(self.on_new_messages),
                               cursor=cursor)

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
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

