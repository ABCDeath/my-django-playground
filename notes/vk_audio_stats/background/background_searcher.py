import requests
import time

import discogs_client
import musicbrainzngs
import redis
import vk_api
from bs4 import BeautifulSoup
from vk_api.audio import VkAudio
from vk_api.exceptions import AccessDenied


def lockable(lock_name=None):
    def decorator(func):
        nonlocal lock_name
        if not lock_name:
            lock_name = ''.join([func.__name__, '_lock'])

        lock = REDIS_CLIENT.lock(lock_name)

        def wrapper(*args, **kwargs):
            with lock:
                res = func(*args, **kwargs)

            return res

        return wrapper

    return decorator



class Singleton(type):
    _instance = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance[cls]


class TagFinder(metaclass=Singleton):
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
        self._discogs_last_time = 0

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
            return sorted(res[0]['tag-list'],
                          key=lambda x: x['count'])[-1]['name']

        for r in res[0]['release-list']:
            if 'tag-list' in r:
                return sorted(r['tag-list'],
                              key=lambda x: int(x['ext:score']))[-1]['name']

        artist_id = res[0]['artist-credit'][0]['artist']['id']
        a = musicbrainzngs.get_artist_by_id(id=artist_id, includes=['tags'])

        if 'tag-list' not in a:
            return None

        return sorted(a['tag-list'],
                      key=lambda x: int(x['ext:score']))[-1]['name']

    def _discogs(self, artist, track):
        self._wait(self._google_last_time, 1)

        res = self._dgs.search('*', type='release', artist=artist, track=track)

        self._discogs_last_time = time.time()

        return (res[0].styles or res[0].genres)[0] if res else None

    def _google(self, artist, track):
        query = (' '.join([artist, track, 'genre'])
                 .replace(' ', '+').replace('/', '%2F'))

        self._wait(self._google_last_time, 1)

        url = f'https://www.google.com/search?q={query}&num=1&hl=en'
        # TODO: ??? ('Connection aborted.', OSError(107, 'Transport endpoint is not connected'))
        try:
            response = requests.get(url, headers=self._user_agent)
        except requests.exceptions.ConnectionError as ex:
            print(f'error: {ex} while trying url {url}')
            return None

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


class VkApi(metaclass=Singleton):
    def __init__(self, credentials):
        self._session = vk_api.VkApi(login=credentials['login'],
                                     password=credentials['password'],
                                     token=credentials['token'])
        try:
            self._session.auth()
        except vk_api.AuthError as e:
            # do smth
            print(e)

        self._audio = VkAudio(self._session)
        self._api = self._session.get_api()

    def friends(self, id):
        friend_list = self._api.friends.get(user_id=id, fields=['name'])
        return {u['id']: ' '.join([u['first_name'], u['last_name']])
                for u in friend_list['items'] if 'deactivated' not in u}

    def username(self, id):
        user = self._api.users.get(user_ids=id)[0]
        return ' '.join([user['first_name'], user['last_name']])

    def track_list(self, id):
        try:
            tracklist = [(t['artist'].lower(), t['title'].lower())
                         for t in self._audio.get(owner_id=id)]
        except AccessDenied:
            tracklist = []

        return tracklist



REDIS_CLIENT = redis.Redis()


class TagFinderLockable(TagFinder):
    @lockable()
    def _musicbrainz(self, *args, **kwargs):
        return super()._musicbrainz(*args, **kwargs)

    @lockable()
    def _discogs(self, *args, **kwargs):
        return super()._discogs(*args, **kwargs)

    @lockable()
    def _google(self, *args, **kwargs):
        return super()._google(*args, **kwargs)

class VkApiLockable(VkApi):
    @lockable('vk_lock')
    def friends(self, *args, **kwargs):
        return super().friends(*args, **kwargs)

    @lockable('vk_lock')
    def username(self, *args, **kwargs):
        return super().username(*args, **kwargs)

    @lockable('vk_lock')
    def track_list(self, *args, **kwargs):
        return super().track_list(*args, **kwargs)
