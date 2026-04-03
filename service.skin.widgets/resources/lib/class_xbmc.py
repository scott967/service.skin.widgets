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

"""Extensions to Kodi classes
"""

import xbmc


class Widgets_Monitor(xbmc.Monitor):
    """wraps the Kodi Monitor class

    Args:
        xbmc.Monitor: Kodi Monitor class
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update_listitems = kwargs['update_listitems']
        self.update_settings = kwargs['update_settings']

    def onScanFinished(self, library: str):
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
        super().__init__()
        self.type = ""
        self.action = kwargs["action"]
        self.substrings = ['-trailer', 'http://']
        self.WPMonitor = xbmc.Monitor()

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
                except Exception:
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
