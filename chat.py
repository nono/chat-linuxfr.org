#!/usr/bin/env python
# -*- coding: utf-8 -*-
import daemon
import os.path
import sys
import string
import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web


class Application(tornado.web.Application):
    def __init__(self, debug):
        handlers = [
            (r"/", MainHandler)
        ]
        settings = dict(
            debug=debug,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static")
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


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

