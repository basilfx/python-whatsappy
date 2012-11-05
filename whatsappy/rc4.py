class RC4Engine:
    """
    Python port of the RC4 Engine in the Android version of WhatsApp, which
    seems to be an obfuscated version of the RC4Engine class found in the
    Bouncy Castle Crypto API (http://bouncycastle.org/java.html)
    """

    def __init__(self, key=None):
        """Initialize the engine. If a key is given, setKey is called"""

        if key is None:
            self.box = None
            self.workingKey = None
            self.x = 0
            self.y = 0
        else:
            self.setKey(key)

    def setKey(self, key):
        self.box = range(256)
        self.workingKey = key
        self.x = 0
        self.y = 0

        j = 0
        for i in range(256):
            j = (j + self.box[i] + ord(key[i % len(key)])) % 256
            self.box[i], self.box[j] = self.box[j], self.box[i]

    def processBytes(self, data):
        assert self.workingKey is not None

        out = []
        for char in data:
            self.x = (self.x + 1) % 256
            self.y = (self.y + self.box[self.x]) % 256
            self.box[self.x], self.box[self.y] = self.box[self.y], self.box[self.x]
            out.append(chr(ord(char) ^ self.box[(self.box[self.x] + self.box[self.y]) % 256]))
        return "".join(out)
