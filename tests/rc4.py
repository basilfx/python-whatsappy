from whatsappy.rc4 import RC4Engine

from hashlib import sha1

import unittest
import os

KEY = os.urandom(20)

class RC4Test(unittest.TestCase):

    def test_encryption(self):
        """
        Test encryption by encrypting some test vectors from Wikipedia
        (http://en.wikipedia.org/wiki/RC4#Test_vectors)
        """

        tests = [
            ("Key", "Plaintext", "BBF316E8D940AF0AD3"),
            ("Wiki", "pedia", "1021BF0420"),
            ("Secret", "Attack at dawn", "45A01F645FC35B383552544B9BF5")
        ]

        for key, plain, cipher in tests:
            rc4 = RC4Engine(key)
            self.assertEqual(rc4.process_bytes(plain), cipher.decode("hex"))

    def test_state(self):
        """
        Test if encrypting the same message twice results in the same
        ciphertext, and if encrypting a message can be reverted by an other
        instance.
        """
        a = RC4Engine(KEY)
        b = RC4Engine(KEY)

        message = os.urandom(128)
        self.assertEqual(a.process_bytes(message), b.process_bytes(message))
        self.assertEqual(a.box, b.box)

        message = os.urandom(128)
        self.assertEqual(a.process_bytes(b.process_bytes(message)), message,
            "encryption is reversible")
        self.assertEqual(a.box, b.box)

        message = os.urandom(128)
        self.assertEqual(a.process_bytes(b.process_bytes(message)), message,
            "encryption is reversible")
        self.assertEqual(a.box, b.box)
