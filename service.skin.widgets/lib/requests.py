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
#pylint: disable=line-too-long,unused-argument

"""Functions to get Kodi data via JSON-RPC

"""

import json as simplejson

import xbmc
from lib.common import LIMIT, MONITOR, addon

RANDOMITEMS_UNPLAYED = addon.getSetting("randomitems_unplayed") == 'true'
RECENTITEMS_UNPLAYED = addon.getSetting("recentitems_unplayed") == 'true'

class Req:
    """Instance methods for requesting JSON-RPC data from Kodi
    """
    def movies(self, request:str) -> dict:
        """Get movies based on request

        Args:
            request (str): Enum strings for valid requests

        Returns:
            dict: the JSON-RPC results
        """
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "votes"], "limits": {"end": %d},' %LIMIT
        if request == 'RecommendedMovie':
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}}}' %json_string)
        elif request == 'RecentMovie' and RECENTITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}, "filter": {"field": "playcount", "operator": "is", "value": "0"}}}' %json_string)
        elif request == 'RecentMovie':
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}' %json_string)
        elif request == "RandomMovie" and RANDOMITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" } }}' %json_string)
        json_query_dict: dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('movies' in json_query_dict['result']):
            return json_query_dict
        return {}

    def episodes(self, request:str) -> dict:
        """Get episodes based on request

        Args:
            request (str): Enum strings for valid requests

        Returns:
            dict: the JSON-RPC results
        """
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "streamdetails", "firstaired", "runtime"], "limits": {"end": %d},' %LIMIT
        if request == 'RecentEpisode' and RECENTITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        elif request == 'RecentEpisode':
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}' %json_string)
        elif request == 'RandomEpisode' and RANDOMITEMS_UNPLAYED:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }}}' %json_string)
        json_query_dict: dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('episodes' in json_query_dict['result']):
            return json_query_dict
        return {}

    def episodes_recommended(self, request:str) -> dict:
        """Gets unwatched episodes for tv show in progress

        Args:
            request (str): not used

        Returns:
            dict: the JSON-RPC results First unplayed episode of recent played tvshows
        """
        if not MONITOR.abortRequested():
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "studio", "mpaa", "file", "art"], "sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}, "limits": {"end": %d}}, "id": 1}' %LIMIT)
            json_query_dict: dict = simplejson.loads(json_query)
            if ('result' in json_query_dict) and ('tvshows' in json_query_dict['result']):
                return json_query_dict
        return {}

    def seasonthumb(self, tvshowid:int, seasonnumber:str) -> str:
        """Gets the season thumb path

        Args:
            tvshowid (int): the library id for the show
            seasonnumber (str): the two-digit season number 00-99

        Returns:
            str: Path to season thumbnail
        """
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "thumbnail"], "tvshowid":%s }, "id": 1}' % tvshowid)
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('seasons'):
            for item in json_query['result']['seasons']:
                season = f"{int(item['season']):02d}"
                if season == seasonnumber:
                    thumbnail:str = item['thumbnail']
                    return thumbnail
        return ''

    def musicvideos(self, request:str) -> dict:
        """Gets music videos based on request

        Args:
            request (str): Enum strings for valid requests

        Returns:
            dict: the JSON-RPC results
        """
        if not MONITOR.abortRequested():
            json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["title", "artist", "playcount", "year", "plot", "genre", "runtime", "fanart", "thumbnail", "file", "streamdetails", "resume"],  "limits": {"end": %d},' %LIMIT
            if request == 'RecommendedMusicVideo':
                json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "playcount" }}}'  %json_string)
            elif request == 'RecentMusicVideo':
                json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}'  %json_string)
            else:
                json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}' %json_string)
            json_query_dict: dict = simplejson.loads(json_query)
            if ('result' in json_query_dict) and ('musicvideos' in json_query_dict['result']):
                return json_query_dict
        return {}

    def albums(self, request:str) -> dict:
        """Gets albums based on request

        Args:
            request (str): Enum strings for valid requests

        Returns:
            dict: the JSON-RPC results
        """
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "theme", "mood", "style", "type", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount"], "limits": {"end": %d},' %LIMIT
        if request == 'RecommendedAlbum':
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "playcount" }}}' %json_string)
        elif request == 'RecentAlbum':
            json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded" }}}' %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}' %json_string)
        json_query_dict: dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('albums' in json_query_dict['result']):
            return json_query_dict
        return {}

    def artist(self, request:str) -> dict:
        """Gets random artists

        Args:
            request (str): not used

        Returns:
            dict: the JSON-RPC results
        """
        # Random artist
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["genre", "description", "mood", "style", "born", "died", "formed", "disbanded", "yearsactive", "instrument", "fanart", "thumbnail"], "sort": {"method": "random"}, "limits": {"end": %d}}, "id": 1}'  %LIMIT)
        json_query_dict: dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('artists' in json_query_dict['result']):
            return json_query_dict
        return {}

    def songs(self, request:str) -> dict:
        """Gets albums based on request

        Args:
            request (str): Enum strings for valid requests

        Returns:
            dict: the JSON-RPC results
        """
        json_string = '{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "playcount", "genre", "artist", "album", "year", "file", "thumbnail", "fanart", "rating"], "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}, "limits": {"end": %d},' %LIMIT
        if request == 'RandomSong' and RANDOMITEMS_UNPLAYED == "True":
            json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}'  %json_string)
        else:
            json_query = xbmc.executeJSONRPC('%s  "sort": {"method": "random"}}}'  %json_string)
        json_query_dict:dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('songs' in json_query_dict['result']):
            return json_query_dict
        return {}

    def addons(self, request:str) -> dict:
        """Gets addons

        Args:
            request (str): Not used

        Returns:
            dict: the JSON-RPC results
        """
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"properties": ["name", "author", "summary", "version", "fanart", "thumbnail"]}, "id": 1}')
        json_query_dict:dict = simplejson.loads(json_query)
        if ('result' in json_query_dict) and ('addons' in json_query_dict['result']):
            return json_query_dict
        return {}
