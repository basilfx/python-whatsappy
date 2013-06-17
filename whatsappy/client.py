import sys

import socket
from select import select
from time import time

from .stream import Reader, Writer, MessageIncomplete, EndOfStream
from .encryption import Encryption
from .node import Node
from .callbacks import Callback

CHATSTATE_NS = "http://jabber.org/protocol/chatstates"
CHATSTATES = "active", "inactive", "composing", "paused", "gone"

class Client(object):
    HOST = "c.whatsapp.net"
    PORTS = [443, 5222]
    TIMEOUT = 0.1 # seconds

    SERVER = "s.whatsapp.net"
    REALM = "s.whatsapp.net"
    GROUPHOST = "g.us"
    DIGEST_URI = "xmpp/s.whatsapp.net"

    VERSION = "Android-2.8.5732"

    PING_INTERVAL = 60 # seconds

    def __init__(self, number, secret, nickname=None, keep_alive=True):
        self.number = number
        self.secret = secret
        self.nickname = nickname

        self.addrinfo = None
        self.portindex = 0

        self.debug = False
        self.socket = None
        self.reader = Reader()
        self.writer = Writer()

        self.messages = []
        self.account_info = None
        self.last_ping = time()
        self.keep_alive = keep_alive

        self.callbacks = {}

    def _connect(self, tries=3):
        if not self.addrinfo:
            self.addrinfo = socket.getaddrinfo(self.HOST, self.PORTS[self.portindex], 0, 0, socket.SOL_TCP)
            self.portindex = (self.portindex + 1) % len(self.PORTS)


        last_ex = None
        for i in range(tries):
            family, socktype, proto, canonname, sockaddr = self.addrinfo.pop()

            if self.debug:
                print >>sys.stderr, "Connecting to %s:%d" % sockaddr

            self.socket = socket.socket(family, socktype, proto)
            try:
                self.socket.connect(sockaddr)
                break
            except socket.error, ex:
                if self.debug:
                    print >>sys.stderr, "Try %d/%d: %s" % (i + 1, tries, ex)
                last_ex = ex
        else:
            raise last_ex

    def _write(self, buf, encrypt=None):
        if isinstance(buf, Node):
            if self.debug:
                sys.stderr.write(buf.toxml(indent="xml > ") + "\n")
            buf = self.writer.node(buf, encrypt)

        if self.debug: self.dump("    >", buf)
        self.socket.sendall(buf)

    def _read(self, nbytes = 4096):
        assert self.socket is not None

        # See if there's data available to read
        r, w, x, = select([self.socket], [], [], self.TIMEOUT)
        if self.socket in r:
            # receive any available data, update Reader's buffer
            buf = self.socket.recv(nbytes)
            if not buf:
                if self.debug:
                    print >>sys.stderr, "Socket Closed"
                self.socket.close()
                self.socket = None

            if self.debug: self.dump("    <", buf)
            self.reader.data(buf)

        nodes = []
        while True:
            try:
                node = self.reader.read()
                if self.debug:
                    sys.stderr.write(node.toxml(indent="xml < ") + "\n")
                nodes.append(node)
            except MessageIncomplete:
                break
            except EndOfStream:
                if self.debug:
                    print >>sys.stderr, "Connection Closed"
                self.socket.close()
                self.socket = None
                break
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

            print >>sys.stderr, prefix + " " + hexstr + bytestr

    def _challenge(self, node):
        encryption = Encryption(self.number, self.secret, node.data)
        self.writer.encrypt = encryption.encrypt
        self.reader.decrypt = encryption.decrypt

        if self.debug:
            print >>sys.stderr, "Session Key:", encryption.export_key()

        response = Node("response", xmlns="urn:ietf:params:xml:ns:xmpp-sasl",
                        data=encryption.get_response())
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
        elif node["type"] == "result" and iq.name == "query":
            self.messages.append(node)
        elif self.debug:
            print >>sys.stderr, "Unknown iq message"
            print >>sys.stderr, node.toxml(indent="  ") + "\n"

    def _incoming(self):
        nodes = self._read()

        for node in nodes:
            print ">>>", node.name

            if node.name == "challenge":
                self._challenge(node)
            elif node.name == "message":
                self.messages.append(node)
                self._received(node)
            elif node.name == "iq":
                self._iq(node)
            elif node.name == "stream:error":
                raise Exception(node.children[0].name)

            if node.name in self.callbacks:
                for callback in self.callbacks[node.name]:
                    if callback.test(node):
                        callback.apply(node)

            #elif node.name in ("start", "stream:features"):
            #    pass # Not interesting
            #elif self.debug:
            #    print >>sys.stderr, "Ignorning message"
            #    print >>sys.stderr, node.toxml(indent="  ") + "\n"

    def _msgid(self):
        return "msg-%d" % (time() * 1000)

    def register_callback(self, callback):
        if callback.name not in self.callbacks:
            self.callbacks[callback.name] = []

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
        self._incoming()

        # Send a ping once in a while if keep alive and still connected
        if self.keep_alive:
            if (time() - self.last_ping) > self.PING_INTERVAL:
                if self.socket != None:
                    self._ping()
                    self.last_ping = time()

    def login(self):
        assert self.socket is None

        self._connect()

        buf = self.writer.start_stream(self.SERVER, self.VERSION)
        self._write(buf)

        features = Node("stream:features")
        features.add(Node("receipt_acks"))
        features.add(Node("w:profile:picture", type="all"))
        features.add(Node("status"))

        # m1.java:48
        features.add(Node("notification", type="participant"))
        features.add(Node("groups"))

        self._write(features)

        auth = Node("auth", xmlns="urn:ietf:params:xml:ns:xmpp-sasl",
                    mechanism="WAUTH-1", user=self.number)
        self._write(auth)

        def on_success(node):
            if self.debug:
                print >>sys.stderr, "Logged In!"
            self.account_info = node.attributes

            presence = Node("presence")
            presence["name"] = self.nickname
            self._write(presence)

        # Create new callback
        callback = Callback("success", on_success)
        self.register_callback_and_wait(callback)

        # Done
        return self.account_info != None

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

        node = Node(state, xmlns = CHATSTATE_NS)
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
                raise Exception("Unknown audio attribute: %r" % name)

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
        Send a vCard to a contact. WhatsApp will display the PHOTO if it is
        embedded in the vCard data (as Base64 encoded JPEG).
        """

        vcard = Node("vcard", data=data)
        vcard["name"] = name
        media = Node("media", children=[vcard], xmlns="urn:xmpp:whatsapp:mms",
                     type="vcard", encoding="text")
        msgid, message = self._message(number, media)
        return msgid
