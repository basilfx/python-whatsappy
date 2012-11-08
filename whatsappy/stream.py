import sys

from .tokens import str2tok, tok2str
from .node import Node

class MessageIncomplete(Exception):
    pass

class EndOfStream(Exception):
    pass

ENCRYPTED_IN  = 0x8
ENCRYPTED_OUT = 0x1

class Reader:
    def __init__(self, buf = ""):
        self.buf = buf
        self.offset = 0
        self.decrypt = None

    def data(self, buf):
        self.buf += buf

    def _consume(self, bytes):
        if bytes > len(self.buf):
            raise Exception("Not enough bytes available")

        self.offset += bytes

        data = self.buf[:bytes]
        self.buf = self.buf[bytes:]
        return data

    def _peek(self, bytes):
        return self.buf[:bytes]

    def read(self):
        if len(self.buf) <= 2:
            raise MessageIncomplete()

        length = self.peek_int24()
        flags  = (length & 0x00F00000) >> 20
        length = (length & 0x000FFFFF)

        if length + 3 > len(self.buf):
            raise MessageIncomplete()

        self.int24()

        if flags & ENCRYPTED_IN:
            return self._read_encrypted(length)
        else:
            return self._read()

    def _read_encrypted(self, length):
        assert self.decrypt is not None

        message_buf = self._consume(length)
        message_buf = self.decrypt(message_buf)

        buf = self.buf
        offset = self.offset

        try:
            self.buf = message_buf
            self.offset = 0
            return self._read()
        finally:
            self.buf = buf
            self.offset = offset

    def _read(self):
        length = self.list_start()

        token = self._peek(1)
        if token == "\x01":
            self._consume(1)
            attributes = self.attributes(length)
            return Node("start", **attributes)

        if token == "\x02":
            self._consume(1)
            raise EndOfStream()

        node = Node(self.string())
        node.attributes = self.attributes(length)

        if (length % 2) == 0:
            token = self._peek(1)
            if token == "\xF8" or token == "\xF9":
                node.children = self.list()
            else:
                node.data = self.string()

        return node

    def peek_int8(self):
        return ord(self._peek(1))

    def peek_int16(self):
        s = self._peek(2)
        return ord(s[0]) << 8 | ord(s[1])

    def peek_int24(self):
        s = self._peek(3)
        return ord(s[0]) << 16 | ord(s[1]) << 8 | ord(s[2])

    def int8(self):
        return ord(self._consume(1))

    def int16(self):
        s = self._consume(2)
        return ord(s[0]) << 8 | ord(s[1])

    def int24(self):
        s = self._consume(3)
        return ord(s[0]) << 16 | ord(s[1]) << 8 | ord(s[2])

    def list(self):
        children = []
        for i in range(self.list_start()):
            children.append(self._read())
        return children

    def list_start(self):
        token = self._consume(1)
        if token == "\x00":
            return 0
        elif token == "\xF8":
            return self.int8()
        elif token == "\xF9":
            return self.int16()
        else:
            raise Exception("Unknown list_start token '%02x'" % ord(token))

    def attributes(self, length):
        attributes = {}
        for _ in range((length - 1) / 2):
            name = self.string()
            value = self.string()
            attributes[name] = value
        return attributes

    def string(self):
        token = self._consume(1)
        if token < "\x05":
            return ""
        elif "\x05" <= token <= "\xF5":
            return tok2str(ord(token))
        elif token == "\xFA":
            user = self.string()
            server = self.string()
            return user + "@" + server
        elif token == "\xFC":
            return self._consume(self.int8())
        elif token == "\xFD":
            return self._consume(self.int24())
        elif token == "\xFE":
            return tok2str(0xF5 + self.int8())
        else:
            raise Exception("Unknown string token '%02x'" % ord(token))

class Writer:
    VERSION = 1, 2

    def __init__(self):
        self.encrypt = None

    def start_stream(self, domain, resource):
        attributes = { "to": domain, "resource": resource }

        buf = "WA%c%c" % self.VERSION

        buf += "\x00\x00\x18"

        buf += self.list_start(len(attributes) * 2 + 1)
        buf += "\x01"
        buf += self.attributes(attributes)

        return buf

    def node(self, node, encrypt=None):
        if node is None:
            buf = "\x00"
        else:
            buf = self._node(node)

        if encrypt is None:
            encrypt = self.encrypt is not None

        if encrypt:
            buf = self.encrypt(buf)
            header = self.int24(ENCRYPTED_OUT << 20 | len(buf))
        else:
            header = self.int24(len(buf))

        return header + buf

    def _node(self, node):
        length = 1
        if node.attributes:
            length += len(node.attributes) * 2
        if node.children:
            length += 1
        if node.data:
            length += 1

        buf = self.list_start(length)
        buf += self.string(node.name)
        buf += self.attributes(node.attributes)

        if node.data:
            buf += self.bytes(node.data)

        if node.children:
            buf += self.list_start(len(node.children))
            for child in node.children:
                buf += self._node(child)

        return buf

    def token(self, token):
        if token < 0xF5:
            return chr(token)
        elif token <= 0x1F4:
            return "\xFE" + chr(token - 0xF5)

    def int8(self, value):
        return chr(value & 0xFF)

    def int16(self, value):
        return chr((value & 0xFF00) >> 8) + \
               chr((value & 0x00FF) >> 0)

    def int24(self, value):
        return chr((value & 0xFF0000) >> 16) + \
               chr((value & 0x00FF00) >>  8) + \
               chr((value & 0x0000FF) >>  0)

    def jid(self, user, server):
        buf = "\xFA"
        buf += self.string(user) if user else "\x00"
        buf += self.string(server)
        return buf

    def bytes(self, string):
        if isinstance(string, unicode):
            string = string.encode("utf-8")
        if len(string) > 0xFF:
            leader = "\xFD" + self.int24(len(string))
        else:
            leader = "\xFC" + self.int8(len(string))
        return leader + string

    def string(self, string):
        if not isinstance(string, basestring):
            string = str(string)
        token = str2tok(string)
        if token is not None:
            return self.token(token)
        elif "@" in string:
            user, at, server = string.partition("@")
            return self.jid(user, server)
        else:
            return self.bytes(string)

    def attributes(self, attributes):
        buf = ""
        for key, value in attributes.iteritems():
            buf += self.string(key)
            buf += self.string(value)
        return buf

    def list_start(self, length):
        if length == 0:
            return "\x00"
        elif length <= 0xFF:
            return "\xF8" + chr(length)
        else:
            # XXX: PHP Code says "\xf9" . chr($len), chr seems to wrap
            # TODO: Find out if this is correct / intentional
            return "\xF9" + chr(length & 0xFF)
