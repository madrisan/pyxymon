#!/usr/bin/python

# -*- coding: utf-8 -*-
'''
Python boilerplate code for Xymon modules
Copyright (C) 2017 Davide Madrisan <davide.madrisan.gmail.com>
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
        
    def __get_date(self):
        return datetime.now().strftime('%c')

    def __get_machine(self):
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
        self.server = os.environ.get('XYMSRV')
        self.port = os.environ.get('XYMONDPORT')
        self.msg = XymonMessage()

    def send(self):
        '''
        Send a message to the xymon server
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server, int(self.port)))
        xymon_string = self.msg.render(self.test)
        s.send(xymon_string)
        s.close()
