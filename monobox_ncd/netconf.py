#!/usr/bin/env python
# -*- coding: utf-8 -*-

# GNU General Public Licence (GPL)
# 
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA
#
# Copyright (c) 2015 by OXullo Intersecans / bRAiNRAPERS

import os
import re
import subprocess
import shlex

def _invoke(command):
    proc = subprocess.Popen(shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    (out, err) = proc.communicate()

    if err:
        for line in err.split('\n'):
            line = line.strip()
            if line:
                logging.error('%s: %s' % (command, line))

    if proc.returncode != 0:
        raise RuntimeError('Command %s failed with rc %d' % (command, proc.returncode))

    return (out, proc.returncode)


class WifiAccessPoint(object):
    FIELDS = ('cell', 'ssid', 'signalStrength', 'signalLevel',
            'open', 'channel', 'mode', 'connected')

    def __init__(self, **kwargs):
        for field in self.FIELDS:
            setattr(self, field, None)

        for field, value in kwargs.iteritems():
            setattr(self, field, value)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                ', '.join(['%s=%s' % (key, val)
                        for key, val in self.__dict__.iteritems()]))


class Interface(object):
    def __init__(self, device):
        if not device in self.available_devices():
            raise RuntimeError('Unknown interface %s' % device)

        self.device = device

    def scan(self):
        current_cell = self._get_current_connection_cell()

        try:
            (data, rc) = _invoke('iwlist %s scan' % self.device)
        except RuntimeError:
            raise WifiConfigError('Wifi interface is not active')

        stations = []
        currentAp = None
        for line in data.split('\n'):
            match = re.search(r'Cell \d+ \- Address: ([\da-fA-F:]+)$', line)
            if match:
                cell = match.group(1)

                currentAp = WifiAccessPoint(cell=cell)
                stations.append(currentAp)

            if currentAp is None:
                continue

            if cell == current_cell:
                currentAp.connected = True
            else:
                currentAp.connected = False

            self._update_ap(currentAp, line)

        return sorted(stations, key=lambda station: station.signalStrength, reverse=True)

    def _update_ap(self, ap, line):
        match = re.search(r'ESSID:"(.+)"', line)
        if match:
            ap.ssid = match.group(1)

        match = re.search(r'Quality=(\d+)/(\d+)  Signal level=(.+) dBm', line)
        if match:
            sigStrength = int(float(match.group(1)) / float(match.group(2)) * 100)
            ap.signalStrength = sigStrength
            ap.signalLevel = match.group(3) + ' dBm'

        match = re.search(r'Encryption key:(\w+)$', line)
        if match:
            ap.open = match.group(1) == 'off'

        match = re.search(r'Channel:(\d+)', line)
        if match:
            ap.channel = int(match.group(1))

        match = re.search(r'Mode:(.+)$', line)
        if match:
            ap.mode = match.group(1)

    def _get_current_connection_cell(self):
        (data, rc) = _invoke('iwconfig %s' % self.device)

        match = re.search(r'Access Point: ([\da-fA-F:]+)', data)
        if match:
            return match.group(1).strip()

        return None

    @classmethod
    def available_devices(cls):
        return os.listdir('/sys/class/net/')


if __name__ == '__main__':
    intf = Interface('wlan0')
    print intf.scan()
