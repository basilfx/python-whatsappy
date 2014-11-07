class RC4Engine(object):
    """
    Python port of the RC4 Engine, which seems to be an obfuscated version of
    the RC4Engine class found in the Bouncy Castle Crypto API
    (http://bouncycastle.org/java.html)
    """

    def __init__(self, key):
        """
        Initialize the engine. If a key is given, set_key is called.
        """

        self.box = range(256)
        self.x = 0
        self.y = 0

        j = 0
        for i in xrange(256):
            j = (j + self.box[i] + ord(key[i % len(key)])) % 256
            self.box[i], self.box[j] = self.box[j], self.box[i]

    def process_bytes(self, data):
        out = []

        for d in data:
            self.x = (self.x + 1) % 256
            self.y = (self.y + self.box[self.x]) % 256

            self.box[self.x], self.box[self.y] = self.box[self.y], self.box[self.x]

            out.append(chr( ord(d) ^ self.box[(self.box[self.x] + self.box[self.y]) % 256] ))

        return "".join(out)
