import sys

import socket
from select import select
from time import time
from hashlib import md5

from twisted.words.protocols.jabber.sasl_mechanisms import DigestMD5

from stream import Reader, Writer, MessageIncomplete, EndOfStream
from node import Node

def hash_secret(secret):
    if ":" in secret:
        # MAC Address
        data = secret.upper() + secret.upper()
    else:
        # IMEI Number
        data = secret[::-1]

    return md5(data).hexdigest()

class Callback:
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.called = 0
        self.result = None

    def apply(self, node):
        self.result = self.callback(node)
        self.called += 1

class Client:
    HOST = "bin-short.whatsapp.net"
    PORT = 5222
    TIMEOUT = 0.1 # s

    SERVER = "s.whatsapp.net"
    REALM = "s.whatsapp.net"
    GROUPHOST = "g.us"
    DIGEST_URI = "xmpp/s.whatsapp.net"

    DEVICE = "iPhone"
    VERSION = "2.8.2"

    def __init__(self, number, secret, nickname = None):
        self.number = number
        self.secret = secret
        self.password = hash_secret(secret)
        self.nickname = nickname

        self.host = self.HOST
        self.port = self.PORT

        self.debug = False
        self.socket = None
        self.reader = Reader()
        self.writer = Writer()

        self.messages = []

        self.callbacks = {}

    def _connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def _write(self, buf):
        if isinstance(buf, Node):
            if self.debug:
                sys.stderr.write(buf.toxml(indent="xml > ") + "\n")
            buf = self.writer.node(buf)

        if self.debug: self.dump("    >", buf)
        self.socket.sendall(buf)

    def _read(self, nbytes = 4096):
        # See if there's data available to read
        r, w, x, = select([self.socket], [], [], self.TIMEOUT)
        if self.socket in r:
            # receive any available data, update Reader's buffer
            buf = self.socket.recv(nbytes)
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
                    bytestr += bytes[i + j] if b >= 0x20 and b < 0x7F else "."
                else:
                    hexstr  += "   "

                if (j % 4) == 3:
                    hexstr += " "

            print >>sys.stderr, prefix + " " + hexstr + bytestr

    def _challenge(self, node):
        # Use SASL DIGEST-MD5 Mechanism from Twisted Words
        mechanism = DigestMD5("xmpp", self.SERVER, None, self.number, self.password)

        # Decode the challende, and encode the resulting data
        challenge = node.data.decode("base64")
        data = mechanism.getResponse(challenge)
        b64data = data.encode("base64").replace("\n", "")

        # Create a response node
        response = Node("response", data=b64data)
        response["xmlns"] = node["xmlns"]

        self._write(response)
        self._incoming()

    def _received(self, node):
        request = node.child("request")
        if request is None or request["xmlns"] != "urn:xmpp:receipts":
            return

        message = Node("message", to=node["from"], id=node["id"], type="chat")
        message.add(Node("received", xmlns="urn:xmpp:receipts"))

        self._write(message)

    def _iq(self, node):
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
                for record in self.callbacks[node.name]:
                    record.apply(node)

            #elif node.name in ("start", "stream:features"):
            #    pass # Not interesting
            #elif self.debug:
            #    print >>sys.stderr, "Ignorning message"
            #    print >>sys.stderr, node.toxml(indent="  ") + "\n"

    def _msgid(self):
        return "msg-%d" % (time() * 1000)

    def register_callback(self, name, callback):
        record = Callback(name, callback)

        if name not in self.callbacks:
            self.callbacks[name] = []

        self.callbacks[name].append(record)
        return record

    def unregister_callback(self, record):
        self.callbacks[record.name].remove(record)

    def wait_for_callback(self, record):
        while not record.called:
            self._incoming()

        self.unregister_callback(record)

        if isinstance(record.result, Exception):
            raise record.result

        return record.result

    def wait_for_any_callback(self, records):
        called = None
        while called is None:
            for record in records:
                if record.called:
                    called = record
                    break
            else:
                self._incoming()

        for record in records:
            self.unregister_callback(record)

        if isinstance(called.result, Exception):
            raise called.result

        return called.result

    def login(self):
        assert self.socket is None

        self._connect()

        resource = "%s-%s-%d" % (self.DEVICE, self.VERSION, self.PORT)
        buf = self.writer.start_stream(self.SERVER, resource)
        self._write(buf)

        features = Node("stream:features")
        features.add(Node("receipt_acks"))
        features.add(Node("groups"))
        self._write(features)

        auth = Node("auth", xmlns="urn:ietf:params:xml:ns:xmpp-sasl", mechanism="DIGEST-MD5-1")
        self._write(auth)

        def on_success(node):
            if self.debug:
                print >>sys.stderr, "Logged In!"
            self.account_info = node.attributes

            presence = Node("presence")
            presence["name"] = self.nickname
            self._write(presence)

        callback = self.register_callback("success", on_success)
        self.wait_for_callback(callback)

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

        callback = self.register_callback("iq", on_iq)
        return self.wait_for_callback(callback)

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

    def image(self, number, url, basename, size, thumbnail = None):
        """
        Send an image to a contact.
        Url should be publicly accessible
        Basename does not have to match Url
        Size is the size of the image, in bytes
        Thumbnail should be a base64 encoded JPEG image, if proviced.
        """
        # TODO: Where does WhatsApp upload images?
        # TODO: Are PNG thumbnails supported?

        media = Node("media", xmlns="urn:xmpp:whatsapp:mms", type="image",
                     url=url, file=basename, size=size, data=thumbnail)
        msgid, message = self._message(number, media)
        self._write(message)

    def location(self, number, latitude, longitude):
        "Send a location update to a contact"
        # XXX: PHP WhatsApi does not include the jabber:x:event

        media = Node("media", xmlns="urn:xmpp:whatsapp:mms", type="location",
                     latitude=latitude, longitude=longitude)
        msgid, message = self._message(number, media)
        self._write(message)
