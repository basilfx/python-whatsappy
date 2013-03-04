class Callback(object):
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.called = 0
        self.result = None

    def apply(self, node):
        self.result = self.callback(node)
        self.called += 1

    def test(self, node):
        """
        Test whether a callback should be executed.
        """
        return True


class ChatMessageCallback(Callback):
    def __init__(self, callback, single=True, group=False, offline=False):
        super(ChatMessageCallback, self).__init__("message", callback)

        self.single = single
        self.group = group
        self.offline = offline

    def test(self, node):
        # Chat messages only
        if node.get("type") != "chat":
            return False

        # Messages with body only
        if not node.has_child("body"):
            return False

        # Include group messages or not
        if node.get("author"):
            if not self.group:
                return False
        else:
            if not self.single:
                return False

        # Include offline messages or not
        if node.has_child("offline"):
            if not self.offline:
                return False

        return True