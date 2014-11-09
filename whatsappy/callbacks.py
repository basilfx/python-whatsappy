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

class LoginSuccessCallback(Callback):
    """
    Callback for succesful login.
    """

    __slots__ = Callback.__slots__

    def __init__(self, callback):
        """
        Construct a new callback.
        """
        super(LoginSuccessCallback, self).__init__("success", callback)

class LoginFailedCallback(Callback):
    """
    Callback for failed login.
    """

    __slots__ = Callback.__slots__

    def __init__(self, callback):
        """
        Construct a new callback.
        """
        super(LoginFailedCallback, self).__init__("failure", callback)

class PresenceCallback(Callback):
    """
    Callback for presence notifications.
    """

    __slots__ = Callback.__slots__ + ("online", "offline")

    def __init__(self, callback, online=True, offline=False):
        """
        Construct a new presence callback.

        online -- When user comes online.
        offline -- When user goes offline.
        """
        super(PresenceCallback, self).__init__("presence", callback)

        self.online = online
        self.offline = offline

    def test(self, node):
        if self.online:
            if not self.offline and node.get("type") == "unavailable":
                return False

        if self.offline:
            if not self.online and node.has_child("type"):
                return False

        return super(PresenceCallback, self).test(node)

class ChatStateCallback(Callback):
    """
    Callback for chat state changes.
    """

    __slots__ = Callback.__slots__ + ("composing", "paused")

    def __init__(self, callback, composing=True, paused=False):
        """
        Construct a new chat state callback.

        composing -- Respond to composing states.
        paused -- Respond to paused states.
        """

        super(ChatStateCallback, self).__init__("chatstate", callback)

        self.composing = composing
        self.paused = paused

    def test(self, node):
        child_name = node.children[0].name

        if self.composing:
            if not self.paused and child_name == "paused":
                return False

        if self.paused:
            if not self.composing and child_name == "composing":
                return False

        return super(ChatStateCallback, self).test(node)

class NotificationCallback(Callback):
    """
    General purpose callback for notifications. Notifications are fired in
    group contexts.
    """

    def __init__(self, callback):
        """
        Construct a new notification callback.
        """
        super(NotificationCallback, self).__init__("notification", callback)

class GroupJoinedCallback(Callback):
    pass

class GroupLeftCallback(Callback):
    pass

class GroupChangedCallback(Notification):
    pass

class MessageCallback(Callback):
    """
    Callback for message notifications, either single conversation messages or
    group conversation messages.
    """

    __slots__ = Callback.__slots__ + ("single", "group", "offline")

    def __init__(self, callback, single=True, group=False, offline=False):
        """
        Construct new message callback.

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
        if node.get("type") != "text":
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