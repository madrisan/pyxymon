# -*- coding: utf-8 -*-

"""
Simple Helper Class intended for creation of Xymon Extension Modules in Python.

This Python module provides a simple class that aims simplify the creation of
Xymon Extension Modules in Python.
"""

__author__ = "Davide Madrisan <davide.madrisan.gmail.com>"
__copyright__ = "Copyright 2017 Davide Madrisan"
__license__ = "GPL-3.0"
__status__ = "Stable"
__version__ = "3"

STATUS_OK = '&green'
STATUS_WARNING = '&yellow'
STATUS_CRITICAL = '&red'

__all__ = ['XymonClient',
           'STATUS_OK', 'STATUS_WARNING', 'STATUS_CRITICAL']

from datetime import datetime
import os
import socket

_ALL_COLORS = (STATUS_OK, STATUS_WARNING, STATUS_CRITICAL)
"""list of all the allower colors (criticity levels)"""

class XymonMessage(object):
    """
    Private class for rendering the message that will be sent to the
    Xymon server.

    This class is not intended to be used directly from your code.
    """
    def __init__(self):
        self._message = ''
        self._footer = None
        self._color = STATUS_OK
        """default criticity"""

    @staticmethod
    def _get_date():
        """Return the current date."""
        return datetime.now().strftime('%c')

    @staticmethod
    def _get_machine():
        """Get the environment variable `MACHINE` exported by Xymon."""
        return os.environ.get('MACHINE')

    @property
    def color(self):
        """Return the current color (message criticity level)."""
        return self._color

    @color.setter
    def color(self, value):
        """
        Set the color (message criticity level) to `value`.

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

    def footer(self, version):
        """Add a footer the the Xymon message.

        Attributes:
            version (str): Usually the script name with version.
        """
        self._footer = (
            '<br>'
            '<center>xymon script: {0} version {1}</center>'.format(
                *version))

    def _render(self, test):
        """
        Return the message string in a format accepted by the xymon server.

        Attributes:
            test (str): The string containing the name of the Xymon test.
        """
        date = self._get_date()
        machine = self._get_machine()
        if self._color not in _ALL_COLORS:
            raise RuntimeError(
                'Illegal color for xymon: {0}'.format(self._color))
        html = (self._message if not self._footer else
                self._message + self._footer)
        return 'status {0}.{1} {2} {3}\n{4}\n'.format(
            machine, test, self._color[1:], date, html)

class XymonClient(XymonMessage):
    """
    Class for managing and sending the final message to the Xymon server.

    Attributes:
        test (str): Name of the Xymon test.

    Usage:
        import pyxymon as pymon
        check_name = 'mytest'
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
        xymon.footer(check_version)
        xymon.send()
    """
    def __init__(self, test):
        XymonMessage.__init__(self)
        self.test = test
        """Name of the Xymon test"""

    @staticmethod
    def _get_xymon_server_name():
        """
        Return the Xymon server name by looking at the env variable XYMSRV.
        """
        xymon_server = os.environ.get('XYMSRV')
        if not xymon_server:
            RuntimeError('The environment variable XYMSRV is not set')
        return os.environ.get('XYMSRV')

    @staticmethod
    def _get_xymon_server_port():
        """
        Return the Xymon server port by looking at the env variable XYMONDPORT
        or the default port 1984 if such a variable does not exist.
        """
        xymon_port = os.environ.get('XYMONDPORT', 1984)
        return int(xymon_port)

    def send(self):
        """Send a rendered message to the xymon server.

        Note:
            The server and port are read from the environment variables
            XYMSRV and XYMONDPORT (default set to 1984 when not found).
        """
        server = self._get_xymon_server_name()
        port = self._get_xymon_server_port()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server, port))
        xymon_string = self._render(self.test)
        sock.send(xymon_string)
        sock.close()
