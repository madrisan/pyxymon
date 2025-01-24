# -*- coding: utf-8 -*-

"""Helper class intended for creation of Xymon Extension Modules in Python.

This simple Python module provides a simple helper class that aims simplify
 the creation of Xymon Extension Modules in Python.
"""

__all__ = ['XymonClient',
           'STATUS_OK', 'STATUS_WARNING', 'STATUS_CRITICAL']

__author__ = "Davide Madrisan <davide.madrisan.gmail.com>"
__copyright__ = "Copyright 2017 Davide Madrisan"
__license__ = "GPL-3.0"
__status__ = "Production"
__version__ = "3"

from datetime import datetime
import os
import socket

STATUS_OK = '&green'
STATUS_WARNING = '&yellow'
STATUS_CRITICAL = '&red'

_ALL_COLORS = (STATUS_OK, STATUS_WARNING, STATUS_CRITICAL)
"""list of all the allower colors (criticity levels)"""

class XymonMessage(object):
    """Class for rendering the Xymon messages that will be sent to the server.

    Note:
        This class is not intended to be used directly from your code.
    """
    def __init__(self):
        self._message = ''
        self._footer = None
        self._color = STATUS_OK
        self._lifetime = None
        """default criticity"""

    @staticmethod
    def _get_date():
        """Return the current date."""
        return datetime.now().strftime('%c')

    @staticmethod
    def _get_machine():
        """Get the environment variable `MACHINE` exported by Xymon.

        Raises:
            RuntimeError: If `MACHINE` is not set.
        """
        xymon_machine = os.environ.get('MACHINE')
        if not xymon_machine:
            raise RuntimeError('The environment variable MACHINE is not set')
        return xymon_machine

    @property
    def color(self):
        """Return the current color (message criticity level)."""
        return self._color

    @color.setter
    def color(self, value):
        """Set the color (message criticity level) to `value`.

        Note:
            The color is not updated when `value` has a criticity
            lower than the current one `self._color`.

        Attributes:
            value (str): The new color to be set.
                         The following colors are the only valid ones:
                           - pyxymon.STATUS_OK
                           - pyxymon.STATUS_WARNING
                           - pyxymon.STATUS_CRITICAL
        Raises:
            ValueError: If `value` is not a valid color string.
        """
        if value not in _ALL_COLORS:
            raise ValueError('Illegal color for xymon: {0}'.format(value))
        current_color_index = _ALL_COLORS.index(self._color)
        new_color_index = _ALL_COLORS.index(value)
        if new_color_index > current_color_index:
            self._color = value

    @property
    def lifetime(self):
        """Return lifetime in minutes in xymon format (str)"""
        return ''.join(['+', str(self._lifetime)]) if self._lifetime else ''

    @lifetime.setter
    def lifetime(self, value):
        """Set the lifetime in minutes (time until purple) to `value`"""
        try:
            self._lifetime = int(value)
        except ValueError:
            raise ValueError('value must be a number: {0}'.format(value))

    def title(self, text):
        """Set the message title.

        Attributes:
            text (str): The string containing the title.
        """
        self._message += '<br><h1>{0}</h1><hr><br>'.format(text)

    def section(self, title, body):
        """Add a section to the Xymon message.

        Attributes:
            title (str): The string containing the title of this section.
            body (str): The content of the section.
        """
        self._message += (
            '<h2>{0}</h2><p>{1}</p><br>'.format(title, body))

    def footer(self, check_filename, check_version):
        """Add a footer the the Xymon message.

        Attributes:
            check_filename (str): The name of the check script.
            check_version (str): The version of the check script.
        """
        self._footer = (
            '<br>'
            '<center>xymon script: {0} version {1}</center>'.format(
                check_filename, check_version))

    def _render(self, test):
        """Return the message string in a format accepted by the Xymon server.

        Attributes:
            test (str): The string containing the name of the Xymon test.

        Raises:
            RuntimeError: If `self._color` is an illegal color
                          (this should never happen).
        """
        date = self._get_date()
        machine = self._get_machine()
        if self._color not in _ALL_COLORS:
            raise RuntimeError(
                'Illegal color for xymon: {0}'.format(self._color))
        html = (self._message if not self._footer else
                self._message + self._footer)
        return 'status{0} {1}.{2} {3} {4}\n{5}\n'.format(
            self.lifetime, machine, test, self._color[1:], date, html)

class XymonClient(XymonMessage):
    """Class for managing and sending the final message to the Xymon server.

    Attributes:
        test (str): Name of the Xymon test.

    Usage:
        import os
        import pyxymon as pymon
        check_name = 'mytest'
        check_version = 1
        check_filename = os.path.basename(__file__)
        xymon = pymon.XymonClient(check_name)
        # do your logic...
        # you can set the criticity of the final xymon message by using:
        #    xymon.color = pymon.STATUS_WARNING
        # or
        #    xymon.color = pymon.STATUS_CRITICAL
        # The criticity is set by default to 'pymon.STATUS_OK'
        xymon.title('Title in the xymon check page')
        xymon.section('Section Title',
                      'Text containing the lines you want to display')
        # You can add here other sections, if required.
        xymon.footer(check_filename, check_version)
        xymon.send()
    """
    def __init__(self, test):
        XymonMessage.__init__(self)
        self.test = test
        """Name of the Xymon test"""

    @staticmethod
    def _get_xymon_server_name():
        """Return the content of the environment variable XYMONSERVERS.

        Raises:
            RuntimeError: If `XYMONSERVERS` is not set.
        """
        xymon_server = os.environ.get('XYMONSERVERS')
        if not xymon_server:
            RuntimeError('The environment variable XYMONSERVERS is not set')
        return os.environ.get('XYMONSERVERS')
     
    @staticmethod
    def _get_xymon_server_port():
        """Return the content of the environment variable XYMONDPORT.

        Note:
            The default Xymon port (1984) is returned, when such a variable
            does not exist.
        """
        xymon_port = os.environ.get('XYMONDPORT', 1984)
        return int(xymon_port)

    def send(self):
        """Send a rendered message to the xymon server.

        Note:
            The server and port are read from the environment variables
            XYMSRV and XYMONDPORT (default set to 1984 when not found).
        """
        servers = self._get_xymon_server_name().split(' ')
        port = self._get_xymon_server_port()
        xymon_string = self._render(self.test)
        for server in servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server, port))
            sock.send(xymon_string.encode('utf-8'))
            sock.close()
