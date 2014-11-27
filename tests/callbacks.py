from whatsappy import callbacks

import unittest

class CallbackTest(unittest.TestCase):
    def test_callback(self):
        """
        Test basic callback
        """

        callback = callbacks.Callback("test", lambda x: x * 1337)

        self.assertEqual(callback.name, "test")
        self.assertEqual(callback.called, 0)

        self.assertTrue(callback.test(None))

        callback(1)

        self.assertEqual(callback.called, 1)
        self.assertEqual(callback.result, 1 * 1337)

        callback(2)

        self.assertEqual(callback.called, 2)
        self.assertEqual(callback.result, 2 * 1337)