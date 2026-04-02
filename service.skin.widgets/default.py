#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-Kodi
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on script.randomitems & script.wacthlist
#    Thanks to their original authors
#
# pylint: disable=line-too-long,invalid-name,unused-argument

"""Module is the driver for the addon.  see lib/widgets.py main class

"""

from lib.class_xbmc import Widgets_Monitor, Widgets_Player
from lib.utils import ADDONVERSION, log
from lib.widgets import Main

if __name__ == "__main__":
    log(f'script version {ADDONVERSION} started')
    Main()
    del Widgets_Monitor
    del Widgets_Player
    del Main
    log(f'script version {ADDONVERSION} stopped')
