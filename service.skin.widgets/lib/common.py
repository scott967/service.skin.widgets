#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012-2013 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
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

"""provide defaults and utility functions
"""

import xbmc
import xbmcaddon
import xbmcvfs

### get addon info
addon       = xbmcaddon.Addon(id='service.skin.widgets')
ADDONID     = addon.getAddonInfo('id')
ADDONNAME   = addon.getAddonInfo('name')
AUTHOR      = addon.getAddonInfo('author')
VERSION     = addon.getAddonInfo('version')
ADDONPATH   = addon.getAddonInfo('path')
ADDONPROFILE= xbmcvfs.translatePath(addon.getAddonInfo('profile'))
ICON        = addon.getAddonInfo('icon')
LOCALIZE    = addon.getLocalizedString
MONITOR     = xbmc.Monitor()
LIMIT       = 20

def log(txt:str):
    """Output to Kodi debug log

    Args:
        txt (str): the message to log
    """
    message = f'{ADDONNAME}: {txt}'
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)
