from whatsappy.stream import Reader, Writer, MessageIncomplete, EndOfStream
from whatsappy.encryption import Encryption
from whatsappy.callbacks import Callback
from whatsappy.node import Node
from whatsappy.exceptions import ConnectionError, LoginError

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
PING_INTERVAL = 30

# Logger instance
logger = logging.getLogger(__name__)

class Client(object):
    SERVER = "s.whatsapp.net"
    GROUPHOST = "g.us"

    def __init__(self, number, secret, nickname=None, keep_alive=True):
        self.number = number
        self.secret = secret
        self.nickname = nickname

        self.debug = False
        self.socket = None

        self.account_info = None

        self.last_ping = time()
        self.keep_alive = keep_alive

        self.callbacks = collections.defaultdict(list)

    def _connect(self):
        logger.info("Connecting to %s:%d", HOST, PORT)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.connect((HOST, PORT))
        except socket.error as e:
            logger.error("Unable to connect: %s", e)
            raise ConnectionError("Unable to connect to remote server")

    def _disconnected(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

        self.account_info = None

        logger.error("Socket closed by remote party")
        raise ConnectionError("Socket closed by remote party")

    def _write(self, buf, encrypt=None):
        if isinstance(buf, Node):
            if self.debug:
                print buf.to_xml(indent="xml > ")
            buf = self.writer.node(buf, encrypt)

        if self.debug:
            self.dump("    >", buf)

        if self.socket:
            self.socket.sendall(buf)

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
                self.dump("    <", buf)

            self.reader.data(buf)

        # Process received nodes
        nodes = []

        while True:
            try:
                node = self.reader.read()

                if self.debug:
                    print node.to_xml(indent="xml < ")
                nodes.append(node)
            except MessageIncomplete:
                break
            except EndOfStream:
                self._disconnected()
                break

        # Return complete nodes
        return nodes

    def dump(self, prefix, bytes):
        length = len(bytes)
        for i in range(0, length, 16):
            hexstr = bytestr = ""
            for j in range(0, 16):
                if i + j < length:
                    b = ord(bytes[i + j])
                    hexstr  += "%02x " % b
                    bytestr += bytes[i + j] if 0x20 <= b < 0x7F else "."
                else:
                    hexstr  += "   "

                if (j % 4) == 3:
                    hexstr += " "

            print prefix + " " + hexstr + bytestr

    def _challenge(self, node):
        encryption = Encryption(self.secret, node.data)
        logger.debug("Session Keys: %s", [ key.encode("hex") for key in encryption.keys ])

        self.writer.encrypt = encryption.encrypt
        self.reader.decrypt = encryption.decrypt

        response = Node("response", xmlns="urn:ietf:params:xml:ns:xmpp-sasl",
                        data=encryption.authenticate(self.number))

        self._write(response, encrypt=False)
        self._incoming()

    def _ping(self):
        msgid = self._msgid()

        message = Node("iq", id=msgid, type="get", to=self.SERVER)
        message.add(Node("ping", xmlns="w:p"))

        self._write(message)

    def _received(self, node):
        request = node.child("request")
        if request is None or request["xmlns"] != "urn:xmpp:receipts":
            return

        message = Node("message", to=node["from"], id=node["id"], type="chat")
        message.add(Node("received", xmlns="urn:xmpp:receipts"))

        self._write(message)

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

            if self.debug:
                print node.to_xml(indent="  ") + "\n"

    def _incoming(self):
        nodes = self._read()

        for node in nodes:
            if self.debug:
                print ">>>", node.name

            if node.name == "challenge":
                self._challenge(node)
            elif node.name == "message":
                #self.messages.append(node)
                self._received(node)
            elif node.name == "iq":
                self._iq(node)
            elif node.name == "stream:error":
                raise Exception(node.children[0].name)

            if self.debug:
                print str(node)[0:500]

            if node.name in self.callbacks:
                for callback in self.callbacks[node.name]:
                    if callback.test(node):
                        callback(node)

            #elif node.name in ("start", "stream:features"):
            #    pass # Not interesting
            #elif self.debug:
            #    print "Ignorning message"
            #    print node.to_xml(indent="  ") + "\n"

    def _msgid(self):
        return "msg-%d" % (time() * 1000)

    def register_callback(self, callback):
        # Add callback to the other callbacks
        self.callbacks[callback.name].append(callback)

    def register_callbacks(self, *callbacks):
        for callback in callbacks:
            self.register_callback(callback)

    def register_callback_and_wait(self, callback):
        self.register_callback(callback)
        self.wait_for_callback(callback)

    def unregister_callback(self, callback):
        self.callbacks[callback.name].remove(callback)

    def wait_for_callback(self, callback):
        while not callback.called:
            self._incoming()

        self.unregister_callback(callback)

        if isinstance(callback.result, Exception):
            raise callback.result

        return callback.result

    def wait_for_any_callback(self, callbacks):
        called = None
        while called is None:
            for callback in callbacks:
                if callback.called:
                    called = callback
                    break
            else:
                self._incoming()

        for callback in callbacks:
            self.unregister_callback(callback)

        if isinstance(called.result, Exception):
            raise called.result

        return called.result

    def service_loop(self):
        # Handle incoming data
        self._incoming()

        # Send a ping once in a while if keep alive and still connected
        if self.keep_alive:
            if (time() - self.last_ping) > PING_INTERVAL:
                self._ping()
                self.last_ping = time()

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None

        self.account_info = None
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

        auth = Node("auth", xmlns="urn:ietf:params:xml:ns:xmpp-sasl",
            mechanism="WAUTH-2", user=self.number)
        self._write(auth)

        def on_success(node):
            logger.info("Login successfull")
            self.account_info = node.attributes

            presence = Node("presence")
            presence["name"] = self.nickname
            self._write(presence)

        # Create new callback
        callback = Callback("success", on_success)
        self.register_callback_and_wait(callback)

        # Raise an exception in case credentials are wronge
        if self.account_info is None:
            raise LoginError("Incorrect number and/or secret")

    def last_seen(self, number):
        msgid = self._msgid()

        iq = Node("iq", type="get", id=msgid)
        iq["from"] = self.number + "@" + self.SERVER
        iq["to"] = number + "@" + self.SERVER
        iq.add(Node("query", xmlns="jabber:iq:last"))

        self._write(iq)

        def on_iq(node):
            if node["id"] != msgid:
                return
            if node["type"] == "error":
                return Exception(node.child("error").children[0].name)
            return int(node.child("query")["seconds"])

        callback = Callback("iq", on_iq)
        self.register_callback_and_wait(callback)

    def _message(self, to, node, group=False):
        msgid = self._msgid()

        message = Node("message", type="chat", id=msgid)
        message["to"] = to + "@" + (self.GROUPHOST if group else self.SERVER)

        x = Node("x", xmlns="jabber:x:event")
        x.add(Node("server"))

        message.add(x)
        message.add(node)

        return msgid, message

    def message(self, number, text):
        msgid, message = self._message(number, Node("body", data=text))
        self._write(message)
        return msgid

    def group_message(self, group, text):
        msgid, message = self._message(group, Node("body", data=text), True)
        self._write(message)
        return msgid

    def chatstate(self, number, state):
        if state not in CHATSTATES:
            raise Exception("Invalid chatstate: %r" % state)

        node = Node(state, xmlns=CHATSTATE_NS)
        msgid, message = self._message(number, node)
        self._write(message)
        return msgid

    def image(self, number, url, basename, size, thumbnail = None):
        """
        Send an image to a contact.
        Url should be publicly accessible
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

        vcard = Node("vcard", data=data)
        vcard["name"] = name

        media = Node("media", children=[vcard], xmlns="urn:xmpp:whatsapp:mms",
            type="vcard", encoding="text")
        msgid, message = self._message(number, media)

        self._write(message)
        return msgid