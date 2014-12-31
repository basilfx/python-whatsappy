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
        if node.get("type") == "unavailable":
            if not self.offline:
                return False

        if node.has_child("type"):
            if not self.online:
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

        if child_name == "paused":
            if not self.paused:
                return False

        if child_name == "composing":
            if not self.composing:
                return False

        return super(ChatStateCallback, self).test(node)


class NotificationCallback(Callback):
    """
    General purpose callback for notifications. Notifications are fired in
    group contexts.
    """

    __slots__ = Callback.__slots__

    def __init__(self, callback):
        """
        Construct a new notification callback.
        """
        super(NotificationCallback, self).__init__("notification", callback)


class GroupJoinedCallback(NotificationCallback):
    """
    Callback for group joined notifications.
    """

    __slots__ = NotificationCallback.__slots__

    def test(self, node):
        if not node.has_child("add"):
            return False

        return Super(GroupJoinedCallback, self).test(node)


class GroupLeftCallback(NotificationCallback):
    """
    Callback for group left notifications.
    """

    __slots__ = NotificationCallback.__slots__

    def test(self, node):
        if not node.has_child("remove"):
            return False

        return Super(GroupChangedCallback, self).test(node)


class GroupChangedCallback(NotificationCallback):
    """
    Callback for group changed notifications.
    """

    __slots__ = NotificationCallback.__slots__ + ("picture", "title")

    def __init__(self, callback, picture=True, title=True, **kwargs):
        super(GroupChangedCallback, self).__init__(callback, **kwargs)

        self.picture = picture
        self.title = title

    def test(self, node):
        # Picture changes
        if node.get("type") == "subject":
            if not self.title:
                return False

        # Title changes
        if node.get("type") == "picture":
            if not self.picture:
                return False

        return super(GroupChangedCallback, self).test(node)


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
        # Include group messages or not
        if node.get("participant"):
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
        # Chat messages only
        if node.get("type") != "text":
            return False

        # Messages with body only
        if not node.has_child("body"):
            return False

        return super(TextMessageCallback, self).test(node)


class MediaMessageCallback(MessageCallback):
    """
    Message callback, specific for media-only messages. Optionally, the type of
    media messages can be filtered.

    types -- List of types to filter on. Valid types are 'image', 'video',
             'audio', 'vcard' or 'location'.
    """

    __slots__ = MessageCallback.__slots__ + ("types", )

    def __init__(self, callback, types=None, **kwargs):
        super(MediaMessageCallback, self).__init__(callback, **kwargs)

        self.types = types

    def test(self, node):
        # Media messages only
        if node.get("type") != "media":
            return False

        # Media messages of certain type only
        if self.types:
            if node.child("media")["type"] not in self.types:
                return False

        return super(MediaMessageCallback, self).test(node)


class SyncResultCallback(Callback):
    """
    Callback for contact sync result.
    """

    __slots__ = Callback.__slots__

    def __init__(self, callback):
        """
        Construct a new callback.
        """
        super(SyncResultCallback, self).__init__("iq", callback)

    def test(self, node):
        if not node.has_child("sync"):
            return False

        return super(SyncResultCallback, self).test(node)