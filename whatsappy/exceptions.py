class Error(Exception):
    """
    Base class for Whatsappy errors.
    """
    pass


class EncryptionError(Error):
    """
    Occurs when an exception happens during encryption/decryption of data.
    """
    pass


class ConnectionError(Error):
    """
    Error class for connection related errors.
    """
    pass


class StreamError(ConnectionError):
    """
    Special type of connection error that occurs when remote server sends a
    stream error
    """
    pass


class LoginError(Error):
    """
    Error class for login related errors.
    """
    pass