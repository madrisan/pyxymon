#!/usr/bin/python

# -*- coding: utf-8 -*-
'''
Python boilerplate code for Xymon modules
Copyright (C) 2017 Davide Madrisan <davide.madrisan.gmail.com>
License: https://opensource.org/licenses/GPL-3.0
'''

from datetime import datetime
import os
import socket

class XymonMessage(object):
    def __init__(self):
        self.__message = ''
        self.__footer = None
        self.OK = '&green'
        self.WARNING = '&yellow'
        self.CRITICAL = '&red'
        self.__all_colors = [
            self.OK, self.WARNING, self.CRITICAL]
        self.message_color = self.OK

    @staticmethod
    def __get_date():
        return datetime.now().strftime('%c')

    @staticmethod
    def __get_machine():
        return os.environ.get('MACHINE')

    def color(self, new_color):
        '''
        Modify the xymon color (criticity level)
        '''
        if new_color not in self.__all_colors:
            raise RuntimeError('Illegal color for xymon: {0}'.format(new_color))
        # update the color only if it will raise the criticity
        current_color_index = self.__all_colors.index(self.message_color)
        new_color_index = self.__all_colors.index(new_color)
        if new_color_index > current_color_index:
            self.message_color = new_color

    def append(self, text):
        self.__message += text

    def title(self, text):
        self.__message += '<br><h1>{0}</h1><hr><br>'.format(text)

    def section(self, title, body):
        self.__message += (
            '<h2>{0}</h2><p>{1}</p><br>'.format(title, body))

    def footer(self, version):
        self.__footer = (
            '<br>'
            '<center>xymon script: {0} version {1}</center>'.format(
                *version))

    def render(self, test):
        '''
        Return the message string in a format accepted by the xymon server.
        '''
        date = self.__get_date()
        machine = self.__get_machine()
        if self.message_color not in self.__all_colors:
            raise RuntimeError(
                'Illegal color for xymon: {0}'.format(self.message_color))
        html = (self.__message if not self.__footer else
            self.__message + self.__footer)
        return 'status {0}.{1} {2} {3}\n{4}\n'.format(
            machine, test, self.message_color[1:], date, html)

class XymonClient(object):
    def __init__(self, test):
        self.test = test
        self.server = self.__get_xymon_server_name()
        self.port = self.__get_xymon_server_port()
        self.msg = XymonMessage()

    @staticmethod
    def __get_xymon_server_name():
        '''
        Return the Xymon server name by looking at the env variable XYMSRV
        '''
        return os.environ.get('XYMSRV')

    @staticmethod
    def __get_xymon_server_port():
        '''
        Return the Xymon server port by looking at the env variable XYMONDPORT
        or the default port 1984 if such a variable does not exist
        '''
        xymon_port = os.environ.get('XYMONDPORT', 1984)
        return int(xymon_port)

    def send(self):
        '''
        Send a message to the xymon server
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server, self.port))
        xymon_string = self.msg.render(self.test)
        s.send(xymon_string)
        s.close()
