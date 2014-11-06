class Callback(object):
    """
    General callback for received nodes.
    """

    __slots__ = ("name", "callback", "called", "result")

    def __init__(self, name, callback):
        """
        Construct a new callback.

        name -- Name of the callback.
        callback -- Function to execute
        """

        self.name = name
        self.callback = callback
        self.called = 0

    def __call__(self, node):
        """
        Run the callback with a given node.

        node -- The node to pass on
        """

        self.result = self.callback(node)
        self.called += 1

    def test(self, node):
        """
        Test whether a callback should be executed.

        node -- The node to check
        """

        return True

class PresenceCallback(Callback):
    """
    Callback for presence notifications.
    """

    __slots__ = Callback.__slots__ + ("online", "offline")

    def __init__(self, callback, online=True, offline=False):
        """
        Constructy a new presence callback

        online -- When user comes online
        offline -- When user goes offline
        """
        super(PresenceCallback, self).__init__("message", callback)

        self.online = online
        self.offline = offline

    def test(self, node):
        pass

class MessageCallback(Callback):
    """
    Callback for message notifications, either single conversation messages or
    group conversation messages.
    """

    __slots__ = Callback.__slots__ + ("single", "group", "offline")

    def __init__(self, callback, single=True, group=False, offline=False):
        """
        Construct new message callback

        single -- Include messages from normal conversations
        group -- Include messages from group conversations
        offline -- Include offline messages
        """
        super(MessageCallback, self).__init__("message", callback)

        self.single = single
        self.group = group
        self.offline = offline

    def test(self, node):
        # Chat messages only
        if node.get("type") != "chat":
            return False

        # Include group messages or not
        if node.get("author"):
            if not self.group:
                return False
        else:
            if not self.single:
                return False

        # Include offline messages or not
        if not self.offline and node.has_child("offline"):
            return False

        return super(MessageCallback, self).test(node)

class TextMessageCallback(MessageCallback):
    """
    Message callback, specific for text-only messages.
    """

    __slots__ = MessageCallback.__slots__

    def test(self, node):
        # Messages with body only
        if not node.has_child("body"):
            return False

        return super(TextMessageCallback, self).test(node)

class MediaMessageCallback(MessageCallback):
    """
    Message callback, specific for media-only messages.
    """

    __slots__ = MessageCallback.__slots__

    def test(self, node):
        # Messages with media only
        if not node.has_child("media"):
            return False

        return super(MediaMessageCallback, self).test(node)