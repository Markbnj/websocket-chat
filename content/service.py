"""Chat client content service.

..  module:: service.py
    :platform: linux
    :synopsis: Implements the http endpoint handler for static content.

..  moduleauthor:: Mark Betz <betz.mark@gmail.com>

"""
import logging
from config import settings
from tornado import ioloop, web


log_level = eval("logging.{}".format(settings["logLevel"]))
logger = logging.getLogger()
logger.setLevel(log_level)
if not [handler for handler in logger.handlers if isinstance(handler,logging.StreamHandler)]:
    sh = logging.StreamHandler()
    sh.setLevel(log_level)
    logger.addHandler(sh)


class CustomerRequestHandler(web.RequestHandler):
    """Handles http GET requests to /

    Returns the customer page from static/html
    """
    def get(self):
        self.render("static/html/customer.html")


class OperatorRequestHandler(web.RequestHandler):
    """Handles http GET requests to /operator/

    Returns the operator page from /static/html.

    """
    def get(self):
        self.render("static/html/operator.html")


app = web.Application([
    (r'/operator/', OperatorRequestHandler),
    (r'/images/(.*)', web.StaticFileHandler, {'path':'./static/images/'}),
    (r'/styles/(.*)', web.StaticFileHandler, {'path':'./static/css/'}),
    (r'/', CustomerRequestHandler)
])


if __name__ == "__main__":
    app.listen(settings['listenOnPort'], address=settings['listenOnIP'])
    ioloop.IOLoop.instance().start()