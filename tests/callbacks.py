from whatsappy import callbacks

import unittest

class CallbackTest(unittest.TestCase):
    def test_callback(self):
        value = False

        callback = callbacks.Callback("test", lambda x: 1337)

        self.assertEqual(callback.name, "test")
        self.assertEqual(callback.called, 0)

        self.assertTrue(callback.test(None))

        callback.apply(None)

        self.assertEqual(callback.called, 1)
        self.assertEqual(callback.result, 1337)

        callback.apply(None)

        self.assertEqual(callback.called, 2)
        self.assertEqual(callback.result, 1337)