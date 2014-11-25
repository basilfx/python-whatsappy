from whatsappy.stream import Reader, Writer, MessageIncomplete, EndOfStream
from whatsappy.encryption import Encryption
from whatsappy.callbacks import Callback, LoginSuccessCallback, \
    LoginFailedCallback
from whatsappy.node import Node
from whatsappy.exceptions import ConnectionError, StreamError, LoginError
from whatsappy import utils

from select import select
from time import time

import sys
import socket
import logging
import collections

CHATSTATE_NS = "http://jabber.org/protocol/chatstates"
CHATSTATES = ("active", "inactive", "composing", "paused", "gone")

# Remote server settings
HOST = "c.whatsapp.net"
PORT = 443

# Protocol settings
PROTOCOL_DEVICE = "Android"
PROTOCOL_VERSION = "2.11.378";
PROTOCOL_USER_AGENT = "WhatsApp/2.11.378 Android/4.2 Device/GalaxyS3"

# Other settings
TIMEOUT = 0.1
ALIVE_INTERVAL = 30

# Logger instance
logger = logging.getLogger(__name__)

class Client(object):
    SERVER = "s.whatsapp.net"
    GROUPHOST = "g.us"

    def __init__(self, number, secret, nickname=None):
        self.number = number
        self.secret = secret
        self.nickname = nickname

        self.auto_receipt = True

        self.debug = False
        self.debug_out = lambda x: sys.stdout.write(x + "\n")
        self.socket = None

        self.account_info = None
        self.counter = 0

        self.last_ping = time()

        self.callbacks = collections.defaultdict(list)

    def _connect(self):
        logger.info("Connecting to %s:%d", HOST, PORT)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.connect((HOST, PORT))
        except socket.error as e:
            raise ConnectionError("Unable to connect to remote server")

    def _disconnect(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

        self.account_info = None
        self.counter = 0

    def _disconnected(self):
        self._disconnect()
        raise ConnectionError("Socket closed by remote party")

    def _write(self, buf, encrypt=None):
        if isinstance(buf, Node):
            if self.debug:
                self.debug_out(utils.dump_xml(buf, prefix="xml >>  "))

            buf, plain = self.writer.node(buf, encrypt)
        else:
            plain = buf

        if self.debug:
            self.debug_out(utils.dump_bytes(plain, prefix="pln >>  "))

        if self.debug:
            self.debug_out(utils.dump_bytes(buf, prefix="    >>  "))

        try:
            self.socket.sendall(buf)
        except socket.error:
            self._disconnected()

    def _read(self, limit=4096):
        # See if there's data available to read.
        try:
            r, w, x, = select([self.socket], [], [], TIMEOUT)
        except (TypeError, socket.error):
            self._disconnected()

        if self.socket in r:
            # Receive any available data, update Reader's buffer
            try:
                buf = self.socket.recv(limit)
            except socket.error:
                buf = None

            # Check for end of stream
            if not buf:
                self._disconnected()

            if self.debug:
                self.debug_out(utils.dump_bytes(buf, prefix="    <<  "))

            self.reader.data(buf)

        # Process received nodes
        nodes = []

        while True:
            try:
                node, plain = self.reader.read()

                if self.debug:
                    self.debug_out(utils.dump_bytes(plain, prefix="pln <<  "))

                if self.debug:
                    self.debug_out(utils.dump_xml(node, prefix="xml <<  "))

                nodes.append(node)
            except MessageIncomplete:
                break
            except EndOfStream:
                self._disconnected()
                break

        # Return complete nodes
        return nodes

    def _challenge(self, node):
        encryption = Encryption(self.secret, node.data)
        logger.debug("Session Keys: %s", [ key.encode("hex") for key in encryption.keys ])

        self.writer.encrypt = encryption.encrypt
        self.reader.decrypt = encryption.decrypt

        response = "%s%s%s" % (self.number, node.data, utils.timestamp())

        response = Node("response", xmlns="urn:ietf:params:xml:ns:xmpp-sasl",
            data=encryption.encrypt(response, False))

        self._write(response, encrypt=False)
        self._incoming()

    def _iq(self, node):
        # Node without children could be a ping reply
        if len(node.children) == 0:
            return

        iq = node.children[0]
        if node["type"] == "get" and iq.name == "ping":
            self._write(Node("iq", to=self.SERVER, id=node["id"], type="result"))
        elif node["type"] == "result": # and iq.name == "query":
            #self.messages.append(node)
            pass
        else:
            logger.debug("Unknown iq message received: %s", node["type"])

    def _clear_dirty(self, *categories):
        nodes = []

        for category in categories:
            nodes.append(Node("clean", type=category))

        self._write(Node("iq", id=self._msgid("cleardirty"), type="set",
            to=self.SERVER, xmlns="urn:xmpp:whatsapp:dirty", children=nodes))

    def _ib(self, node):
        for child in node.children:
            if child.name == "dirty":
                self._clear_dirty(child["type"])
            elif child.name == "offline":
                pass
            else:
                logger.debug("No 'ib' handler for %s implemented", child.name)

    def _notification(self, node):
        out = Node("ack", to=node["from"], id=node["id"], type=node["type"])

        # Class is reserved keyword.
        out["class"] = "notification"

        if node["to"]:
            out["from"] = node["to"]
        if node["participant"]:
            out["participant"] = node["participant"]

        self._write(out)

    def _incoming(self):
        nodes = self._read()

        for node in nodes:
            if node.name == "challenge":
                self._challenge(node)
            elif node.name == "message":
                if self.auto_receipt:
                    self._receipt(node)
            elif node.name == "ib":
                self._ib(node)
            elif node.name == "iq":
                self._iq(node)
            elif node.name == "notification":
                self._notification(node)
            elif node.name in ("start", "stream:features"):
                pass
            elif node.name == "stream:error":
                raise StreamError(node.children[0].name)

            # Handle callbacks
            if node.name in self.callbacks:
                for callback in self.callbacks[node.name]:
                    if callback.test(node):
                        callback(node)

    def _msgid(self, prefix):
        """
        Generate a unique message ID.
        """

        return "%s-%s-%d" % (prefix, utils.timestamp(), self.counter)

    def _jid(self, number):
        """
        Return Jabber ID for given number.
        """

        if "@" not in number:
            if "-" in number:
                return number + "@" + self.GROUPHOST
            else:
                return number + "@" + self.SERVER

        # Number already formatted
        return number

    def _message(self, to, node, group=False):
        msgid = self._msgid("message")
        to = self._jid(to)

        x = Node("x", xmlns="jabber:x:event", children=Node("server"))
        notify = Node("notify", xmlns="urn:xmpp:whatsapp", name=self.nickname)
        request = Node("request", xmlns="urn:xmpp:receipts")

        message = Node("message", to=to, type="text", id=msgid,
            t=utils.timestamp(), children=[x, notify, request, node])

        return msgid, message

    def _receipt(self, node):
        self._write(Node("receipt", type="read", to=node["from"], id=node["id"],
            t=utils.timestamp()))

    def register_callback(self, *callbacks):
        for callback in callbacks:
            self.callbacks[callback.name].append(callback)

    def unregister_callback(self, *callbacks):
        for callback in callbacks:
            self.callbacks[callback.name].remove(callback)

    def register_callback_and_wait(self, *callbacks):
        self.register_callback(*callbacks)
        self.wait_for_callback(*callbacks)

    def wait_for_callback(self, *callbacks):
        called = None

        # Wait for one of the callbacks to happen
        while not called:
            for callback in callbacks:
                if callback.called:
                    called = callback
                    break
            else:
                self._incoming()

        # Unregister all callbacks
        self.unregister_callback(*callbacks)

        # Process result
        if isinstance(called.result, Exception):
            raise called.result

        return called.result

    def service_loop(self):
        # Handle incoming data
        self._incoming()

        # Send a ping once in a while if keep alive and still connected
        if (time() - self.last_ping) > ALIVE_INTERVAL:
            self.presence("active")
            self.last_ping = time()

    def disconnect(self):
        self._disconnect()
        logger.debug("Disconnected by user")

    def connect(self):
        assert self.socket is None

        self.reader = Reader()
        self.writer = Writer()

        self._connect()

        buf = self.writer.start_stream(self.SERVER, "%s-%s-%d" %
            (PROTOCOL_DEVICE, PROTOCOL_VERSION, PORT))
        self._write(buf)

        features = Node("stream:features")
        #features.add(Node("receipt_acks"))
        #features.add(Node("w:profile:picture", type="all"))
        #features.add(Node("status"))
        #features.add(Node("notification", type="participant"))
        #features.add(Node("groups"))
        self._write(features)

        self._write(Node("auth", mechanism="WAUTH-2", user=self.number))

        def on_success(node):
            logger.info("Login successfull")
            self.account_info = node.attributes

            self._write(Node("presence", name=self.nickname))

        def on_failure(node):
            self._disconnect()
            raise LoginError("Incorrect number and/or secret.")

        # Wait for either success, or failure
        self.register_callback_and_wait(LoginSuccessCallback(on_success),
            LoginFailedCallback(on_failure))

    def last_seen(self, number):
        msgid = self._msgid("lastseen")

        iq = Node("iq", type="get", id=msgid)
        iq["from"] = self.number + "@" + self.SERVER
        iq["to"] = number + "@" + self.SERVER
        iq.add(Node("query", xmlns="jabber:iq:last"))

        self._write(iq)

        def on_iq(node):
            if node["id"] != msgid:
                return
            if node["type"] == "error":
                return StreamError(node.child("error").children[0].name)
            return int(node.child("query")["seconds"])

        callback = Callback("iq", on_iq)
        self.register_callback_and_wait(callback)

    def message(self, number, text):
        msgid, message = self._message(number, Node("body", data=text))
        self._write(message)
        return msgid

    def group_message(self, group, text):
        msgid, message = self._message(group, Node("body", data=text), True)
        self._write(message)
        return msgid

    def presence(self, state):
        self._write(Node("presence", type=state))

    def chatstate(self, number, state):
        if state not in CHATSTATES:
            raise ValueError("Invalid chatstate: %r" % state)

        node = Node(state, xmlns=CHATSTATE_NS)
        msgid, message = self._message(number, node)
        self._write(message)
        return msgid

    def image(self, number, url, basename, size, thumbnail = None):
        """
        Send an image to a contact.

        The URL should be publicly accessible
        Basename does not have to match Url
        Size is the size of the image, in bytes
        Thumbnail should be a Base64 encoded JPEG image, if provided.
        """
        # TODO: Where does WhatsApp upload images?
        # PNG thumbnails are apparently not supported

        media = Node("media", xmlns="urn:xmpp:whatsapp:mms", type="image",
                     url=url, file=basename, size=size, data=thumbnail)
        msgid, message = self._message(number, media)
        self._write(message)
        return msgid

    def audio(self, number, url, basename, size, attributes):
        valid_attributes = ("abitrate", "acodec", "asampfmt", "asampfreq",
            "duration", "encoding", "filehash", "mimetype")

        for name, value in attributes.iteritems:
            if name not in valid_attributes:
                raise ValueError("Unknown audio attribute: %r" % name)

        media = Node("media", xmlns="urn:xmpp:whatsapp:mms", type="audio",
                     url=url, file=basename, size=size, **attributes)
        msgid, message = self._message(number, media)

        self._write(message)
        return msgid

    def location(self, number, latitude, longitude):
        """
        Send a location update to a contact.
        """

        media = Node("media", xmlns="urn:xmpp:whatsapp:mms", type="location",
            latitude=latitude, longitude=longitude)
        msgid, message = self._message(number, media)

        self._write(message)
        return msgid

    def vcard(self, number, name, data):
        """
        Send a vCard to a contact. WhatsApp will display the photo if it is
        embedded in the vCard data as base64 encoded JPEG.
        """

        vcard = Node("vcard", name=name, data=data)

        media = Node("media", children=[vcard], xmlns="urn:xmpp:whatsapp:mms",
            type="vcard", encoding="text")
        msgid, message = self._message(number, media)

        self._write(message)
        return msgid