import json
import os
import requests
import sys
import time

import discogs_client
import django
import musicbrainzngs
import vk_api
from bs4 import BeautifulSoup
from vk_api.audio import VkAudio


sys.path.extend([os.getcwd() + '/notes'])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notes.settings")
django.setup()


with open('credentials.json') as cred_file:
    credentials = json.load(cred_file)


class TagFinder:
    def __init__(self, discogs_creds):
        self._dgs = discogs_client.Client(
            discogs_creds['app_name'], user_token=discogs_creds['token'])
        musicbrainzngs.set_useragent('MyTagFinderApp', '0.01')
        self._user_agent = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/61.0.3163.100 Safari/537.36'
            }

        self._google_last_time = 0

    def _wait(self, last, rate):
        if time.time() - last < 1 / rate:
            time.sleep(1 / rate - (time.time() - last))

    def _musicbrainz(self, artist, track):
        res = sorted(
            musicbrainzngs.search_recordings(
                recording=track, artist=artist, type='Album',
                status='Official', limit=100, strict=True)
            ['recording-list'], key=lambda x: int(x['ext:score']), reverse=True)

        if not res:
            return None

        if 'tag-list' in res[0]:
            return sorted(res[0]['tag-list'], key=lambda x: x['count'])[-1]

        for r in res[0]['release-list']:
            if 'tag-list' in r:
                return sorted(r['tag-list'],
                              key=lambda x: int(x['ext:score']))[-1]

        artist_id = res[0]['artist-credit'][0]['artist']['id']
        a = musicbrainzngs.get_artist_by_id(id=artist_id, includes=['tags'])

        return sorted(a['tag-list'], key=lambda x: int(x['ext:score']))[-1]

    def _discogs(self, artist, track):
        res = self._dgs.search('*', type='release', artist=artist, track=track)
        return (res[0].styles or res[0].genres)[0] if res else None

    def _google(self, artist, track):
        query = (' '.join([artist, track, 'genre'])
                 .replace(' ', '+').replace('/', '%2F'))

        self._wait(self._google_last_time, 1)

        url = f'https://www.google.com/search?q={query}&num=1&hl=en'
        response = requests.get(url, headers=self._user_agent)
        self._google_last_time = time.time()

        soup = BeautifulSoup(response.text, 'lxml')

        # рандомные названия классов в html, поэтому такая фигня
        main = soup('a', class_='rl_item rl_item_base')
        alternative = soup('div', class_='kp-hc')

        if main:
            genre_tag = main[0].find('div', class_='title')
        elif alternative:
            genre_tag = alternative[0].find('div', role='heading').next
        else:
            return None

        return genre_tag.string.lower()

    def find(self, artist, track):
        return (self._discogs(artist, track) or
                self._musicbrainz(artist, track) or
                self._google(artist, track))


class VkData:
    def __init__(self, credentials):
        self._session = vk_api.VkApi(login=credentials['vk']['login'],
                                     password=credentials['vk']['password'],
                                     token=credentials['vk']['token'])
        try:
            self._session.auth()
        except vk_api.AuthError as e:
            # do smth
            print(e)

        self._audio = VkAudio(self._session)
        self._api = self._session.get_api()

    def friends(self, id):
        return self._api.friends.get(user_id=id)['items']

    def username(self, id):
        user = self._api.users.get(user_ids=id)
        return ' '.join([user['first_name'], user['last_name']])

    def track_list(self, id):
        return [(t['artist'], t['title'])
                for t in self._audio.get(owner_id=id)]


def get_track_list(vk_id):
    pass


def find_tags(artist, track):
    pass

