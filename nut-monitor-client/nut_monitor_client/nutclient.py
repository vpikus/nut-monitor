import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List

from . import nutsock, nutvartypes
from .exceptions import NutClientCmdError


@dataclass(frozen=True)
class NutAuthentication:
    username: str
    password: str


class NutClient:
    """NUT (Network UPS Tools) client."""

    LOG = logging.getLogger(__name__)

    def __init__(
        self,
        host="127.0.0.1",
        port=nutsock.DEF_PORT,
        timeout=nutsock.DEF_TIMEOUT,
    ):
        """
        Class initialization method.

        Parameters:
        - host (str): The hostname or IP address of the NUT server.
        - port (int): The port number of the NUT server.
        - timeout (int): The timeout in seconds for the socket connection.
        """
        self.LOG.debug("NutClient initialization")
        self.LOG.debug(f"\tHost: {host}, Port: {port}")
        self.host = host
        self.port = port
        self.timeout = timeout

    def session(self, authentication: NutAuthentication = None):
        """
        Create a new NUT session.

        Parameters:
        - authentication (NutAuthentication): The authentication credentials for the NUT server.

        Returns:
        - NutSession: A new NUT session.
        """

        return NutSession(
            host=self.host,
            port=self.port,
            authentication=authentication,
            timeout=self.timeout,
        )


class GET(Enum):
    """NUT (Network UPS Tools) GET sub-commands."""

    VAR = "VAR"
    TYPE = "TYPE"
    DESC = "DESC"
    NUMLOGINS = "NUMLOGINS"
    UPSDESC = "UPSDESC"
    CMDDESC = "CMDDESC"


class LIST(Enum):
    """NUT (Network UPS Tools) LIST sub-commands."""

    UPS = "UPS"
    VAR = "VAR"
    RW = "RW"
    ENUM = "ENUM"
    RANGE = "RANGE"
    CMD = "CMD"
    CLIENT = "CLIENT"


class SET(Enum):
    """NUT (Network UPS Tools) SET sub-commands."""

    VAR = "VAR"
    TRACKING = "TRACKING"


class NutSession:
    """NUT (Network UPS Tools) session."""

    LOG = logging.getLogger(__name__)

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = nutsock.DEF_PORT,
        authentication: NutAuthentication = None,
        timeout: float = nutsock.DEF_TIMEOUT,
    ):
        """
        Class initialization method.

        Parameters:
        - host (str): The hostname or IP address of the NUT server.
        - port (int): The port number of the NUT server.
        - authentication (NutAuthentication): The authentication credentials for the NUT server.
        - timeout (int): The timeout in seconds for the socket connection.
        """
        self.sock = nutsock.NutSock(host, port, timeout)
        self.authentication = authentication

    def __enter__(self):
        self.LOG.debug("Opening NUT connection")
        self.sock.connect()
        if self.authentication:
            if self.authentication.username:
                self.username(self.authentication.username)
            if self.authentication.password:
                self.password(self.authentication.password)
        return self

    def __exit__(self, *args):
        self.LOG.debug("Closing NUT connection")
        if self.sock:
            self.logout()
            self.sock.close()
        self.sock = None

    def auth(self, username: str, password: str):
        """
        Write the username and password to the NUT.

        Parameters:
        - username (str): The username to use for the login.
        - password (str): The password to use for the login.
        """
        self.username(username)
        self.password(password)

    def login(self, upsname: str):
        self.sock.cmd(f"LOGIN {upsname}")
        raw_result = self.sock.read_line()
        if raw_result.startswith("ERR ") or raw_result != "OK\n":
            raise NutClientCmdError(f"Invalid response from 'LOGIN' command: {raw_result}")

    def logout(self):
        self.sock.cmd("LOGOUT")
        raw_result = self.sock.read_line()
        if not raw_result in ["Goodbye...\n", "OK Goodbye\n"]:
            raise NutClientCmdError(f"Invalid response from 'LOGOUT' command: {raw_result}")

    def username(self, username: str):
        """
        Set the username for the NUT session.

        Parameters:
        - username (str): The username to set.
        """
        self.sock.cmd(f"USERNAME {username}")
        raw_result = self.sock.read_line()
        if raw_result.startswith("ERR ") or raw_result != "OK\n":
            raise NutClientCmdError(f"Invalid response from 'USERNAME' command: {raw_result}")

    def password(self, password: str):
        """
        Set the password for the NUT session.

        Parameters:
        - password (str): The password to set.
        """
        self.sock.cmd(f"PASSWORD {password}")
        raw_result = self.sock.read_line()
        if raw_result.startswith("ERR ") or raw_result != "OK\n":
            raise NutClientCmdError(f"Invalid response from 'PASSWORD' command: {raw_result}")

    def __exec_get(self, command: GET, *args: str) -> str:
        """
        Retrieve a single response from the NUT server.

        Parameters:
        - command (GET): The GET sub-command.
        - args (str): The arguments for the GET sub-command.

        Returns:
        - str: The value of the variable.
        """

        sub_cmd = f"{command.value} {' '.join(args)}"
        full_cmd = f"GET {sub_cmd}"
        self.sock.cmd(full_cmd)
        raw_response = self.sock.read_line()
        expected_start = f"{sub_cmd} "
        if not raw_response.startswith(expected_start):
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {raw_response}")
        return raw_response[len(expected_start) : -1]

    def num_logins(self, upsname: str) -> int:
        """
        Get the number of clients which have done LOGIN for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - int: The number of clients which have done LOGIN for this UPS. This is used by the upsmon in primary mode to determine how many clients are still connected when starting the shutdown process.
        """
        try:
            value = int(self.__exec_get(GET.NUMLOGINS, upsname))
            return value
        except (IndexError, ValueError):
            raise NutClientCmdError("Invalid response from 'GET NUMLOGINS' command")

    def ups_desc(self, upsname: str) -> str:
        """
        Get the description of a UPS.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The value of "desc=" from ups.conf for this UPS. If it is not set, upsd will return "Unavailable".
        """
        try:
            return self.__exec_get(GET.UPSDESC, upsname).strip('"')
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET UPSDESC' command")

    def var_value(self, upsname: str, var: str) -> str:
        """
        Get the value of a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The value of the variable.
        """
        try:
            return self.__exec_get(GET.VAR, upsname, var).strip('"')
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET VAR' command")

    def var_type(self, upsname: str, var: str) -> List[nutvartypes.VarTypeEnum]:
        """
        Get the type of a variable for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The type of the variable.
        """
        try:
            types: List[nutvartypes.VarTypeEnum] = []
            for type in self.__exec_get(GET.TYPE, upsname, var).split(" "):
                pos = type.find(":")
                if pos != -1:
                    types.append(nutvartypes.StringType(max_length=int(type[pos + 1 :])))
                else:
                    types.append(nutvartypes.BaseType(type=nutvartypes.VarTypeEnum(type)))
            return types
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET TYPE' command")

    def var_desc(self, upsname: str, var: str) -> str:
        """
        Get the description of a variable for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The description that gives a brief explanation of the named variable. upsd may return "Unavailable" if the file which provides this description is not installed.
        """
        try:
            return self.__exec_get(GET.DESC, upsname, var).strip('"')
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET VAR' command")

    def cmd_desc(self, upsname: str, cmd: str) -> str:
        """
        Get the description of a command for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.
        - cmd (str): The name of the command.

        Returns:
        - str: The description that gives a brief explanation of the named command. upsd may return "Unavailable" if the file which provides this description is not installed.
        """
        try:
            return self.__exec_get(GET.CMDDESC, upsname, cmd).strip('"')
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET CMDDESC' command")

    def tracking(self, id: str = None) -> str:
        """
        Get the tracking status of a variable for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.
        - id (str): The tracking ID.

        Returns:
        - str: The tracking status of the variable.
        """
        self.sock.cmd(f"GET TRACKING {id}")
        raw_response = self.sock.read_line()
        if raw_response.startswith("ERR "):
            raise NutClientCmdError(f"Invalid response from 'GET TRACKING' comand: {raw_response}")
        return raw_response

    def ___exec_list(self, command: LIST, consumer: Callable[[str], None], *args: str) -> None:
        """
        Retrieve a list response from the NUT server.

        Parameters:
        - command (LIST): The LIST sub-command.
        - consumer (Callable[[str], None]): The consumer function to process each line of the response.
        - args (str): The arguments for the LIST sub-command.
        """
        sub_cmd = f"{command.value} {' '.join(args)}".strip()
        full_cmd = f"LIST {sub_cmd}"
        self.sock.cmd(full_cmd)
        head_response = self.sock.read_line()
        if head_response != f"BEGIN LIST {sub_cmd}\n":
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {head_response}")

        while True:
            response = self.sock.read_line()
            if response == f"END LIST {sub_cmd}\n":
                break
            if not response.startswith(sub_cmd):
                raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {response}")
            consumer(response[len(sub_cmd) + 1 : -1])

    def list_ups(self) -> dict:
        """
        List the UPSes on the NUT server.

        Returns:
        - ups_dict: A dictionary of UPS names and descriptions.
        """
        ups_dict = {}

        def accept(line: str):
            name, description = line.split(" ", 1)
            ups_dict.update({name: description.strip('"').strip()})

        self.___exec_list(LIST.UPS, accept)
        return ups_dict

    def list_vars(self, upsname: str) -> dict:
        """
        List the variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        vars_dict = {}

        def accept(line: str) -> dict:
            var, value = line.split(" ", 1)
            vars_dict.update({var: value.strip('"').strip()})

        self.___exec_list(LIST.VAR, accept, upsname)
        return vars_dict

    def list_rw_vars(self, upsname: str) -> dict:
        """
        List the read-write variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        vars_dict = {}

        def accept(line: str) -> dict:
            var, value = line.split(" ", 1)
            vars_dict.update({var: value.strip('"').strip()})

        self.___exec_list(LIST.RW, accept, upsname)
        return vars_dict

    def list_cmds(self, upsname: str) -> List[str]:
        """
        List the commands for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        cmds = []

        def accept(line: str):
            cmds.append(line)

        self.___exec_list(LIST.CMD, accept, upsname)
        return cmds

    def list_enum(self, upsname: str, var: str) -> List[str]:
        """
        List the enumeration values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        emums = []

        def accept(line: str):
            _, value = line.split(" ", 1)
            emums.append(value)

        return self.___exec_list(LIST.ENUM, accept, upsname, var)

    def list_range(self, upsname: str, var: str) -> List[dict]:
        """
        List the range values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        ranges: List[dict] = []

        def accept(line: str) -> dict:
            min, max = line.split(" ", 1)
            ranges.append({"min": min, "max": max})

        self.___exec_list(LIST.RANGE, accept, upsname, var)
        return ranges

    def list_clients(self, upsname: str) -> List[str]:
        """
        List the clients connected to the NUT server.

        Returns:
        - str: The response from the NUT server.
        """
        clients = []

        def accept(line: str):
            clients.append(line)

        self.___exec_list(LIST.CLIENT, accept, upsname)
        return clients

    def __exec_set(self, command: SET, *args: str) -> str:
        """
        Execute a SET command on the NUT.

        Parameters:
        - command (SET): The SET sub-command.
        - args (str): The arguments for the SET sub-command.

        Returns:
        - str: tracking ID. This is a unique identifier for the tracking operation.
        """

        full_cmd = f"SET {command.value} {' '.join(args)}"
        self.sock.cmd(full_cmd)
        raw_response = self.sock.read_line()
        if raw_response.startswith("ERR "):
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {raw_response}")

        if raw_response.startswith("OK TRACKING "):
            return raw_response[len("OK TRACKING ") : -1]
        elif raw_response == "OK\n":
            return None
        else:
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {raw_response}")

    def set_var(self, upsname: str, var: str, value: str) -> str:
        """
        Set the value of a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.
        - value (str): The value to set the variable to.

        Returns:
        - str: tracking ID. This is a unique identifier for the tracking operation.
        """
        return self.__exec_set(SET.VAR, upsname, var, f'"{value}"')

    def tracking_on(self):
        """
        Turn on tracking for the NUT server.
        """
        return self.__exec_set(SET.TRACKING, "ON")

    def tracking_off(self):
        """
        Turn off tracking for the NUT server.
        """
        return self.__exec_set(SET.TRACKING, "OFF")

    def run_cmd(self, upsname: str, cmd: str, *args: str) -> str:
        """
        Execute an instant command on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - cmd (str): The name of the command.

        Returns:
        - str: tracking ID. This is a unique identifier for the tracking operation.
        """
        full_cmd = f"INSTCMD {upsname} {cmd}"
        if args:
            full_cmd += f' {" ".join(args)}'
        self.sock.cmd(full_cmd)
        raw_response = self.sock.read_line()
        if raw_response.startswith("ERR "):
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {raw_response}")

        if raw_response.startswith("OK TRACKING "):
            return raw_response[len("OK TRACKING ") : -1]
        elif raw_response == "OK\n":
            return None
        else:
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {raw_response}")
