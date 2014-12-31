from whatsappy.rc4 import RC4Engine
from whatsappy.exceptions import EncryptionError

from pbkdf2 import PBKDF2
from hashlib import md5, sha1

import hmac
import struct

class Encryption(object):
    """
    This class handles:
     - creating the keys
     - decryption of messages (for Reader)
     - encryption of messages (for Writer)

    Encryption and decryption is both done using a RC4 engine. After
    initializing the RC4 engines, the first 768 bytes are dropped.
    """

    KEY_ITERATIONS = 2
    KEY_LENGTH = 20

    RC4_DROP = 768

    def __init__(self, secret, challenge):
        self.secret = secret
        self.challenge = challenge

        self.keys = []
        self.write_sequence = 0
        self.read_sequence = 0

        # Compute keys
        self.compute()

        # Construct RC4 engines, from which the first 768 bytes are dropped.
        self.rc4_in = RC4Engine(self.keys[2])
        self.rc4_in.process_bytes("\0" * self.RC4_DROP)

        self.rc4_out = RC4Engine(self.keys[0])
        self.rc4_out.process_bytes("\0" * self.RC4_DROP)

    def compute(self):
        """
        Compute the four session keys for the RC4 engines.

        The four session keys are derived using PBKDF2. The passphrase is the
        hashed secret, the salt is the challenge data sent by the WhatsApp
        server. The iteration count is 2, key length is 20 bytes.
        """

        # Generate keys
        for i in xrange(4):
            key = PBKDF2(self.secret, self.challenge + chr(i + 1),
                iterations=self.KEY_ITERATIONS).read(self.KEY_LENGTH)
            self.keys.append(key)

    def encrypt(self, data, append_mac=True):
        """
        Encrypt a given string of bytes. If 'append_mac' is False, the MAC is
        prepended to the output, otherwise appended.
        """

        sequence = struct.pack(">I", self.write_sequence)
        self.write_sequence += 1

        # Encrypt message and calculate MAC
        encrypted = self.rc4_out.process_bytes(data)
        mac = hmac.new(self.keys[1], encrypted + sequence,
            digestmod=sha1).digest()

        return encrypted + mac[:4] if append_mac else mac[:4] + encrypted

    def decrypt(self, data):
        """
        Decrypt a given string of bytes. Raises an EncryptionError if the MAC
        fails.
        """

        sequence = struct.pack(">I", self.read_sequence)
        self.read_sequence += 1

        # Calculate MAC
        mac = hmac.new(self.keys[3], data[:-4] + sequence,
            digestmod=sha1).digest()

        # Compare received MAC to calculated MAC
        if mac[:4] != data[-4:]:
            raise EncryptionError("MAC mismatch: expected %s, found %s" %
                (mac[:4].encode("hex"), data[-4:].encode("hex")))

        return self.rc4_in.process_bytes(data[:-4])

class AuthBlobEncryption(Encryption):

    KEY_ITERATIONS = 16

    def compute(self):
        data = PBKDF2(self.secret, self.challenge,
            iterations=self.KEY_ITERATIONS).read(self.KEY_LENGTH)

        for i in xrange(4):
            self.keys.append(data[i])