class NutClientError(Exception):
    """NUT (Network UPS Tools) client base exception."""


class NutClientCmdError(NutClientError):
    """NUT (Network UPS Tools) client CMD exception."""


class NutClientConnectError(NutClientError):
    """NUT (Network UPS Tools) client connection error."""
