import logging
import nutsock
from enum import Enum
from typing import List, Callable, Dict, Union, Type, TypeVar
import nutvartypes

class NutClientError(Exception):
    """NUT (Network UPS Tools) client base exception."""

class NutClientCmdError(NutClientError):
    """NUT (Network UPS Tools) client CMD exception."""

class NutClient:
    """NUT (Network UPS Tools) client."""

    LOG = logging.getLogger(__name__)

    def __init__(self, host="127.0.0.1", port=nutsock.DEF_PORT, timeout=nutsock.DEF_TIMEOUT):
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

    def session(self):
        """
        Create a new NUT session.

        Returns:
        - NutSession: A new NUT session.
        """
        return NutSession(self.host, self.port, self.timeout)

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

EXEC_LIST_T = TypeVar('EXEC_LIST_T', bound=Union[Dict[str, str], List[str]])

class NutSession:
    """NUT (Network UPS Tools) session."""

    LOG = logging.getLogger(__name__)

    def __init__(self, host: str="127.0.0.1", port: int=nutsock.DEF_PORT, timeout: float=nutsock.DEF_TIMEOUT):
        """
        Class initialization method.

        Parameters:
        - host (str): The hostname or IP address of the NUT server.
        - port (int): The port number of the NUT server.
        - timeout (int): The timeout in seconds for the socket connection.
        """
        self.sock = nutsock.NutSock(host, port, timeout)

    def __enter__(self):
        self.LOG.debug("Opening NUT connection")
        self.sock.connect()
        return self

    def __exit__(self, *args):
        self.LOG.debug("Closing NUT connection")
        if self.sock:
            self.sock.close()
        self.sock = None

    def exec_get(self, command: GET, *args: str) -> str:
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
        return raw_response[len(expected_start):-1]

    def num_logins(self, upsname: str) -> int:
        """
        Get the number of clients which have done LOGIN for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - int: The number of clients which have done LOGIN for this UPS. This is used by the upsmon in primary mode to determine how many clients are still connected when starting the shutdown process.
        """
        try:
            value = int(self.exec_get(GET.NUMLOGINS, upsname))
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
            return self.exec_get(GET.UPSDESC, upsname).strip('"')
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
            return self.exec_get(GET.VAR, upsname, var).strip('"')
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
            for type in self.exec_get(GET.TYPE, upsname, var).split(" "):
                pos = type.find(":")
                if pos != -1:
                    types.append(nutvartypes.StringType(max_length=int(type[pos+1:])))
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
            return self.exec_get(GET.DESC, upsname, var).strip('"')
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
            return self.exec_get(GET.CMDDESC, upsname, cmd).strip('"')
        except IndexError:
            raise NutClientCmdError("Invalid response from 'GET CMDDESC' command")

    def exec_list(self, command: LIST, result_type: Type[EXEC_LIST_T], converter: Callable[[str], Type[EXEC_LIST_T]], *args: str) -> EXEC_LIST_T:
        """
        Retrieve a list response from the NUT server.

        Parameters:
        - command (LIST): The LIST sub-command.
        - result_type (Type[T]): The type of the result (dict or list).
        - converter (Callable[[str], Type[T]]): Function to convert response lines into the desired format.
        - args (str): The arguments for the LIST sub-command.

        Returns:
        - T: The response from the NUT server.
        """
        sub_cmd = f"{command.value} {' '.join(args)}".strip()
        full_cmd = f"LIST {sub_cmd}"
        self.sock.cmd(full_cmd)
        head_response = self.sock.read_line()
        if head_response != f"BEGIN LIST {sub_cmd}\n":
            raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {head_response}")

        data: EXEC_LIST_T
        if result_type == dict:
            data = {}
        elif result_type == list:
            data = []
        else:
            raise NutClientCmdError(f"Invalid type '{type}'")

        while True:
            response = self.sock.read_line()
            if response == f"END LIST {sub_cmd}\n":
                break
            if not response.startswith(sub_cmd):
                raise NutClientCmdError(f"Invalid response from '{full_cmd}' comand: {response}")

            val = converter(response[len(sub_cmd)+1:-1])
            if result_type == dict:
                data.update(val)
            elif result_type == list:
                data.append(val)

        return data

    def list_ups(self) -> dict:
        """
        List the UPSes on the NUT server.

        Returns:
        - ups_dict: A dictionary of UPS names and descriptions.
        """
        def parse(line: str) -> dict:
            name, description = line.split(" ", 1)
            return {name: description.strip('"').strip()}

        return self.exec_list(LIST.UPS, dict, parse)

    def list_vars(self, upsname: str) -> dict:
        """
        List the variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        def parse_var(line: str) -> dict:
            var, value = line.split(" ", 1)
            return {var: value.strip('"').strip()}

        return self.exec_list(LIST.VAR, dict, parse_var, upsname)

    def list_rw_vars(self, upsname: str) -> dict:
        """
        List the read-write variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        def parse_var(line: str) -> dict:
            var, value = line.split(" ", 1)
            return {var: value.strip('"').strip()}

        return self.exec_list(LIST.RW, dict, parse_var, upsname)

    def list_cmds(self, upsname: str) -> List[str]:
        """
        List the commands for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """

        return self.exec_list(LIST.CMD, list, lambda v: v, upsname)

    def list_enum(self, upsname: str, var: str) -> List[str]:
        """
        List the enumeration values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        def parse(line: str) -> str:
            _, value = line.split(" ", 1)
            return value

        return self.exec_list(LIST.ENUM, list, parse, upsname, var)

    def list_range(self, upsname: str, var: str) -> List[dict]:
        """
        List the range values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        def parse(line: str) -> dict:
            min, max = line.split(" ", 1)
            return {"min": min, "max": max}

        return self.exec_list(LIST.RANGE, list, parse, upsname, var)

    def list_clients(self, upsname: str) -> List[str]:
        """
        List the clients connected to the NUT server.

        Returns:
        - str: The response from the NUT server.
        """

        return self.exec_list(LIST.CLIENT, list, lambda v: v, upsname)
