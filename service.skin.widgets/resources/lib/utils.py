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

"""Utility functions

"""

import os
import urllib.request

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONVERSION = ADDON.getAddonInfo('version')
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
LOCALIZE = ADDON.getLocalizedString


def log(txt: str) -> None:
    """writes to kodi log at debug level

    Args:
        txt (str): string to write to log
    """
    message = f'{ADDONID}: {txt}'
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def media_path(path: str) -> str:
    """fixes path to media based on kodi special protocol
    stacked media
    rar'ed media
    multipath media

    Args:
        path (str): a Kodi media path

    Returns:
        str: actual path to media
    """
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,", ",")
    except Exception:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        pathlist = [os.path.split(
            urllib.request.url2pathname(path.replace("rar://", "")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://", "").split('%2f/')
        pathlist = []
        for item in temp_path:
            pathlist.append(urllib.request.url2pathname(item))
    else:
        pathlist = [path]
    return pathlist[0]


def media_streamdetails(filename: str, streamdetails: dict) -> dict:
    """gets the streamdetails for an item from the filename or
    library streamdetails

    Args:
        filename (str): filename of item
        streamdetails (dict): dict of audio , video, subtitle streams of item

    Returns:
        dict of the streamdetails
    """
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    if '3d' in filename:
        info['videoresolution'] = '3d'
    elif video:
        # videowidth = video[0]['width']
        videoheight = video[0]['height']
        if (video[0]['width'] <= 720 and videoheight <= 480):
            info['videoresolution'] = "480"
        elif (video[0]['width'] <= 768 and videoheight <= 576):
            info['videoresolution'] = "576"
        elif (video[0]['width'] <= 960 and videoheight <= 544):
            info['videoresolution'] = "540"
        elif (video[0]['width'] <= 1280 and videoheight <= 720):
            info['videoresolution'] = "720"
        elif (video[0]['width'] >= 1281 or videoheight >= 721):
            info['videoresolution'] = "1080"
        else:
            info['videoresolution'] = ""
    elif ((('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename)
          or (filename.endswith('.vob' or '.ifo'))):
        info['videoresolution'] = '576'
    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd')
          in filename):
        info['videoresolution'] = '1080'
    else:
        info['videoresolution'] = '1080'
    if video:
        if 'hdrtpe' in video[0].keys():
            info['hdrtype'] = video[0]['hdrtype']
            # log('got hdrtype {}'.format(info['hdrtype']))
        else:
            info['hdrtype'] = 'SDR'
            # log('NO hdrtype {}'.format(info['hdrtype']))
        info['videocodec'] = video[0]['codec']
        if video[0]['aspect'] < 1.4859:
            info['videoaspect'] = "1.33"
        elif video[0]['aspect'] < 1.7190:
            info['videoaspect'] = "1.66"
        elif video[0]['aspect'] < 1.8147:
            info['videoaspect'] = "1.78"
        elif video[0]['aspect'] < 2.0174:
            info['videoaspect'] = "1.85"
        elif video[0]['aspect'] < 2.2738:
            info['videoaspect'] = "2.20"
        else:
            info['videoaspect'] = "2.35"
    else:
        info['videocodec'] = ''
        info['videoaspect'] = ''
        info['hdrtype'] = ''
    if audio:
        info['audiocodec'] = audio[0]['codec']
        info['audiochannels'] = audio[0]['channels']
    else:
        info['audiocodec'] = ''
        info['audiochannels'] = ''
    # log('media_streamdetails: {}'.format(info))
    return info
