# -*- coding: utf-8 -*-

"""
Simple Helper Class intended for creation of Xymon Extension Modules in Python.

This Python module provides a simple class that aims simplify the creation of
Xymon Extension Modules in Python.

SPDX-License-Identifier: GPL-3.0
"""

__author__ = "Davide Madrisan <davide.madrisan.gmail.com>"
__copyright__ = "Copyright 2017 Davide Madrisan"
__license__ = "GPL-3.0"
__status__ = "Stable"
__version__ = "1"

from datetime import datetime
import os
import socket

__all__ = ['XymonClient', 'XymonMessage']

class XymonMessage(object):
    """
    Private class for rendering the message that will be sent to the
    Xymon server.

    This class is not intended to be used directly from your code but
    by the hook variable `XymonClient.msg`.
    """

    OK = '&green'   # pylint: disable-msg=C0103
    WARNING = '&yellow'
    CRITICAL = '&red'
    __ALL_COLORS__ = (OK, WARNING, CRITICAL)

    def __init__(self):
        self.__message = ''

        self.__footer = None
        """list of all the allower colors (criticity levels)"""

        self.message_color = self.OK
        """default criticity"""

    @staticmethod
    def __get_date():
        """Return the current date."""
        return datetime.now().strftime('%c')

    @staticmethod
    def __get_machine():
        """Get the environment variable `MACHINE` exported by Xymon."""
        return os.environ.get('MACHINE')

    def color(self, new_color):
        """
        Set the color (message criticity level) to `new_color`.
        Note that the color is not updated when `new_colo` has a criticity
        lower than the global `message_color`.
        """
        if new_color not in self.__ALL_COLORS__:
            raise RuntimeError('Illegal color for xymon: {0}'.format(new_color))
        current_color_index = self.__ALL_COLORS__.index(self.message_color)
        new_color_index = self.__ALL_COLORS__.index(new_color)
        if new_color_index > current_color_index:
            self.message_color = new_color

    def append(self, text):
        """Append `text` to the current Xymon messsage."""
        self.__message += text

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
        date = self.__get_date()
        machine = self.__get_machine()
        if self.message_color not in self.__ALL_COLORS__:
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
        xymon = pymon.XymonClient(check_name)

        # do your logic...
        # you can set the criticity of the final xymon message by using:
        #    xymon.msg.color(xymon.msg.WARNING)
        # or
        #    xymon.msg.color(xymon.msg.CRITICAL)
        # The default criticity is 'xymon.msg.OK'

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
        self.server = self.__get_xymon_server_name()
        """Xymon server name"""
        self.port = self.__get_xymon_server_port()
        """Xymon server port"""
        self.msg = XymonMessage()
        """Xymon message hook"""

    @staticmethod
    def __get_xymon_server_name():
        """
        Return the Xymon server name by looking at the env variable XYMSRV.
        """
        return os.environ.get('XYMSRV')

    @staticmethod
    def __get_xymon_server_port():
        """
        Return the Xymon server port by looking at the env variable XYMONDPORT
        or the default port 1984 if such a variable does not exist.
        """
        xymon_port = os.environ.get('XYMONDPORT', 1984)
        return int(xymon_port)

    def send(self):
        """Send a rendered message to the xymon server."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server, self.port))
        xymon_string = self.msg.render(self.test)
        sock.send(xymon_string)
        sock.close()
