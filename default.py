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
# pylint: disable=line-too-long,invalid-name

import datetime
import json as simplejson
import os
import random
import sys
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__    = __addon__.getLocalizedString

def log(txt: str) -> None:
    """writes to kodi log at debug level

    Args:
        txt (str): string to write to log
    """
    message = f'{__addonname__}: {txt}'
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    """
    Provides all processing
    """
    def __init__(self):
        """If called as a runscript starts a
        Kodi player to play selected mediaid.  If running as a service initalizes
        globals and starts the _daemon
        """
        self._parse_argv()
        # check how we were executed via globals
        if self.MOVIEID:
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Player.Open", '
                '"params": { "item": { "movieid": %d }, '
                '"options":{ "resume": %s } }, "id": 1 }'
                % (int(self.MOVIEID), self.RESUME))
        elif self.EPISODEID:
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Player.Open", '
                '"params": { "item": { "episodeid": %d }, '
                '"options":{ "resume": %s }  }, "id": 1 }'
                % (int(self.EPISODEID), self.RESUME))
        elif self.MUSICVIDEOID:
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Player.Open", '
                '"params": { "item": { "musicvideoid": %d } }, "id": 1 }'
                % int(self.MUSICVIDEOID))
        elif self.ALBUMID:
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Player.Open", '
                '"params": { "item": { "albumid": %d } }, "id": 1 }'
                % int(self.ALBUMID))
        elif self.SONGID:
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Player.Open", '
                '"params": { "item": { "songid": %d } }, "id": 1 }'
                % int(self.SONGID))
        else: # run as service
            self._init_vars()
            self._init_property()
            # clear our property, if another instance is already running
            # it should stop now
            self.WINDOW.clearProperty('SkinWidgets_Running')
            a_total = datetime.datetime.now()
            self._fetch_info_randomitems()
            self._fetch_info_recommended()
            self._fetch_info_recentitems()
            b_total = datetime.datetime.now()
            c_total = b_total - a_total
            log(f'Total time needed for all queries: {c_total}')
            # give a possible other instance some time to notice
            # the empty property
            self.WINDOW.setProperty('SkinWidgets_Running', 'true')
            self._daemon()

    def _init_vars(self):
        """Creates a home window, player, and monitor object
        """
        self.WINDOW = xbmcgui.Window(10000)
        self.Player = Widgets_Player(action = self._update)
        self.Monitor = Widgets_Monitor(update_listitems = self._update,
                                       update_settings = self._on_change)
        self.LIMIT = 20
        self.RANDOMITEMS_UNPLAYED = False
        self.RECENTITEMS_UNPLAYED = False

    def _on_change(self):
        """Widget_Monitor runs when addon settings change to update widgets
        by clearing appropriate home window properties and refetching
        library info
        """
        log('_on_change called gettings add infos and properties')
        clearlist_groups = ['Recommended','Random','Recent']
        clearlist_types = ['Movie','Episode','MusicVideo','Album',
                           'Artist','Song','Addon']
        for item_group in clearlist_groups:
            for item_type in clearlist_types:
                clear = item_group + item_type
                self._clear_properties(clear)
        self._init_property()
        self._fetch_info_randomitems()
        self._fetch_info_recommended()
        self._fetch_info_recentitems()
        log('_on_change completed')

    def _init_property(self):
        """Initializes home window properties and some globals
        from addon settings
        """
        self.WINDOW.setProperty(
            'SkinWidgets_Recommended',
            f'{__addon__.getSetting("recommended_enable")}'
            )
        self.WINDOW.setProperty(
            'SkinWidgets_RandomItems',
            f'{__addon__.getSetting("randomitems_enable")}'
            )
        self.WINDOW.setProperty(
            'SkinWidgets_RecentItems',
            f'{__addon__.getSetting("recentitems_enable")}'
            )
        self.WINDOW.setProperty('SkinWidgets_RandomItems_Update', 'false')
        self.RANDOMITEMS_UPDATE_METHOD = (
            __addon__.getSetting("randomitems_method"))
        self.RECENTITEMS_HOME_UPDATE = (
            __addon__.getSetting("recentitems_homeupdate"))
        self.PLOT_ENABLE = __addon__.getSetting("plot_enable")  == 'true'
        # convert time to seconds, times 2 for 0,5 second sleep compensation
        self.RANDOMITEMS_TIME = __addon__.getSetting("randomitems_time") * 120

    def _parse_argv(self):
        """gets any arguments passed from Kodi and sets globals
        """
        try:
            params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
        except:
            params = {}
        self.MOVIEID = params.get("movieid", "")
        self.EPISODEID = params.get("episodeid", "")
        self.MUSICVIDEOID = params.get("musicvideoid", "")
        self.ALBUMID = params.get("albumid", "")
        self.SONGID = params.get("songid", "")
        self.RESUME = "true"
        for arg in sys.argv:
            param = str(arg)
            if 'resume=' in param:
                if param.replace('resume=', '') == "false":
                    self.RESUME = "false"

    def _fetch_info_recommended(self):
        """gets info for 'in progress' widgets by media type
        """
        a = datetime.datetime.now()
        if __addon__.getSetting('recommended_enable') == 'true':
            self._fetch_movies('RecommendedMovie')
            self._fetch_tvshows_recommended('RecommendedEpisode')
            self._fetch_albums('RecommendedAlbum')
            self._fetch_musicvideo('RecommendedMusicVideo')
            b = datetime.datetime.now()
            c = b - a
            log(f'Total time needed to request recommended queries: {c}')

    def _fetch_info_randomitems(self):
        """gets info for random widgets by media type
        """
        a = datetime.datetime.now()
        if __addon__.getSetting("randomitems_enable") == 'true':
            self.RANDOMITEMS_UNPLAYED = (
                __addon__.getSetting("randomitems_unplayed") == 'true')
            self._fetch_movies('RandomMovie')
            self._fetch_tvshows('RandomEpisode')
            self._fetch_musicvideo('RandomMusicVideo')
            self._fetch_albums('RandomAlbum')
            self._fetch_artist('RandomArtist')
            self._fetch_song('RandomSong')
            self._fetch_addon('RandomAddon')
            b = datetime.datetime.now()
            c = b - a
            log(f'Total time needed to request random queries: {c}')

    def _fetch_info_recentitems(self):
        """gets info for last added items by media type note tv shows get
        episodes
        """
        a = datetime.datetime.now()
        if __addon__.getSetting("recentitems_enable") == 'true':
            self.RECENTITEMS_UNPLAYED = (
                __addon__.getSetting("recentitems_unplayed") == 'true')
            self._fetch_movies('RecentMovie')
            self._fetch_tvshows('RecentEpisode')
            self._fetch_musicvideo('RecentMusicVideo')
            self._fetch_albums('RecentAlbum')
            b = datetime.datetime.now()
            c = b - a
            log(f'Total time needed to request recent items queries: {c}')

    def _fetch_movies(self, request: str):
        """gets info via json rpc VideoLibrary.GetMovies for movies based on
        request type

        Args:
            request (str): in progress/random/last added
        """
        if not self.Monitor.abortRequested():
            json_string = ('{"jsonrpc": "2.0",  "id": 1, '
                '"method": "VideoLibrary.GetMovies", '
                '"params": {"properties": ['
                                           '"title", '
                                           '"originaltitle", '
                                           '"playcount", '
                                           '"year", '
                                           '"genre", '
                                           '"studio", '
                                           '"country", '
                                           '"tagline", '
                                           '"plot", '
                                           '"runtime", '
                                           '"file", '
                                           '"plotoutline", '
                                           '"lastplayed", '
                                           '"trailer", '
                                           '"rating", '
                                           '"ratings", '
                                           '"userrating", '
                                           '"resume", '
                                           '"art", '
                                           '"streamdetails", '
                                           '"mpaa", '
                                           '"director"'
                                           '], '
                    '"limits": {"end": %d},'
                %self.LIMIT)
            if request == 'RecommendedMovie':
                json_query = xbmc.executeJSONRPC(
                    '%s "sort": {"order": "descending", "method": "lastplayed"},'
                    '"filter": {"field": "inprogress", "operator": "true", '
                    '"value": ""}}}' %json_string)
            elif request == 'RecentMovie' and self.RECENTITEMS_UNPLAYED:
                json_query = xbmc.executeJSONRPC(
                    '%s "sort": {"order": "descending", "method": "dateadded"}, '
                    '"filter": {"field": "playcount", "operator": "is", '
                    '"value": "0"}}}' %json_string)
            elif request == 'RecentMovie':
                json_query = xbmc.executeJSONRPC(
                    '%s "sort": {"order": "descending", "method": "dateadded"}}}'
                    %json_string)
            elif request == "RandomMovie" and self.RANDOMITEMS_UNPLAYED:
                json_query = xbmc.executeJSONRPC(
                    '%s "sort": {"method": "random" }, "filter": '
                    '{"field": "playcount", "operator": "lessthan", '
                    '"value": "1"}}}' %json_string)
            else:
                json_query = xbmc.executeJSONRPC(
                    '%s "sort": {"method": "random" } }}' %json_string)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'movies' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['movies']:
                    count += 1
                    #if count <= 2:
                        #log('get movie json response: {}'.format(item))  #debug
                    if (item['resume']['position']
                        and item['resume']['total']) > 0:
                        resume = "true"
                        played = '%s%%'%int((float(item['resume']['position'])
                                            / float(item['resume']['total'])) * 100)
                        played_asint = '%s'%int((float(item['resume']['position'])
                                                / float(item['resume']['total'])) * 100)
                    else:
                        resume = "false"
                        played = '0%'
                        played_asint = '0'
                    if item['playcount'] >= 1:
                        watched = "true"
                    else:
                        watched = "false"
                    if not self.PLOT_ENABLE and watched == "false":
                        plot = __localize__(32014)
                    else:
                        plot = item['plot']
                    art = item['art']
                    path = media_path(item['file'])
                    play = ('RunScript(' + __addonid__ + ',movieid='
                            + str(item.get('movieid')) + ')')
                    streaminfo = media_streamdetails(item['file'].lower(),
                                                    item['streamdetails'])
                    if len(item['studio']) > 0:
                        studio = item['studio'][0]
                    else:
                        studio = ""
                    if len(item['country']) > 0:
                        country = item['country'][0]
                    else:
                        country = ""
                    self.WINDOW.setProperty("%s.%d.DBID"            % (request, count), str(item.get('movieid')))
                    self.WINDOW.setProperty("%s.%d.Title"           % (request, count), item['title'])
                    self.WINDOW.setProperty("%s.%d.OriginalTitle"   % (request, count), item['originaltitle'])
                    self.WINDOW.setProperty("%s.%d.Year"            % (request, count), str(item['year']))
                    self.WINDOW.setProperty("%s.%d.Genre"           % (request, count), " / ".join(item['genre']))
                    self.WINDOW.setProperty("%s.%d.Studio"          % (request, count), studio)
                    self.WINDOW.setProperty("%s.%d.Country"         % (request, count), country)
                    self.WINDOW.setProperty("%s.%d.Plot"            % (request, count), plot)
                    self.WINDOW.setProperty("%s.%d.PlotOutline"     % (request, count), item['plotoutline'])
                    self.WINDOW.setProperty("%s.%d.Tagline"         % (request, count), item['tagline'])
                    self.WINDOW.setProperty("%s.%d.Runtime"         % (request, count), str(int((item['runtime'] / 60) + 0.5)))
                    self.WINDOW.setProperty("%s.%d.Rating"          % (request, count), str(round(float(item['rating']),1)))
                    self.WINDOW.setProperty("%s.%d.Userrating"      % (request, count), str(item['userrating']))
                    self.WINDOW.setProperty("%s.%d.mpaa"            % (request, count), item['mpaa'])
                    self.WINDOW.setProperty("%s.%d.Director"        % (request, count), " / ".join(item['director']))
                    self.WINDOW.setProperty("%s.%d.Trailer"         % (request, count), item['trailer'])
                    self.WINDOW.setProperty("%s.%d.Art(poster)"     % (request, count), art.get('poster',''))
                    self.WINDOW.setProperty("%s.%d.Art(fanart)"     % (request, count), art.get('fanart',''))
                    self.WINDOW.setProperty("%s.%d.Art(clearlogo)"  % (request, count), art.get('clearlogo',''))
                    self.WINDOW.setProperty("%s.%d.Art(clearart)"   % (request, count), art.get('clearart',''))
                    self.WINDOW.setProperty("%s.%d.Art(landscape)"  % (request, count), art.get('landscape',''))
                    self.WINDOW.setProperty("%s.%d.Art(banner)"     % (request, count), art.get('banner',''))
                    self.WINDOW.setProperty("%s.%d.Art(discart)"    % (request, count), art.get('discart',''))
                    self.WINDOW.setProperty("%s.%d.Art(icon)"       % (request, count), art.get('icon',''))
                    self.WINDOW.setProperty("%s.%d.Resume"          % (request, count), resume)
                    self.WINDOW.setProperty("%s.%d.PercentPlayed"   % (request, count), played)
                    self.WINDOW.setProperty("%s.%d.PercentPlayedAsInt"   % (request, count), played_asint)
                    self.WINDOW.setProperty("%s.%d.Watched"         % (request, count), watched)
                    self.WINDOW.setProperty("%s.%d.File"            % (request, count), item['file'])
                    self.WINDOW.setProperty("%s.%d.Path"            % (request, count), path)
                    self.WINDOW.setProperty("%s.%d.Play"            % (request, count), play)
                    self.WINDOW.setProperty("%s.%d.VideoCodec"      % (request, count), streaminfo['videocodec'])
                    self.WINDOW.setProperty("%s.%d.VideoResolution" % (request, count), streaminfo['videoresolution'])
                    self.WINDOW.setProperty("%s.%d.VideoAspect"     % (request, count), streaminfo['videoaspect'])
                    self.WINDOW.setProperty("%s.%d.HDRType"         % (request, count), streaminfo['hdrtype'])
                    self.WINDOW.setProperty("%s.%d.AudioCodec"      % (request, count), streaminfo['audiocodec'])
                    self.WINDOW.setProperty("%s.%d.AudioChannels"   % (request, count), str(streaminfo['audiochannels']))
                    for k,v in art.items():
                        self.WINDOW.setProperty("%s.%d.Art(%s)"     % (request, count, k), str(v))

            del json_query

    def _fetch_tvshows_recommended(self, request: str):
        """Gets unplayed episodes of tv shows via json rpc
        VideoLibrary.GetTVShows based on request

        Args:
            request (str): in progress/random/last added
        """
        if not self.Monitor.abortRequested():
            # First unplayed episode of recent played tvshows
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", '
                '"method": "VideoLibrary.GetTVShows", '
                '"params": {"properties": ["title", '
                                           '"studio", '
                                           '"mpaa", '
                                           '"file", '
                                           '"art"'
                                           '], '
                            '"sort": {"order": "descending", '
                                      '"method": "lastplayed"}, '
                            '"filter": {"field": "inprogress", '
                                        '"operator": "true", "value": ""}, '
                '"limits": {"end": %d}}, "id": 1}' %self.LIMIT)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'tvshows' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['tvshows']:
                    if self.Monitor.abortRequested():
                        return
                    count += 1
                    json_query2 = xbmc.executeJSONRPC(
                        '{"jsonrpc": "2.0", '
                        '"method": "VideoLibrary.GetEpisodes", '
                        '"params": {"tvshowid": %d, "properties": ["title", '
                                                                   '"playcount", '
                                                                   '"plot", '
                                                                   '"season", '
                                                                   '"episode", '
                                                                   '"showtitle", '
                                                                   '"file", '
                                                                   '"lastplayed", '
                                                                   '"rating", '
                                                                   '"userrating", '
                                                                   '"resume", '
                                                                   '"art", '
                                                                   '"streamdetails", '
                                                                   '"firstaired", '
                                                                   '"runtime"'
                                                                   '], '
                                                    '"sort": {"method": "episode"}, '
                                                    '"filter": {"field": '
                                                                '"playcount", '
                                                                '"operator": "is", '
                                                                '"value": "0"}, '
                                                    '"limits": {"end": 1}}, '
                        '"id": 1}' %item['tvshowid'])
                    json_query2 = simplejson.loads(json_query2)
                    if ('result' in json_query2
                        and json_query2['result'] is not None
                        and 'episodes' in json_query2['result']):
                        for item2 in json_query2['result']['episodes']:
                            episode = "%.2d" % float(item2['episode'])
                            season = "%.2d" % float(item2['season'])
                            rating = str(round(float(item2['rating']),1))
                            episodeno = "s%se%s" %(season,episode)
                            art2 = item2['art']
                            #if float(item2['episode']) <= 2:
                                #log('TVshow episode item2: {}'.format(item2))  #debug
                            #seasonthumb = ''
                            if (item2['resume']['position']
                                and item2['resume']['total']) > 0:
                                resume = "true"
                                played = '%s%%'%int((float(item2['resume']['position'])
                                    / float(item2['resume']['total'])) * 100)
                                played_asint = '%s'%int((float(item2['resume']['position'])
                                    / float(item2['resume']['total'])) * 100)
                            else:
                                resume = "false"
                                played = '0%'
                                played_asint = '0%'
                            if item2['playcount'] >= 1:
                                watched = "true"
                            else:
                                watched = "false"
                            if not self.PLOT_ENABLE and watched == "false":
                                plot = __localize__(32014)
                            else:
                                plot = item2['plot']
                            art = item['art']
                            path = media_path(item['file'])
                            play = ('RunScript(' + __addonid__ + ',episodeid='
                            + str(item2.get('episodeid')) + ')')
                            streaminfo = media_streamdetails(item['file'].lower(),
                                                            item2['streamdetails'])
                            if len(item['studio']) > 0:
                                studio = item['studio'][0]
                            else:
                                studio = ""
                            self.WINDOW.setProperty("%s.%d.DBID"                % (request, count), str(item2.get('episodeid')))
                            self.WINDOW.setProperty("%s.%d.Title"               % (request, count), item2['title'])
                            self.WINDOW.setProperty("%s.%d.Episode"             % (request, count), episode)
                            self.WINDOW.setProperty("%s.%d.EpisodeNo"           % (request, count), episodeno)
                            self.WINDOW.setProperty("%s.%d.Season"              % (request, count), season)
                            self.WINDOW.setProperty("%s.%d.Plot"                % (request, count), plot)
                            self.WINDOW.setProperty("%s.%d.TVshowTitle"         % (request, count), item2['showtitle'])
                            self.WINDOW.setProperty("%s.%d.Rating"              % (request, count), rating)
                            self.WINDOW.setProperty("%s.%d.Runtime"             % (request, count), str(int((item2['runtime'] / 60) + 0.5)))
                            self.WINDOW.setProperty("%s.%d.Premiered"           % (request, count), item2['firstaired'])
                            self.WINDOW.setProperty("%s.%d.Art(thumb)"          % (request, count), art2.get('thumb',''))
                            self.WINDOW.setProperty("%s.%d.Art(icon)"           % (request, count), art2.get('icon',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.fanart)"  % (request, count), art2.get('tvshow.fanart',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.poster)"  % (request, count), art2.get('tvshow.poster',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.banner)"  % (request, count), art2.get('tvshow.banner',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.clearlogo)"% (request, count), art2.get('tvshow.clearlogo',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.clearart)" % (request, count), art2.get('tvshow.clearart',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.landscape)"% (request, count), art2.get('tvshow.landscape',''))
                            self.WINDOW.setProperty("%s.%d.Art(tvshow.characterart)"% (request, count), art2.get('tvshow.characterart',''))
                            #self.WINDOW.setProperty("%s.%d.Art(season.poster)" % (request, count), seasonthumb)
                            self.WINDOW.setProperty("%s.%d.Studio"              % (request, count), studio)
                            self.WINDOW.setProperty("%s.%d.mpaa"                % (request, count), item['mpaa'])
                            self.WINDOW.setProperty("%s.%d.Resume"              % (request, count), resume)
                            self.WINDOW.setProperty("%s.%d.PercentPlayed"       % (request, count), played)
                            self.WINDOW.setProperty("%s.%d.PercentPlayedAsInt"  % (request, count), played_asint)
                            self.WINDOW.setProperty("%s.%d.Watched"             % (request, count), watched)
                            self.WINDOW.setProperty("%s.%d.File"                % (request, count), item2['file'])
                            self.WINDOW.setProperty("%s.%d.Path"                % (request, count), path)
                            self.WINDOW.setProperty("%s.%d.Play"                % (request, count), play)
                            self.WINDOW.setProperty("%s.%d.VideoCodec"          % (request, count), streaminfo['videocodec'])
                            self.WINDOW.setProperty("%s.%d.VideoResolution"     % (request, count), streaminfo['videoresolution'])
                            self.WINDOW.setProperty("%s.%d.VideoAspect"         % (request, count), streaminfo['videoaspect'])
                            self.WINDOW.setProperty("%s.%d.AudioCodec"          % (request, count), streaminfo['audiocodec'])
                            self.WINDOW.setProperty("%s.%d.AudioChannels"       % (request, count), str(streaminfo['audiochannels']))
                    del json_query2
            del json_query

    def _fetch_tvshows(self, request):
        if not self.Monitor.abortRequested():
            season_folders = __addon__.getSetting("randomitems_seasonfolders")
            json_string = ('{"jsonrpc": "2.0", "id": 1, '
                            '"method": "VideoLibrary.GetEpisodes", '
                            '"params": { "properties": '
                                        '["title", '
                                        '"playcount", '
                                        '"season", '
                                        '"episode", '
                                        '"showtitle", '
                                        '"plot", '
                                        '"file", '
                                        '"rating", '
                                        '"userrating", '
                                        '"resume", '
                                        '"tvshowid", '
                                        '"art", '
                                        '"streamdetails", '
                                        '"firstaired", '
                                        '"runtime"], '
                            '"limits": {"end": %d},' %self.LIMIT)
            if request == 'RecentEpisode' and self.RECENTITEMS_UNPLAYED:
                json_query = (xbmc.executeJSONRPC('%s "sort": {"order": "descending", '
                                                                '"method": "dateadded"}, '
                                                        '"filter": {"field": "playcount", '
                                                                    '"operator": "lessthan", '
                                                                    '"value": "1"}}}'
                                                    %json_string))
            elif request == 'RecentEpisode':
                json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}' %json_string)
            elif request == 'RandomEpisode' and self.RANDOMITEMS_UNPLAYED:
                json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}}}' %json_string)
            else:
                json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random" }}}' %json_string)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'episodes' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['episodes']:
                    count += 1
                    #if count <= 2:
                    #   log('tvshow episeode json resuolt: {}'.format(item))  #debug
                    '''
                    # This part is commented out because it takes 1.5second extra on my system 
                    # to request these which doubles the total time.
                    # Hence the ugly path hack that will require users to have season folders.
                    json_query2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"properties": ["file", "studio"], "tvshowid":%s}, "id": 1}' %item['tvshowid'])
                    json_query2 = simplejson.loads(json_query2)
                    path = json_query2['result']['tvshowdetails']['file']
                    studio = json_query2['result']['tvshowdetails']['studio'][0]
                    '''
                    if season_folders == 'true':
                        path = os.path.split(media_path(item['file']))[0]
                    else:
                        path = media_path(item['file'])
                    episode = "%.2d" % float(item['episode'])
                    season = "%.2d" % float(item['season'])
                    episodeno = "s%se%s" %(season,episode)
                    #seasonthumb = ''
                    rating = str(round(float(item['rating']),1))
                    if (item['resume']['position'] and item['resume']['total']) > 0:
                        resume = "true"
                        played = '%s%%'%int((float(item['resume']['position'])
                        / float(item['resume']['total'])) * 100)
                        played_asint = '%s'%int((float(item['resume']['position'])
                        / float(item['resume']['total'])) * 100)
                    else:
                        resume = "false"
                        played = '0%'
                        played_asint = '0'
                    if item['playcount'] >= 1:
                        watched = "true"
                    else:
                        watched = "false"
                    if not self.PLOT_ENABLE and watched == "false":
                        plot = __localize__(32014)
                    else:
                        plot = item['plot']
                    art = item['art']
                    path = media_path(item['file'])
                    play = 'RunScript(' + __addonid__ + ',episodeid=' + str(item.get('episodeid')) + ')'
                    streaminfo = media_streamdetails(item['file'].lower(),
                                                     item['streamdetails'])
                    self.WINDOW.setProperty("%s.%d.DBID"                % (request, count), str(item.get('episodeid')))
                    self.WINDOW.setProperty("%s.%d.Title"               % (request, count), item['title'])
                    self.WINDOW.setProperty("%s.%d.Episode"             % (request, count), episode)
                    self.WINDOW.setProperty("%s.%d.EpisodeNo"           % (request, count), episodeno)
                    self.WINDOW.setProperty("%s.%d.Season"              % (request, count), season)
                    self.WINDOW.setProperty("%s.%d.Plot"                % (request, count), plot)
                    self.WINDOW.setProperty("%s.%d.TVshowTitle"         % (request, count), item['showtitle'])
                    self.WINDOW.setProperty("%s.%d.Rating"              % (request, count), rating)
                    self.WINDOW.setProperty("%s.%d.Runtime"             % (request, count), str(int((item['runtime'] / 60) + 0.5)))
                    self.WINDOW.setProperty("%s.%d.Premiered"           % (request, count), item['firstaired'])
                    self.WINDOW.setProperty("%s.%d.Art(thumb)"          % (request, count), art.get('thumb',''))
                    self.WINDOW.setProperty("%s.%d.Art(icon)"           % (request, count), art.get('icon',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.fanart)"  % (request, count), art.get('tvshow.fanart',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.poster)"  % (request, count), art.get('tvshow.poster',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.banner)"  % (request, count), art.get('tvshow.banner',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.clearlogo)"% (request, count), art.get('tvshow.clearlogo',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.clearart)" % (request, count), art.get('tvshow.clearart',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.landscape)"% (request, count), art.get('tvshow.landscape',''))
                    self.WINDOW.setProperty("%s.%d.Art(tvshow.characterart)"% (request, count), art.get('tvshow.characterart',''))
                    self.WINDOW.setProperty("%s.%d.Resume"              % (request, count), resume)
                    self.WINDOW.setProperty("%s.%d.PercentPlayed"       % (request, count), played)
                    self.WINDOW.setProperty("%s.%d.PercentPlayedAsInt"  % (request, count), played_asint)
                    self.WINDOW.setProperty("%s.%d.Watched"             % (request, count), watched)
                    self.WINDOW.setProperty("%s.%d.File"                % (request, count), item['file'])
                    self.WINDOW.setProperty("%s.%d.Path"                % (request, count), path)
                    self.WINDOW.setProperty("%s.%d.Play"                % (request, count), play)
                    self.WINDOW.setProperty("%s.%d.VideoCodec"          % (request, count), streaminfo['videocodec'])
                    self.WINDOW.setProperty("%s.%d.VideoResolution"     % (request, count), streaminfo['videoresolution'])
                    self.WINDOW.setProperty("%s.%d.VideoAspect"         % (request, count), streaminfo['videoaspect'])
                    self.WINDOW.setProperty("%s.%d.AudioCodec"          % (request, count), streaminfo['audiocodec'])
                    self.WINDOW.setProperty("%s.%d.AudioChannels"       % (request, count), str(streaminfo['audiochannels']))
            del json_query

    def _fetch_seasonthumb(self, tvshowid, seasonnumber):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", '
                                        '"method": "VideoLibrary.GetSeasons", '
                                        '"params": {"properties": ["season", "thumbnail"], '
                                        '"tvshowid":%s }, "id": 1}' % tvshowid)
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'seasons' in json_query['result']:
            for item in json_query['result']['seasons']:
                season = "%.2d" % float(item['season'])
                if season == seasonnumber:
                    thumbnail = item['thumbnail']
                    return thumbnail

    def _fetch_musicvideo(self, request):
        if not self.Monitor.abortRequested():
            json_string = ('{"jsonrpc": "2.0",  "id": 1, '
                            '"method": "VideoLibrary.GetMusicVideos", '
                            '"params": {"properties": '
                                '["title", '
                                '"artist", '
                                '"playcount", '
                                '"year", '
                                '"plot", '
                                '"genre", '
                                '"runtime", '
                                '"userrating", '
                                '"art", '
                                '"file", '
                                '"streamdetails", '
                                '"resume"],  '
                            '"limits": {"end": %d},' %self.LIMIT)
            if request == 'RecommendedMusicVideo':
                json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "playcount" }}}'  %json_string)
            elif request == 'RecentMusicVideo':
                json_query = xbmc.executeJSONRPC('%s "sort": {"order": "descending", "method": "dateadded"}}}'  %json_string)
            else:
                json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}' %json_string)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'musicvideos' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['musicvideos']:
                    count += 1
                    #if count <= 2:
                        #log('music vidoe jsopn respone: {}'.format(item))  # debug
                    if (item['resume']['position'] and item['resume']['total'])> 0:
                        resume = "true"
                        played = '%s%%'%int((float(item['resume']['position'])
                        / float(item['resume']['total'])) * 100)
                        played_asint = '%s'%int((item['resume']['position']
                        / item['resume']['total']) * 100)
                    else:
                        resume = "false"
                        played = '0%'
                        played_asint = '0'
                    if item['playcount'] >= 1:
                        watched = "true"
                    else:
                        watched = "false"
                    art = item['art']
                    play = 'RunScript(' + __addonid__ + ',musicvideoid=' + str(item.get('musicvideoid')) + ')'
                    path = media_path(item['file'])
                    streaminfo = media_streamdetails(item['file'].lower(),
                                                     item['streamdetails'])
                    runtimesecs = str(item['runtime'] // 60) + ':' + '{:02d}'.format(item['runtime'] % 60)
                    self.WINDOW.setProperty("%s.%d.DBID"           % (request, count), str(item.get('musicvideoid')))
                    self.WINDOW.setProperty("%s.%d.Title"           % (request, count), item['title'])
                    self.WINDOW.setProperty("%s.%d.Artist"          % (request, count), " / ".join(item['artist']))
                    self.WINDOW.setProperty("%s.%d.Year"            % (request, count), str(item['year']))
                    self.WINDOW.setProperty("%s.%d.Plot"            % (request, count), item['plot'])
                    self.WINDOW.setProperty("%s.%d.Genre"           % (request, count), " / ".join(item['genre']))
                    self.WINDOW.setProperty("%s.%d.Userrating"      % (request, count), str(item['userrating']))
                    self.WINDOW.setProperty("%s.%d.Runtime"         % (request, count), str(int((item['runtime'] / 60) + 0.5)))
                    self.WINDOW.setProperty("%s.%d.Runtimesecs"     % (request, count), runtimesecs)
                    self.WINDOW.setProperty("%s.%d.Thumb"           % (request, count), art.get('thumb','')) #remove
                    self.WINDOW.setProperty("%s.%d.Fanart"          % (request, count), art.get('fanart','')) #remove
                    self.WINDOW.setProperty("%s.%d.Art(thumb)"      % (request, count), art.get('thumb',''))
                    self.WINDOW.setProperty("%s.%d.Art(fanart)"     % (request, count), art.get('fanart',''))
                    self.WINDOW.setProperty("%s.%d.Art(clearlogo)"  % (request, count), art.get('clearlogo',''))
                    self.WINDOW.setProperty("%s.%d.Art(clearart)"   % (request, count), art.get('clearart',''))
                    self.WINDOW.setProperty("%s.%d.Art(landscape)"  % (request, count), art.get('landscape',''))
                    self.WINDOW.setProperty("%s.%d.Art(banner)"     % (request, count), art.get('banner',''))
                    self.WINDOW.setProperty("%s.%d.Art(cover)"      % (request, count), art.get('cover',''))
                    self.WINDOW.setProperty("%s.%d.Art(icon)"       % (request, count), art.get('icon',''))
                    self.WINDOW.setProperty("%s.%d.File"            % (request, count), item['file'])
                    self.WINDOW.setProperty("%s.%d.Path"            % (request, count), path)
                    self.WINDOW.setProperty("%s.%d.Resume"          % (request, count), resume)
                    self.WINDOW.setProperty("%s.%d.PercentPlayed"   % (request, count), played)
                    self.WINDOW.setProperty("%s.%d.PercentPlayedAsInt" % (request, count), played_asint)
                    self.WINDOW.setProperty("%s.%d.Watched"         % (request, count), watched)
                    self.WINDOW.setProperty("%s.%d.Play"            % (request, count), play)
                    self.WINDOW.setProperty("%s.%d.VideoCodec"      % (request, count), streaminfo['videocodec'])
                    self.WINDOW.setProperty("%s.%d.VideoResolution" % (request, count), streaminfo['videoresolution'])
                    self.WINDOW.setProperty("%s.%d.VideoAspect"     % (request, count), streaminfo['videoaspect'])
                    self.WINDOW.setProperty("%s.%d.AudioCodec"      % (request, count), streaminfo['audiocodec'])
                    self.WINDOW.setProperty("%s.%d.AudioChannels"   % (request, count), str(streaminfo['audiochannels']))
            del json_query

    def _fetch_albums(self, request):
        if not self.Monitor.abortRequested():
            json_string = ('{"jsonrpc": "2.0", "id": 1, '
                            '"method": "AudioLibrary.GetAlbums", '
                            '"params": {"properties": '
                                '["title", '
                                '"description", '
                                '"albumlabel", '
                                '"theme", '
                                '"mood", '
                                '"style", '
                                '"type", '
                                '"artist", '
                                '"genre", '
                                '"year", '
                                '"thumbnail", '
                                '"fanart", '
                                '"art", '
                                '"rating", '
                                '"userrating", '
                                '"playcount"], '
                            '"limits": {"end": %d},' %self.LIMIT)
            if request == 'RecommendedAlbum':
                json_query = xbmc.executeJSONRPC('%s "sort": '
                                                        '{"order": "descending", '
                                                        '"method": "playcount" }}}'
                                                %json_string)
            elif request == 'RecentAlbum':
                json_query = xbmc.executeJSONRPC('%s "sort": '
                                                        '{"order": "descending", '
                                                        '"method": "dateadded" }}}'
                                                %json_string)
            else:
                json_query = xbmc.executeJSONRPC('%s "sort": '
                                                        '{"method": "random"}}}'
                                                %json_string)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'albums' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['albums']:
                    count += 1
                    #if count <= 2:
                        #log('music album json respone: {}'.format(item))  # debug
                    rating = str(item['rating'])
                    if rating == '48':
                        rating = ''
                    play = 'RunScript(' + __addonid__ + ',albumid=' + str(item.get('albumid')) + ')'
                    self.WINDOW.setProperty("%s.%d.Title"       % (request, count), item['title'])
                    self.WINDOW.setProperty("%s.%d.Label"       % (request, count), item['title']) #needs to be removed
                    self.WINDOW.setProperty("%s.%d.Artist"      % (request, count), " / ".join(item['artist']))
                    self.WINDOW.setProperty("%s.%d.Genre"       % (request, count), " / ".join(item['genre']))
                    self.WINDOW.setProperty("%s.%d.Theme"       % (request, count), " / ".join(item['theme']))
                    self.WINDOW.setProperty("%s.%d.Mood"        % (request, count), " / ".join(item['mood']))
                    self.WINDOW.setProperty("%s.%d.Style"       % (request, count), " / ".join(item['style']))
                    self.WINDOW.setProperty("%s.%d.Type"        % (request, count), " / ".join(item['type']))
                    self.WINDOW.setProperty("%s.%d.Year"        % (request, count), str(item['year']))
                    self.WINDOW.setProperty("%s.%d.RecordLabel" % (request, count), item['albumlabel'])
                    self.WINDOW.setProperty("%s.%d.Description" % (request, count), item['description'])
                    self.WINDOW.setProperty("%s.%d.Rating"      % (request, count), rating)
                    self.WINDOW.setProperty("%s.%d.Userrating"  % (request, count), str(item['userrating']))
                    self.WINDOW.setProperty("%s.%d.Thumb"       % (request, count), item['thumbnail']) #remove
                    self.WINDOW.setProperty("%s.%d.Fanart"      % (request, count), item['fanart']) #remove
                    self.WINDOW.setProperty("%s.%d.Art(thumb)"  % (request, count), item['thumbnail'])
                    self.WINDOW.setProperty("%s.%d.Art(fanart)" % (request, count), item['fanart'])
                    self.WINDOW.setProperty("%s.%d.Play"        % (request, count), play)
            del json_query

    def _fetch_artist(self, request):
        if not self.Monitor.abortRequested():
            # Random artist
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", '
                                            '"method": "AudioLibrary.GetArtists", '
                                            '"params": {"properties": '
                                                '["genre", '
                                                '"description", '
                                                '"mood", '
                                                '"style", '
                                                '"born", '
                                                '"died", '
                                                '"formed", '
                                                '"disbanded", '
                                                '"yearsactive", '
                                                '"instrument", '
                                                '"fanart", '
                                                '"thumbnail", '
                                                '"art"], '
                                            '"sort": {"method": "random"}, '
                                            '"limits": {"end": %d}}, "id": 1}'  %self.LIMIT)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'artists' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['artists']:
                    count += 1
                    #if count <= 2:
                        #log('music artist json respone: {}'.format(item))  # debug
                    path = 'musicdb://2/' + str(item['artistid']) + '/'
                    self.WINDOW.setProperty("%s.%d.Title"       % (request, count), item['label'])
                    self.WINDOW.setProperty("%s.%d.Genre"       % (request, count), " / ".join(item['genre']))
                    self.WINDOW.setProperty("%s.%d.Thumb"       % (request, count), item['thumbnail']) #remove
                    self.WINDOW.setProperty("%s.%d.Fanart"      % (request, count), item['fanart']) #remove
                    self.WINDOW.setProperty("%s.%d.Art(thumb)"  % (request, count), item['thumbnail'])
                    self.WINDOW.setProperty("%s.%d.Art(fanart)" % (request, count), item['fanart'])
                    self.WINDOW.setProperty("%s.%d.Description" % (request, count), item['description'])
                    self.WINDOW.setProperty("%s.%d.Born"        % (request, count), item['born'])
                    self.WINDOW.setProperty("%s.%d.Died"        % (request, count), item['died'])
                    self.WINDOW.setProperty("%s.%d.Formed"      % (request, count), item['formed'])
                    self.WINDOW.setProperty("%s.%d.Disbanded"   % (request, count), item['disbanded'])
                    self.WINDOW.setProperty("%s.%d.YearsActive" % (request, count), " / ".join(item['yearsactive']))
                    self.WINDOW.setProperty("%s.%d.Style"       % (request, count), " / ".join(item['style']))
                    self.WINDOW.setProperty("%s.%d.Mood"        % (request, count), " / ".join(item['mood']))
                    self.WINDOW.setProperty("%s.%d.Instrument"  % (request, count), " / ".join(item['instrument']))
                    self.WINDOW.setProperty("%s.%d.LibraryPath" % (request, count), path)

    def _fetch_song(self, request):
        if not self.Monitor.abortRequested():
            json_string = ('{"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.GetSongs", '
                                '"params": {"properties": '
                                    '["title", '
                                    '"playcount", '
                                    '"artist", '
                                    '"album", '
                                    '"comment", '
                                    '"year", '
                                    '"file", '
                                    '"thumbnail", '
                                    '"fanart", '
                                    '"art", '
                                    '"rating", '
                                    '"userrating"], '
                                '"filter": {"field": "playcount", '
                                            '"operator": "lessthan", '
                                            '"value": "1"}, '
                                '"limits": {"end": %d},' %self.LIMIT)
            if request == 'RandomSong' and self.RANDOMITEMS_UNPLAYED == "True":
                json_query = xbmc.executeJSONRPC('%s "sort": {"method": "random"}}}'  %json_string)
            else:
                json_query = xbmc.executeJSONRPC('%s  "sort": {"method": "random"}}}'  %json_string)
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'songs' in json_query['result']:
                self._clear_properties(request)
                count = 0
                for item in json_query['result']['songs']:
                    count += 1
                    #if count <= 2:
                        #log('music song json respone: {}'.format(item))  # debug
                    play = 'RunScript(' + __addonid__ + ',songid=' + str(item.get('songid')) + ')'
                    path = media_path(item['file'])
                    self.WINDOW.setProperty("%s.%d.Title"       % (request, count), item['title'])
                    self.WINDOW.setProperty("%s.%d.Artist"      % (request, count), " / ".join(item['artist']))
                    self.WINDOW.setProperty("%s.%d.Year"        % (request, count), str(item['year']))
                    self.WINDOW.setProperty("%s.%d.Rating"      % (request, count), str(int(item['rating'])-48))
                    self.WINDOW.setProperty("%s.%d.Userrating"  % (request, count), str(item['userrating']))
                    self.WINDOW.setProperty("%s.%d.Album"       % (request, count), item['album'])
                    self.WINDOW.setProperty("%s.%d.Thumb"       % (request, count), item['thumbnail']) #remove
                    self.WINDOW.setProperty("%s.%d.Fanart"      % (request, count), item['fanart']) #remove
                    self.WINDOW.setProperty("%s.%d.Art(thumb)"  % (request, count), item['thumbnail'])
                    self.WINDOW.setProperty("%s.%d.Art(fanart)" % (request, count), item['fanart'])
                    self.WINDOW.setProperty("%s.%d.File"        % (request, count), item['file'])
                    self.WINDOW.setProperty("%s.%d.Path"        % (request, count), path)
                    self.WINDOW.setProperty("%s.%d.Play"        % (request, count), play)
                    self.WINDOW.setProperty("%s.%d.Description" % (request, count), item['comment'])
            del json_query

    def _fetch_addon(self, request):
        if not self.Monitor.abortRequested():
            addonlist = []
            for content in ['music', 'video', 'unknown']:
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", '
                                                    '"method": "Addons.GetAddons", '
                                                    f'"params": {{"content": "{content}", '
                                                                '"properties": '
                                                                '["name", '
                                                                '"author", '
                                                                '"summary", '
                                                                '"version", '
                                                                '"fanart", '
                                                                '"thumbnail", '
                                                                '"enabled" ,'
                                                                '"extrainfo" ,'
                                                                '"broken"]}, '
                                                    '"id": 1}')
                json_query = simplejson.loads(json_query)
                if 'result' in json_query and 'addons' in json_query['result']:
                    # find plugins and scripts
                    for item in json_query['result']['addons']:
                        if (item['type'] == 'xbmc.python.script' or item['type'] == 'xbmc.python.pluginsource') and item['enabled']:
                            item['content'] = content
                            if item.get('extrainfo'):
                                for info in item['extrainfo']:
                                    if info.get('key') and info['key'] == 'provides':
                                        item['provides'] = info['value']
                            addonlist.append(item)
            # randomize the list
            random.shuffle(addonlist)
            self._clear_properties(request)
            count = 0
            for item in addonlist:
                count += 1
                #if count <= 2:
                #log(f'addon request {request} json response: {item}')  # debug
                self.WINDOW.setProperty("%s.%d.Title"       % (request, count), item['name'])
                self.WINDOW.setProperty("%s.%d.Author"      % (request, count), item['author'])
                self.WINDOW.setProperty("%s.%d.Summary"     % (request, count), item['summary'])
                self.WINDOW.setProperty("%s.%d.Version"     % (request, count), item['version'])
                self.WINDOW.setProperty("%s.%d.Path"        % (request, count), item['addonid'])
                self.WINDOW.setProperty("%s.%d.Thumb"       % (request, count), item['thumbnail']) #remove
                self.WINDOW.setProperty("%s.%d.Fanart"      % (request, count), item['fanart']) #remove
                self.WINDOW.setProperty("%s.%d.Art(thumb)"  % (request, count), item['thumbnail'])
                self.WINDOW.setProperty("%s.%d.Art(fanart)" % (request, count), item['fanart'])
                self.WINDOW.setProperty("%s.%d.Type"        % (request, count), item['type'])
                self.WINDOW.setProperty("%s.%d.Content"     % (request, count), item['content'])
                self.WINDOW.setProperty("%s.%d.Provides"    % (request, count), item.get('provides', ''))
                # stop if we've reached the number of items we need
                if count == self.LIMIT:
                    break
            self.WINDOW.setProperty("%s.Count" % (request), str(json_query['result']['limits']['total']))
        del json_query

    def _daemon(self):
        """keeps script running at all time
        """
        log('daemon started')
        count = 0
        home_update = False
        while (not self.Monitor.abortRequested()) and (
            self.WINDOW.getProperty('SkinWidgets_Running') == 'true'):
            if self.Monitor.waitForAbort(1):
                break
            if not self.Player.isPlayingVideo():
                if self.RANDOMITEMS_UPDATE_METHOD == 0:
                    count += 1
                    if count == self.RANDOMITEMS_TIME:
                        log('daemon random time fetch_info_random_items')
                        self._fetch_info_randomitems()
                        count = 0    # reset counter
                if self.WINDOW.getProperty('SkinWidgets_RandomItems_Update') == 'true':
                    count = 0
                    self.WINDOW.setProperty('SkinWidgets_RandomItems_Update','false')
                    log('daemon update fetch_info_randomitems')
                    self._fetch_info_randomitems()
                if  (self.RECENTITEMS_HOME_UPDATE == 'true'
                and home_update
                and xbmcgui.getCurrentWindowId() == 10000):
                    log('daemon fetch_info_recentitems')
                    self._fetch_info_recentitems()
                    home_update = False
                elif (self.RECENTITEMS_HOME_UPDATE == 'true'
                and not home_update
                and xbmcgui.getCurrentWindowId() != 10000):
                    home_update = True
        else:
            if self.Monitor.abortRequested():
                log('daemon got abortRequested returning to main __init__')
                return
            self.Monitor.update_listitems = None
            self.Monitor.update_settings = None
            self.Player.action = None
        clearlist_groups = ['Recommended','Random','Recent']
        clearlist_types = ['Movie','Episode','MusicVideo','Album', 'Artist','Song','Addon']
        log('clearing properties')
        for item_group in clearlist_groups:
            for item_type in clearlist_types:
                clear = item_group + item_type
                self._clear_properties(clear)
        log('deamon completed returning')

    def _clear_properties(self, request: str):
        """Clears hoime window properties of the requested type

        Args:
            request (str): in progress/random/last added
        """
        count = 0
        for count in range(int(self.LIMIT)):
            count += 1
            self.WINDOW.clearProperty("%s.%d.Title" % (request, count))

    def _update(self, vidtype: str):
        """Widget_Monitor runs when OnScanFinished received to update
        home window properties based on new library contents (music or
        video), or when timer fires.  Widget_Player runs when playback 
        ended

        Args:
            type (str): video/music (library was scanned)
            music/movie/episode/musicvideo (playback ended)
        """
        self.Monitor.waitForAbort(1)
        if self.Monitor.abortRequested():
            return
        if vidtype == 'movie':
            self._fetch_movies('RecommendedMovie')
            self._fetch_movies('RecentMovie')
        elif vidtype == 'episode':
            self._fetch_tvshows_recommended('RecommendedEpisode')
            self._fetch_tvshows('RecentEpisode')
        elif vidtype == 'video':
            #only on db update
            self._fetch_movies('RecommendedMovie')
            self._fetch_tvshows_recommended('RecommendedEpisode')
            self._fetch_movies('RecentMovie')
            self._fetch_tvshows('RecentEpisode')
            self._fetch_musicvideo('RecentMusicVideo')
        elif vidtype == 'musicvideo':
            self._fetch_musicvideo('RecommendedMusicVideo')
            self._fetch_musicvideo('RecentMusicVideo')
        elif vidtype == 'music':
            self._fetch_albums('RecommendedAlbum')
            self._fetch_albums('RecentAlbum')
        if self.RANDOMITEMS_UPDATE_METHOD == 1:
            # update random if db update is selected instead of timer
            if vidtype == 'video':
                self._fetch_movies('RandomMovie')
                self._fetch_tvshows('RandomEpisode')
                self._fetch_musicvideo('RandomMusicVideo')
            elif vidtype == 'music':
                self._fetch_albums('RandomAlbum')
                self._fetch_artist('RandomArtist')
                self._fetch_song('RandomSong')
                self._fetch_addon('RandomAddon')

def media_path(path:str) -> str:
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
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        path = [os.path.split(urllib.request.url2pathname(path.replace("rar://","")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://","").split('%2f/')
        path = []
        for item in temp_path:
            path.append(urllib.request.url2pathname(item))
    else:
        path = [path]
    return path[0]

def media_streamdetails(filename: str, streamdetails: dict) ->dict:
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
        videowidth = video[0]['width']
        videoheight = video[0]['height']
        if (video[0]['width'] <= 720 and video[0]['height'] <= 480):
            info['videoresolution'] = "480"
        elif (video[0]['width'] <= 768 and video[0]['height'] <= 576):
            info['videoresolution'] = "576"
        elif (video[0]['width'] <= 960 and video[0]['height'] <= 544):
            info['videoresolution'] = "540"
        elif (video[0]['width'] <= 1280 and video[0]['height'] <= 720):
            info['videoresolution'] = "720"
        elif (video[0]['width'] >= 1281 or video[0]['height'] >= 721):
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
            #log('got hdrtype {}'.format(info['hdrtype']))
        else:
            info['hdrtype'] = 'SDR'
            #log('NO hdrtype {}'.format(info['hdrtype']))
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
    #log('media_streamdetails: {}'.format(info))
    return info


class Widgets_Monitor(xbmc.Monitor):
    """wraps the Kodi Monitor class 

    Args:
        xbmc.Monitor: Kodi Monitor class
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update_listitems = kwargs['update_listitems']
        self.update_settings = kwargs['update_settings']

    def onScanFinished(self, library:str):
        """ updates widgets. Called when library scan has ended and return
        video or music to indicate which library has been scanned

        Args:
            library (str): 'video'/'music'
        """
        self.update_listitems(library)

    def onSettingsChanged(self):
        """ updates settings.  Called when addon settings are changed 
        """
        self.update_settings()

class Widgets_Player(xbmc.Player):
    """Wraps Kodi Player class

    Args:
        xbmc.Player: Kodi Player class  Updates the home window properties
        when a playing media stops or ends.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(self)
        self.type = ""
        self.action = kwargs["action"]
        self.substrings = ['-trailer', 'http://']
        self.WPMonitor=xbmc.Monitor()

    def onPlayBackStarted(self):
        """sets the media type (used for updating the home window properties)
        """
        self.WPMonitor.waitForAbort(1)
        if self.WPMonitor.abortRequested():
            return
        # Set values based on the file content
        if self.isPlayingAudio():
            self.type = "music"
        else:
            if xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
                filename = ''
                isMovie = True
                try:
                    filename = self.getPlayingFile()
                except:
                    pass
                if filename != '':
                    for string in self.substrings:
                        if string in filename:
                            isMovie = False
                            break
                if isMovie:
                    self.type = "movie"
            elif xbmc.getCondVisibility('VideoPlayer.Content(episodes)'):
                # Check for tv show title and season to make sure it's
                # really an episode
                if (xbmc.getInfoLabel('VideoPlayer.Season') != ""
                and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != ""):
                    self.type = "episode"
            elif xbmc.getCondVisibility('VideoPlayer.Content(musicvideos)'):
                self.type = "musicvideo"

    def onPlayBackEnded(self):
        """runs onPlayBackStopped
        """
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        """updates home window propertied for the last played media type
        """
        if self.type == 'movie':
            self.action('movie')
        elif self.type == 'episode':
            self.action('episode')
        elif self.type == 'music':
            self.action('music')
        elif self.type == 'musicvideo':
            self.action('musicvideo')
        self.type = ""

# Program from here:
if __name__ == "__main__":
    log(f'script version {__addonversion__} started')
    Main()
    del Widgets_Monitor
    del Widgets_Player
    del Main
    log(f'script version {__addonversion__} stopped')
