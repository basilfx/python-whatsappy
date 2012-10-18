import sys

import socket
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

class Client:
    HOST = "bin-short.whatsapp.net"
    PORT = 5222

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
        buf = self.socket.recv(nbytes)
        if self.debug: self.dump("    <", buf)

        if buf:
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
        pass

    def _iq(self, node):
        iq = node.children[0]
        if node["type"] == "get" and iq.name == "ping":
            self._pong(node["id"])
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
            elif node.name == "success":
                if self.debug:
                    print >>sys.stderr, "Logged In!"
                self.account_info = node.attributes
            elif node.name == "message":
                self.messages.append(node)
                self._received(node)
            elif node.name == "iq":
                self._iq(node)
            elif node.name == "stream:error":
                raise Exception(node.children[0].name)
            elif node.name in ("start", "stream:features"):
                pass # Not interesting
            elif self.debug:
                print >>sys.stderr, "Ignorning message"
                print >>sys.stderr, node.toxml(indent="  ") + "\n"

    def login(self):
        assert self.socket is None

        self._connect()

        resource = "%s-%s-%d" % (self.DEVICE, self.VERSION, self.PORT)
        buf = self.writer.start_stream(self.SERVER, resource)
        self._write(buf)

        features = Node("stream:features")
        features.add(Node("receipt_acks"))
        self._write(features)

        auth = Node("auth", xmlns="urn:ietf:params:xml:ns:xmpp-sasl", mechanism="DIGEST-MD5-1")
        self._write(auth)

        self._incoming()
