import logging
import nutsock

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

    def list_ups(self):
        """
        List the UPSes on the NUT server.

        Returns:
        - ups_dict: A dictionary of UPS names and descriptions.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = "LIST UPS"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != "BEGIN LIST UPS\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until("END LIST UPS\n")

        ups_dict = {}
        for line in raw_result.split("\n"):
            if line.startswith("UPS "):
                _, name, description = line.split(" ", 2)
                description = description.strip('"')
                ups_dict[name] = description
        return ups_dict

    def ups_num_logins(self, upsname):
        """
        Get the number of clients which have done LOGIN for a UPS.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - int: The number of clients which have done LOGIN for this UPS.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET NUMLOGINS {upsname}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"NUMLOGINS {upsname} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = int(raw_result.split(" ")[2])
            return value
        except (IndexError, ValueError):
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

    def ups_desc(self, upsname):
        """
        Get the description of a UPS.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The description of the UPS.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET UPSDESC {upsname}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"UPSDESC {upsname} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = raw_result.split('"')[1]
            return value
        except IndexError:
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

    def list_vars(self, upsname):
        """
        List the variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"LIST VAR {upsname}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != f"BEGIN LIST VAR {upsname}\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until(f"END LIST VAR {upsname}\n")

        vars_dict = {}
        for line in raw_result.split("\n"):
            if line.startswith("VAR "):
                _, _, var, value = line.split(" ", 3)
                vars_dict[var] = value.strip('"').strip()
        return vars_dict

    def list_rw_vars(self, upsname):
        """
        List the read-write variables for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"LIST RW {upsname}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != f"BEGIN LIST RW {upsname}\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until(f"END LIST RW {upsname}\n")

        vars_dict = {}
        for line in raw_result.split("\n"):
            if line.startswith("RW "):
                _, _, var, value = line.split(" ", 3)
                vars_dict[var] = value.strip('"').strip()
        return vars_dict

    def list_enum(self, upsname, var):
        """
        List the enumeration values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"LIST ENUM {upsname} {var}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != f"BEGIN LIST ENUM {upsname} {var}\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until(f"END LIST ENUM {upsname} {var}\n")

        values = []
        for line in raw_result.split("\n"):
            if line.startswith("ENUM "):
                _, _, _, value = line.split(" ", 3)
                values.append(value.strip('"').strip())
        return values

    def list_range(self, upsname, var):
        """
        List the range values for a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The response from the NUT server.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"LIST RANGE {upsname} {var}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != f"BEGIN LIST RANGE {upsname} {var}\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until(f"END LIST RANGE {upsname} {var}\n")

        list_range = []
        for line in raw_result.split("\n"):
            if line.startswith("RANGE "):
                _, _, _, min, max = line.split(" ", 4)
                list_range.append({"min": min, "max": max})
        return list_range

    def var_value(self, upsname, var):
        """
        Get the value of a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The value of the variable.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET VAR {upsname} {var}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"VAR {upsname} {var} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = raw_result.split('"')[1]
            return value
        except IndexError:
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

    def var_type(self, upsname, var):
        """
        Get the type of a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The type of the variable.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET TYPE {upsname} {var}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"TYPE {upsname} {var} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = raw_result.split(" ")[3].strip()
            return value
        except IndexError:
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

    def var_desc(self, upsname, var):
        """
        Get the description of a variable for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - var (str): The name of the variable.

        Returns:
        - str: The description of the variable.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET DESC {upsname} {var}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"DESC {upsname} {var} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = raw_result.split('"')[1]
            return value
        except IndexError:
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

    def list_cmds(self, upsname):
        """
        List the commands for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.

        Returns:
        - str: The response from the NUT server.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"LIST CMD {upsname}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if raw_result != f"BEGIN LIST CMD {upsname}\n":
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
            raw_result = sock.read_until(f"END LIST CMD {upsname}\n")

        cmd_list = []
        for line in raw_result.split("\n"):
            if line.startswith("CMD "):
                _, _, cmd = line.split(" ", 3)
                cmd_list.append(cmd)
        return cmd_list

    def cmd_desc(self, upsname, cmd):
        """
        Get the description of a command for a UPS on the NUT server.

        Parameters:
        - upsname (str): The name of the UPS.
        - cmd (str): The name of the command.

        Returns:
        - str: The description of the command.
        """
        with nutsock.NutSock(self.host, self.port, self.timeout) as sock:
            sock.connect()
            command = f"GET CMDDESC {upsname} {cmd}"
            sock.cmd(command)
            raw_result = sock.read_until("\n")
            if not raw_result.startswith(f"CMDDESC {upsname} {cmd} "):
                raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")

        try:
            value = raw_result.split('"')[1]
            return value
        except IndexError:
            raise NutClientCmdError(f"Invalid response from '{command}' comand: {raw_result}")
