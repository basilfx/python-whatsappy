from whatsappy.rc4 import RC4Engine

from time import time
from pbkdf2 import PBKDF2
from hashlib import md5, sha1

import hmac
import struct

class Encryption(object):
    """
    This class handles:
     - creating the session key
     - construction the authentication challenge response
     - decryption of messages (for Reader)
     - encryption of messages (for Writer)

    The session keys are derived using PBKDF2. The passphrase is the hashed
    secret, the salt is the challenge data sent by the WhatsApp server. The
    iteration count is 16, key length is 20 bytes.

    Encryption and decryption is both done using a RC4 engine. After
    initializing the RC4 engines, the first 768 bytes are dropped.
    """

    KEY_ITERATIONS = 2
    KEY_LENGTH = 20
    KEY_DROP = 768

    def __init__(self, secret, challenge):
        self.secret = secret
        self.challenge = challenge

        self.keys = []
        self.write_sequence = 0
        self.read_sequence = 0

        # Generate session keys
        for i in xrange(4):
            key = PBKDF2(secret, challenge + chr(i + 1),
                iterations=self.KEY_ITERATIONS).read(self.KEY_LENGTH)
            self.keys.append(key)

        # Construct RC4 engines, from which the first 768 bytes are dropped.
        self.rc4_in = RC4Engine(self.keys[2])
        self.rc4_in.process_bytes("\0" * self.KEY_DROP)

        self.rc4_out = RC4Engine(self.keys[0])
        self.rc4_out.process_bytes("\0" * self.KEY_DROP)

    def encrypt(self, data, append_mac=True):# mac_offset=0):
        encrypted = self.rc4_out.process_bytes(data)
        mac = self.mac(encrypted, self.keys[1], True)

        if append_mac:
            return encrypted + mac[:4]
        else:
            return mac[:4] + encrypted

    def decrypt(self, data):
        mac = self.mac(data[:-4], self.keys[3], False)[:4]

        # Compare received MAC to calculated MAC
        if mac != data[-4:]:
            raise ValueError("MAC mismatch: expected %s, found %s" %
                (mac.encode("hex"), data[-4:].encode("hex")))

        return self.rc4_in.process_bytes(data[:-4])

    def mac(self, data, key, writing):
        data += struct.pack(">I", self.write_sequence if writing else self.read_sequence)

        if writing:
            self.write_sequence += 1
        else:
            self.read_sequence += 1

        return hmac.new(key, data, digestmod=sha1).digest()
