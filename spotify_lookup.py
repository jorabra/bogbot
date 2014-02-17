import json

import requests


class SpotifyLookup(object):
    """
    Simple class for helping with looking up artist, album and track
    on Spotify.
    """

    # spotify:{artist,album,track}:HASH[&extras={track,trackdetail}]
    lookup_base_url = "http://ws.spotify.com/lookup/1/.json?uri=spotify"

    def lookup(self, uri):
        if "http" in uri:
            target, spotify_id = self.parse_http_uri(uri)
        elif "spotify:" in uri:
            target, spotify_id = self.parse_spotify_uri(uri)
        else:
            # TODO: raise exception?
            return

        if target and spotify_id is not None:
            query = "%s:%s:%s" % (self.lookup_base_url, target, spotify_id)
            response = requests.get(query)
            meta_json = json.loads(response.text)
            info_string = self._make_info_string(meta_json)
            return info_string
        return None

    def _make_info_string(self, meta_json):
        target = meta_json['info']['type']
        info_string = ""
        if target != "artist":
            info_string += target.title() + ": "
            target_name = meta_json[target]['name']
            info_string += target_name + " by "
            target_artists = [artist['name'] for artist in meta_json[target]['artists']]
            if len(target_artists) == 1:
                info_string += target_artists[0]
            elif len(target_artists) == 2:
                info_string += "%s og %s" % (target_artists[0], target_artists[1])
            elif len(target_artists) > 2:
                first_artist = target_artists.pop(0)
                last_artist = target_artists.pop()
                info_string += first_artist
                for artist in target_artists:
                    info_string += ", %s" % artist
                info_string += " and %s" % last_artist

        return info_string

    def parse_http_uri(self, uri):
        # http://open.spotify.com/track/1t7adBEtxZXavJ1mbiyAWy 
        query = uri.rpartition(".com/")
        target, spotify_id = query[2].split('/')
        return target, spotify_id

    def parse_spotify_uri(self, uri):
        # spotify:track:1t7adBEtxZXavJ1mbiyAWy 
        _, target, spotify_id = uri.split(':')
        return target, spotify_id

