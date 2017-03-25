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
__version__ = "2"

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

    This class is not intended to be used directly from your code but
    by the hook variable `XymonClient.msg`.
    """
    def __init__(self):
        self.__message = ''
        self.__footer = None

        self.message_color = STATUS_OK
        """default criticity"""

    @staticmethod
    def _get_date():
        """Return the current date."""
        return datetime.now().strftime('%c')

    @staticmethod
    def _get_machine():
        """Get the environment variable `MACHINE` exported by Xymon."""
        return os.environ.get('MACHINE')

    def set_color(self, new_color):
        """
        Set the color (message criticity level) to `new_color`.
        Note that the color is not updated when `new_colo` has a criticity
        lower than the global `message_color`.
        """
        if new_color not in _ALL_COLORS:
            raise RuntimeError('Illegal color for xymon: {0}'.format(new_color))
        current_color_index = _ALL_COLORS.index(self.message_color)
        new_color_index = _ALL_COLORS.index(new_color)
        if new_color_index > current_color_index:
            self.message_color = new_color

    def title(self, text):
        """Set the message title, rendered in HTML."""
        self.__message += '<br><h1>{0}</h1><hr><br>'.format(text)

    def section(self, title, body):
        """Renders a section in HTML, with `title` and content `body`."""
        self.__message += (
            '<h2>{0}</h2><p>{1}</p><br>'.format(title, body))

    def footer(self, version):
        """Set the message footer (script name and version)."""
        self.__footer = (
            '<br>'
            '<center>xymon script: {0} version {1}</center>'.format(
                *version))

    def render(self, test):
        """
        Return the message string in a format accepted by the xymon server.
        """
        date = self._get_date()
        machine = self._get_machine()
        if self.message_color not in _ALL_COLORS:
            raise RuntimeError(
                'Illegal color for xymon: {0}'.format(self.message_color))
        html = (self.__message if not self.__footer else
            self.__message + self.__footer)
        return 'status {0}.{1} {2} {3}\n{4}\n'.format(
            machine, test, self.message_color[1:], date, html)

class XymonClient(object):
    """
    Class for managing and sending the final message to the Xymon server.

    Usage:
        import pyxymon as pymon

        xymon = pymon.XymonClient(check_name)

        # do your logic...
        # you can set the criticity of the final xymon message by using:
        #    xymon.set_color(pymon.STATUS_WARNING)
        # or
        #    xymon.set_color(pymon.STATUS_CRITICAL)
        # The default criticity is 'pymon.STATUS_OK'

        xymon.msg.title('Title in the xymon check page')
        xymon.msg.section('Section Title',
                          'Text containing the lines you want to display')
        # You can add here other sections, if required.
        xymon.msg.footer(check_version)
        xymon.send()
    """
    def __init__(self, test):
        self.test = test
        """Name of the Xymon test"""

        self._msg = XymonMessage()
        """Xymon message hook"""

        self.set_color = self._msg.set_color
        self.title = self._msg.title
        self.section = self._msg.section
        self.footer = self._msg.footer
        """Provide the methods available in XymonMessage"""

    @staticmethod
    def _get_xymon_server_name():
        """
        Return the Xymon server name by looking at the env variable XYMSRV.
        """
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
        """Send a rendered message to the xymon server."""
        self.server = self._get_xymon_server_name()
        self.port = self._get_xymon_server_port()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server, self.port))
        xymon_string = self._msg.render(self.test)
        sock.send(xymon_string)
        sock.close()
