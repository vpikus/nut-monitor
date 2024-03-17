import socket
import logging

class NutSock:
    """NUT (Network UPS Tools) socket helpper."""

    def __init__(self, host="127.0.0.1", port=3493, timeout=5):
        """
        Class initialization method.

        Parameters:
        - host (str): The hostname or IP address of the NUT server.
        - port (int): The port number of the NUT server.
        - timeout (int): The timeout in seconds for the socket connection.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("NutSock initialization")
        self.logger.debug(f"\tHost: {host}, Port: {port}")
        
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.raw_queue = None
    
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.logger.debug("Closing NUT connection")
        if self.sock:
            self.sock.close()
        self.sock = None
        self.raw_queue = None

    def connect(self):
        """
        Connect to the NUT server and return the socket object.

        Returns:
        - self: The NutSock object.
        """
        self.logger.debug("Connecting to NUT server")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

    def cmd(self, command):
        """
        Send a command to the NUT server and return the response.

        Parameters:
        - command (str): The command to send to the NUT server.

        Returns:
        - str: The response from the NUT server.
        """
        self.logger.debug(f"Sending command:\n{command}")
        self.sock.sendall(f"{command}\n".encode("utf-8"))
        
    def read_until(self, untilText):
        """
        Read from the socket until the specified text is found. The method accumulates 
        data read from the socket in a 'raw_queue'. Once the 'untilText' is encountered, 
        the method returns the accumulated data up to and including 'untilText'. 
        The data beyond 'untilText' is saved in the 'raw_queue' for future reads.

        Parameters:
        - untilText (str): The text to read until.

        Returns:
        - str: The response from the NUT server.
        """
        buf = self.raw_queue or ""
        while not untilText in buf:
            buf += self.sock.recv(50).decode("utf-8")
        pos = buf.find(untilText) + len(untilText)
        self.raw_queue = buf[pos:]
        response = buf[:pos]
        self.logger.debug(f"Received response:\n{response}")
        return response
