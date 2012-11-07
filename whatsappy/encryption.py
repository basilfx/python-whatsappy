import sys

from time import time
from pbkdf2 import PBKDF2
from hashlib import md5, sha1
import hmac

from .rc4 import RC4Engine

class Encryption:
    """
    This class handles:
     - creating the session key
     - construction the authentication challenge response
     - decryption of messages (for Reader)
     - encryption of messages (for Writer)

    The session key is derived using PBKDF2. The passprase is the hashed secret,
    the salt is the challenge data sent by the WhatsApp server.
    Iteration count is 16, key length is 20 bytes.

    Encryption and decryption is both done using a RC4 engine. After
    initializing the RC4 engines, a buffer of 256 nullbytes is encrypted.
    """

    KEY_ITERATIONS = 16
    KEY_LENGTH = 20

    def __init__(self, number, secret = None, challenge = None):
        self.number = number
        self.challenge = challenge

        if secret is not None:
            passphrase = self.hash_secret(secret)
            pbkdf2 = PBKDF2(passphrase, challenge, iterations=self.KEY_ITERATIONS)
            key = pbkdf2.read(self.KEY_LENGTH)
            self.set_key(key)

    def hash_secret(self, secret):
        if ":" in secret: # MAC Address
            data = secret.upper() + secret.upper()
        else: # IMEI Number
            data = secret[::-1]
        return md5(data).hexdigest()

    def get_response(self):
        data = "%s%s%d" % (self.number, self.challenge, time())
        encrypted = self.rc4out.processBytes(data)
        return self.mac(encrypted) + encrypted

    def export_key(self):
        return self.key.encode("hex")

    def set_key(self, key):
        if len(key) == self.KEY_LENGTH * 2:
            key = key.decode("hex")
        self.key = key

        self.rc4in = RC4Engine()
        self.rc4in.setKey(self.key)
        self.rc4in.processBytes("\0" * 256)

        self.rc4out = RC4Engine()
        self.rc4out.setKey(self.key)
        self.rc4out.processBytes("\0" * 256)

    def encrypt(self, data):
        encrypted = self.rc4out.processBytes(data)
        return encrypted + self.mac(encrypted)

    def decrypt(self, data, macAtStart=True):
        if macAtStart:
            encrypted = data[4:]
            mac = data[:4]
        else:
            encrypted = data[:-4]
            mac = data[-4:]

        decrypted = self.rc4in.processBytes(encrypted)

        calculatedMac = self.mac(encrypted)
        if mac != calculatedMac:
            print >>sys.stderr, "MAC mismatch (Expected %s; Found %s)" % (
                calculatedMac.encode("hex"), mac.encode("hex"))

        return decrypted

    def mac(self, data):
        return hmac.new(self.key, data, digestmod=sha1).digest()[:4]
