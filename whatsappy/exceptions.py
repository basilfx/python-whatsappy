class Error(Exception):
    """
    Base class for Whatsappy errors.
    """
    pass


class ConnectionError(Error):
    """
    Error class for connection related errors.
    """
    pass


class LoginError(Error):
    """
    Error class for login related errors.
    """
    pass