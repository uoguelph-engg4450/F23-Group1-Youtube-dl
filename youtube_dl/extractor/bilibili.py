# coding: utf-8
from __future__ import unicode_literals

import hashlib
import re
from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    parse_iso8601,
    smuggle_url,
    str_or_none,
    strip_jsonp,
    unified_timestamp,
    unsmuggle_url,
    urlencode_postdata,
    traverse_obj,
    srt_subtitles_timecode,
    filter_dict,
    merge_dicts,
    itertools,
    base64
)


class BiliBiliIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:(?:www|bangumi)\.)?
                        bilibili\.(?:tv|com)/
                        (?:
                            (?:
                                video/[aA][vV]|
                                anime/(?P<anime_id>\d+)/play\#
                            )(?P<id_bv>\d+)|
                            video/[bB][vV](?P<id>[^/?#&]+)
                        )
                    '''

    _TESTS = [{
        'url': 'http://www.bilibili.tv/video/av1074402/',
        'md5': '5f7d29e1a2872f3df0cf76b1f87d3788',
        'info_dict': {
            'id': '1074402',
            'ext': 'flv',
            'title': '【金坷垃】金泡沫',
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'duration': 308.067,
            'timestamp': 1398012678,
            'upload_date': '20140420',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': '菊子桑',
            'uploader_id': '156160',
        },
    }, {
        # Tested in BiliBiliBangumiIE
        'url': 'http://bangumi.bilibili.com/anime/1869/play#40062',
        'only_matching': True,
    }, {
        'url': 'http://bangumi.bilibili.com/anime/5802/play#100643',
        'md5': '3f721ad1e75030cc06faf73587cfec57',
        'info_dict': {
            'id': '100643',
            'ext': 'mp4',
            'title': 'CHAOS;CHILD',
            'description': '如果你是神明，并且能够让妄想成为现实。那你会进行怎么样的妄想？是淫靡的世界？独裁社会？毁灭性的制裁？还是……2015年，涩谷。从6年前发生的大灾害“涩谷地震”之后复兴了的这个街区里新设立的私立高中...',
        },
        'skip': 'Geo-restricted to China',
    }, {
        # Title with double quotes
        'url': 'http://www.bilibili.com/video/av8903802/',
        'info_dict': {
            'id': '8903802',
            'title': '阿滴英文｜英文歌分享#6 "Closer',
            'description': '滴妹今天唱Closer給你聽! 有史以来，被推最多次也是最久的歌曲，其实歌词跟我原本想像差蛮多的，不过还是好听！ 微博@阿滴英文',
        },
        'playlist': [{
            'info_dict': {
                'id': '8903802_part1',
                'ext': 'flv',
                'title': '阿滴英文｜英文歌分享#6 "Closer',
                'description': 'md5:3b1b9e25b78da4ef87e9b548b88ee76a',
                'uploader': '阿滴英文',
                'uploader_id': '65880958',
                'timestamp': 1488382634,
                'upload_date': '20170301',
            },
            'params': {
                'skip_download': True,  # Test metadata only
            },
        }, {
            'info_dict': {
                'id': '8903802_part2',
                'ext': 'flv',
                'title': '阿滴英文｜英文歌分享#6 "Closer',
                'description': 'md5:3b1b9e25b78da4ef87e9b548b88ee76a',
                'uploader': '阿滴英文',
                'uploader_id': '65880958',
                'timestamp': 1488382634,
                'upload_date': '20170301',
            },
            'params': {
                'skip_download': True,  # Test metadata only
            },
        }]
    }, {
        # new BV video id format
        'url': 'https://www.bilibili.com/video/BV1JE411F741',
        'only_matching': True,
    }]

    _APP_KEY = 'iVGUTjsxvpLeuDCf'
    _BILIBILI_KEY = 'aHRmhWMLkdeMuILqORnYZocwMBpMEOdt'

    def _report_error(self, result):
        if 'message' in result:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, result['message']), expected=True)
        elif 'code' in result:
            raise ExtractorError('%s returns error %d' % (self.IE_NAME, result['code']), expected=True)
        else:
            raise ExtractorError('Can\'t extract Bangumi episode ID')

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id') or mobj.group('id_bv')
        anime_id = mobj.group('anime_id')
        webpage = self._download_webpage(url, video_id)

        if 'anime/' not in url:
            cid = self._search_regex(
                r'\bcid(?:["\']:|=)(\d+)', webpage, 'cid',
                default=None
            ) or compat_parse_qs(self._search_regex(
                [r'EmbedPlayer\([^)]+,\s*"([^"]+)"\)',
                 r'EmbedPlayer\([^)]+,\s*\\"([^"]+)\\"\)',
                 r'<iframe[^>]+src="https://secure\.bilibili\.com/secure,([^"]+)"'],
                webpage, 'player parameters'))['cid'][0]
        else:
            if 'no_bangumi_tip' not in smuggled_data:
                self.to_screen('Downloading episode %s. To download all videos in anime %s, re-run youtube-dl with %s' % (
                    video_id, anime_id, compat_urlparse.urljoin(url, '//bangumi.bilibili.com/anime/%s' % anime_id)))
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': url
            }
            headers.update(self.geo_verification_headers())

            js = self._download_json(
                'http://bangumi.bilibili.com/web_api/get_source', video_id,
                data=urlencode_postdata({'episode_id': video_id}),
                headers=headers)
            if 'result' not in js:
                self._report_error(js)
            cid = js['result']['cid']

        headers = {
            'Accept': 'application/json',
            'Referer': url
        }
        headers.update(self.geo_verification_headers())

        entries = []

        RENDITIONS = ('qn=80&quality=80&type=', 'quality=2&type=mp4')
        for num, rendition in enumerate(RENDITIONS, start=1):
            payload = 'appkey=%s&cid=%s&otype=json&%s' % (self._APP_KEY, cid, rendition)
            sign = hashlib.md5((payload + self._BILIBILI_KEY).encode('utf-8')).hexdigest()

            video_info = self._download_json(
                'http://interface.bilibili.com/v2/playurl?%s&sign=%s' % (payload, sign),
                video_id, note='Downloading video info page',
                headers=headers, fatal=num == len(RENDITIONS))

            if not video_info:
                continue

            if 'durl' not in video_info:
                if num < len(RENDITIONS):
                    continue
                self._report_error(video_info)

            for idx, durl in enumerate(video_info['durl']):
                formats = [{
                    'url': durl['url'],
                    'filesize': int_or_none(durl['size']),
                }]
                for backup_url in durl.get('backup_url', []):
                    formats.append({
                        'url': backup_url,
                        # backup URLs have lower priorities
                        'preference': -2 if 'hd.mp4' in backup_url else -3,
                    })

                for a_format in formats:
                    a_format.setdefault('http_headers', {}).update({
                        'Referer': url,
                    })

                self._sort_formats(formats)

                entries.append({
                    'id': '%s_part%s' % (video_id, idx),
                    'duration': float_or_none(durl.get('length'), 1000),
                    'formats': formats,
                })
            break

        title = self._html_search_regex(
            ('<h1[^>]+\btitle=(["\'])(?P<title>(?:(?!\1).)+)\1',
             '(?s)<h1[^>]*>(?P<title>.+?)</h1>'), webpage, 'title',
            group='title')
        description = self._html_search_meta('description', webpage)
        timestamp = unified_timestamp(self._html_search_regex(
            r'<time[^>]+datetime="([^"]+)"', webpage, 'upload time',
            default=None) or self._html_search_meta(
            'uploadDate', webpage, 'timestamp', default=None))
        thumbnail = self._html_search_meta(['og:image', 'thumbnailUrl'], webpage)

        # TODO 'view_count' requires deobfuscating Javascript
        info = {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'thumbnail': thumbnail,
            'duration': float_or_none(video_info.get('timelength'), scale=1000),
        }

        uploader_mobj = re.search(
            r'<a[^>]+href="(?:https?:)?//space\.bilibili\.com/(?P<id>\d+)"[^>]*>(?P<name>[^<]+)',
            webpage)
        if uploader_mobj:
            info.update({
                'uploader': uploader_mobj.group('name').strip(),
                'uploader_id': uploader_mobj.group('id'),
            })
        if not info.get('uploader'):
            info['uploader'] = self._html_search_meta(
                'author', webpage, 'uploader', default=None)

        for entry in entries:
            entry.update(info)

        if len(entries) == 1:
            return entries[0]
        else:
            for idx, entry in enumerate(entries):
                entry['id'] = '%s_part%d' % (video_id, (idx + 1))

            return {
                '_type': 'multi_video',
                'id': video_id,
                'title': title,
                'description': description,
                'entries': entries,
            }


class BiliBiliBangumiIE(InfoExtractor):
    _VALID_URL = r'https?://bangumi\.bilibili\.com/anime/(?P<id>\d+)'

    IE_NAME = 'bangumi.bilibili.com'
    IE_DESC = 'BiliBili番剧'

    _TESTS = [{
        'url': 'http://bangumi.bilibili.com/anime/1869',
        'info_dict': {
            'id': '1869',
            'title': '混沌武士',
            'description': 'md5:6a9622b911565794c11f25f81d6a97d2',
        },
        'playlist_count': 26,
    }, {
        'url': 'http://bangumi.bilibili.com/anime/1869',
        'info_dict': {
            'id': '1869',
            'title': '混沌武士',
            'description': 'md5:6a9622b911565794c11f25f81d6a97d2',
        },
        'playlist': [{
            'md5': '91da8621454dd58316851c27c68b0c13',
            'info_dict': {
                'id': '40062',
                'ext': 'mp4',
                'title': '混沌武士',
                'description': '故事发生在日本的江户时代。风是一个小酒馆的打工女。一日，酒馆里来了一群恶霸，虽然他们的举动令风十分不满，但是毕竟风只是一届女流，无法对他们采取什么行动，只能在心里嘟哝。这时，酒家里又进来了个“不良份子...',
                'timestamp': 1414538739,
                'upload_date': '20141028',
                'episode': '疾风怒涛 Tempestuous Temperaments',
                'episode_number': 1,
            },
        }],
        'params': {
            'playlist_items': '1',
        },
    }]

    @classmethod
    def suitable(cls, url):
        return False if BiliBiliIE.suitable(url) else super(BiliBiliBangumiIE, cls).suitable(url)

    def _real_extract(self, url):
        bangumi_id = self._match_id(url)
        # Sometimes this API returns a JSONP response
        season_info = self._download_json(
            'http://bangumi.bilibili.com/jsonp/seasoninfo/%s.ver' % bangumi_id,
            bangumi_id, transform_source=strip_jsonp)['result']

        entries = [{
            '_type': 'url_transparent',
            'url': smuggle_url(episode['webplay_url'], {'no_bangumi_tip': 1}),
            'ie_key': BiliBiliIE.ie_key(),
            'timestamp': parse_iso8601(episode.get('update_time'), delimiter=' '),
            'episode': episode.get('index_title'),
            'episode_number': int_or_none(episode.get('index')),
        } for episode in season_info['episodes']]

        entries = sorted(entries, key=lambda entry: entry.get('episode_number'))

        return self.playlist_result(
            entries, bangumi_id,
            season_info.get('bangumi_title'), season_info.get('evaluate'))


class BilibiliAudioBaseIE(InfoExtractor):
    def _call_api(self, path, sid, query=None):
        if not query:
            query = {'sid': sid}
        return self._download_json(
            'https://www.bilibili.com/audio/music-service-c/web/' + path,
            sid, query=query)['data']


class BilibiliAudioIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/au(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/au1003142',
        'md5': 'fec4987014ec94ef9e666d4d158ad03b',
        'info_dict': {
            'id': '1003142',
            'ext': 'm4a',
            'title': '【tsukimi】YELLOW / 神山羊',
            'artist': 'tsukimi',
            'comment_count': int,
            'description': 'YELLOW的mp3版！',
            'duration': 183,
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }],
            },
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1564836614,
            'upload_date': '20190803',
            'uploader': 'tsukimi-つきみぐー',
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        au_id = self._match_id(url)

        play_data = self._call_api('url', au_id)
        formats = [{
            'url': play_data['cdns'][0],
            'filesize': int_or_none(play_data.get('size')),
        }]

        for a_format in formats:
            a_format.setdefault('http_headers', {}).update({
                'Referer': url,
            })

        song = self._call_api('song/info', au_id)
        title = song['title']
        statistic = song.get('statistic') or {}

        subtitles = None
        lyric = song.get('lyric')
        if lyric:
            subtitles = {
                'origin': [{
                    'url': lyric,
                }]
            }

        return {
            'id': au_id,
            'title': title,
            'formats': formats,
            'artist': song.get('author'),
            'comment_count': int_or_none(statistic.get('comment')),
            'description': song.get('intro'),
            'duration': int_or_none(song.get('duration')),
            'subtitles': subtitles,
            'thumbnail': song.get('cover'),
            'timestamp': int_or_none(song.get('passtime')),
            'uploader': song.get('uname'),
            'view_count': int_or_none(statistic.get('play')),
        }


class BilibiliAudioAlbumIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/am(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/am10624',
        'info_dict': {
            'id': '10624',
            'title': '每日新曲推荐（每日11:00更新）',
            'description': '每天11:00更新，为你推送最新音乐',
        },
        'playlist_count': 19,
    }

    def _real_extract(self, url):
        am_id = self._match_id(url)

        songs = self._call_api(
            'song/of-menu', am_id, {'sid': am_id, 'pn': 1, 'ps': 100})['data']

        entries = []
        for song in songs:
            sid = str_or_none(song.get('id'))
            if not sid:
                continue
            entries.append(self.url_result(
                'https://www.bilibili.com/audio/au' + sid,
                BilibiliAudioIE.ie_key(), sid))

        if entries:
            album_data = self._call_api('menu/info', am_id) or {}
            album_title = album_data.get('title')
            if album_title:
                for entry in entries:
                    entry['album'] = album_title
                return self.playlist_result(
                    entries, am_id, album_title, album_data.get('intro'))

        return self.playlist_result(entries, am_id)


class BiliBiliPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.bilibili\.com/player\.html\?.*?\baid=(?P<id>\d+)'
    _TEST = {
        'url': 'http://player.bilibili.com/player.html?aid=92494333&cid=157926707&page=1',
        'only_matching': True,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'http://www.bilibili.tv/video/av%s/' % video_id,
            ie=BiliBiliIE.ie_key(), video_id=video_id)


class BiliIntlBaseIE(InfoExtractor):
    _API_URL = 'https://api.bilibili.tv/intl/gateway'
    _NETRC_MACHINE = 'biliintl'

    def _call_api(self, endpoint, *args, **kwargs):
        json = self._download_json(self._API_URL + endpoint, *args, **kwargs)
        if json.get('code'):
            if json['code'] in (10004004, 10004005, 10023006):
                self.raise_login_required()
            elif json['code'] == 10004001:
                self.raise_geo_restricted()
            else:
                if json.get('message') and str(json['code']) != json['message']:
                    errmsg = f'{kwargs.get("errnote", "Unable to download JSON metadata")}: {self.IE_NAME} said: {json["message"]}'
                else:
                    errmsg = kwargs.get('errnote', 'Unable to download JSON metadata')
                if kwargs.get('fatal'):
                    raise ExtractorError(errmsg)
                else:
                    self.report_warning(errmsg)
        return json.get('data')

    def json2srt(self, json):
        data = '\n\n'.join(
            f'{i + 1}\n{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n{line["content"]}'
            for i, line in enumerate(traverse_obj(json, (
                'body', lambda _, l: l['content'] and l['from'] and l['to']))))
        return data

    def _get_subtitles(self, *, ep_id=None, aid=None):
        sub_json = self._call_api(
            '/web/v2/subtitle', ep_id or aid, fatal=False,
            note='Downloading subtitles list', errnote='Unable to download subtitles list',
            query=filter_dict({
                'platform': 'web',
                's_locale': 'en_US',
                'episode_id': ep_id,
                'aid': aid,
            })) or {}
        subtitles = {}
        for sub in sub_json.get('subtitles') or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            sub_data = self._download_json(
                sub_url, ep_id or aid, errnote='Unable to download subtitles', fatal=False,
                note='Downloading subtitles%s' % f' for {sub["lang"]}' if sub.get('lang') else '')
            if not sub_data:
                continue
            subtitles.setdefault(sub.get('lang_key', 'en'), []).append({
                'ext': 'srt',
                'data': self.json2srt(sub_data)
            })
        return subtitles

    def _get_formats(self, *, ep_id=None, aid=None):
        video_json = self._call_api(
            '/web/playurl', ep_id or aid, note='Downloading video formats',
            errnote='Unable to download video formats', query=filter_dict({
                'platform': 'web',
                'ep_id': ep_id,
                'aid': aid,
            }))
        video_json = video_json['playurl']
        formats = []
        for vid in video_json.get('video') or []:
            video_res = vid.get('video_resource') or {}
            video_info = vid.get('stream_info') or {}
            if not video_res.get('url'):
                continue
            formats.append({
                'url': video_res['url'],
                'ext': 'mp4',
                'format_note': video_info.get('desc_words'),
                'width': video_res.get('width'),
                'height': video_res.get('height'),
                'vbr': video_res.get('bandwidth'),
                'acodec': 'none',
                'vcodec': video_res.get('codecs'),
                'filesize': video_res.get('size'),
            })
        for aud in video_json.get('audio_resource') or []:
            if not aud.get('url'):
                continue
            formats.append({
                'url': aud['url'],
                'ext': 'mp4',
                'abr': aud.get('bandwidth'),
                'acodec': aud.get('codecs'),
                'vcodec': 'none',
                'filesize': aud.get('size'),
            })

        return formats

    def _parse_video_metadata(self, video_data):
        return {
            'title': video_data.get('title_display') or video_data.get('title'),
            'thumbnail': video_data.get('cover'),
            'episode_number': int_or_none(self._search_regex(
                r'^E(\d+)(?:$| - )', video_data.get('title_display') or '', 'episode number', default=None)),
        }

    # def _perform_login(self, username, password):
    #     if not Cryptodome.RSA:
    #         raise ExtractorError('pycryptodomex not found. Please install', expected=True)

    #     key_data = self._download_json(
    #         'https://passport.bilibili.tv/x/intl/passport-login/web/key?lang=en-US', None,
    #         note='Downloading login key', errnote='Unable to download login key')['data']

    #     public_key = Cryptodome.RSA.importKey(key_data['key'])
    #     password_hash = Cryptodome.PKCS1_v1_5.new(public_key).encrypt((key_data['hash'] + password).encode('utf-8'))
    #     login_post = self._download_json(
    #         'https://passport.bilibili.tv/x/intl/passport-login/web/login/password?lang=en-US', None, data=urlencode_postdata({
    #             'username': username,
    #             'password': base64.b64encode(password_hash).decode('ascii'),
    #             'keep_me': 'true',
    #             's_locale': 'en_US',
    #             'isTrusted': 'true'
    #         }), note='Logging in', errnote='Unable to log in')
    #     if login_post.get('code'):
    #         if login_post.get('message'):
    #             raise ExtractorError(f'Unable to log in: {self.IE_NAME} said: {login_post["message"]}', expected=True)
    #         else:
    #             raise ExtractorError('Unable to log in')
    
    def _search_json_BiliBili(self, start_pattern, string, name, video_id, *, end_pattern='',
                     contains_pattern=r'{(?s:.+)}', default={}, **kwargs):
        """Searches string for the JSON object specified by start_pattern"""
        # NB: end_pattern is only used to reduce the size of the initial match

        json_string = self._search_regex(
            rf'(?:{start_pattern})\s*(?P<json>{contains_pattern})\s*(?:{end_pattern})',
            string, name, group='json', fatal=False, default=None)
        if not json_string:
            return default

        return self._parse_json(json_string, video_id, ignore_extra=True, **kwargs)

class BiliIntlIE(BiliIntlBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bili(?:bili\.tv|intl\.com)/(?:[a-zA-Z]{2}/)?(play/(?P<season_id>\d+)/(?P<ep_id>\d+)|video/(?P<aid>\d+))'
    _TESTS = [{
        # Bstation page
        'url': 'https://www.bilibili.tv/en/play/34613/341736',
        'info_dict': {
            'id': '341736',
            'ext': 'mp4',
            'title': 'E2 - The First Night',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 2,
            'upload_date': '20201009',
            'episode': 'Episode 2',
            'timestamp': 1602259500,
            'description': 'md5:297b5a17155eb645e14a14b385ab547e',
            'chapters': [{
                'start_time': 0,
                'end_time': 76.242,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 76.242,
                'end_time': 161.161,
                'title': 'Intro'
            }, {
                'start_time': 1325.742,
                'end_time': 1403.903,
                'title': 'Outro'
            }],
        }
    }, {
        # Non-Bstation page
        'url': 'https://www.bilibili.tv/en/play/1033760/11005006',
        'info_dict': {
            'id': '11005006',
            'ext': 'mp4',
            'title': 'E3 - Who?',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 3,
            'description': 'md5:e1a775e71a35c43f141484715470ad09',
            'episode': 'Episode 3',
            'upload_date': '20211219',
            'timestamp': 1639928700,
            'chapters': [{
                'start_time': 0,
                'end_time': 88.0,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 88.0,
                'end_time': 156.0,
                'title': 'Intro'
            }, {
                'start_time': 1173.0,
                'end_time': 1259.535,
                'title': 'Outro'
            }],
        }
    }, {
        # Subtitle with empty content
        'url': 'https://www.bilibili.tv/en/play/1005144/10131790',
        'info_dict': {
            'id': '10131790',
            'ext': 'mp4',
            'title': 'E140 - Two Heartbeats: Kabuto\'s Trap',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 140,
        },
        'skip': 'According to the copyright owner\'s request, you may only watch the video after you log in.'
    }, {
        'url': 'https://www.bilibili.tv/en/video/2041863208',
        'info_dict': {
            'id': '2041863208',
            'ext': 'mp4',
            'timestamp': 1670874843,
            'description': 'Scheduled for April 2023.\nStudio: ufotable',
            'thumbnail': r're:https?://pic[-\.]bstarstatic.+/ugc/.+\.jpg$',
            'upload_date': '20221212',
            'title': 'Kimetsu no Yaiba Season 3 Official Trailer - Bstation',
        },
    }, {
        # episode comment extraction
        'url': 'https://www.bilibili.tv/en/play/34580/340317',
        'info_dict': {
            'id': '340317',
            'ext': 'mp4',
            'timestamp': 1604057820,
            'upload_date': '20201030',
            'episode_number': 5,
            'title': 'E5 - My Own Steel',
            'description': 'md5:2b17ab10aebb33e3c2a54da9e8e487e2',
            'thumbnail': r're:https?://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode': 'Episode 5',
            'comment_count': int,
            'chapters': [{
                'start_time': 0,
                'end_time': 61.0,
                'title': '<Untitled Chapter 1>'
            }, {
                'start_time': 61.0,
                'end_time': 134.0,
                'title': 'Intro'
            }, {
                'start_time': 1290.0,
                'end_time': 1379.0,
                'title': 'Outro'
            }],
        },
        'params': {
            'getcomments': True
        }
    }, {
        # user generated content comment extraction
        'url': 'https://www.bilibili.tv/en/video/2045730385',
        'info_dict': {
            'id': '2045730385',
            'ext': 'mp4',
            'description': 'md5:693b6f3967fb4e7e7764ea817857c33a',
            'timestamp': 1667891924,
            'upload_date': '20221108',
            'title': 'That Time I Got Reincarnated as a Slime: Scarlet Bond - Official Trailer 3| AnimeStan - Bstation',
            'comment_count': int,
            'thumbnail': 'https://pic.bstarstatic.com/ugc/f6c363659efd2eabe5683fbb906b1582.jpg',
        },
        'params': {
            'getcomments': True
        }
    }, {
        # episode id without intro and outro
        'url': 'https://www.bilibili.tv/en/play/1048837/11246489',
        'info_dict': {
            'id': '11246489',
            'ext': 'mp4',
            'title': 'E1 - Operation \'Strix\' <Owl>',
            'description': 'md5:b4434eb1a9a97ad2bccb779514b89f17',
            'timestamp': 1649516400,
            'thumbnail': 'https://pic.bstarstatic.com/ogv/62cb1de23ada17fb70fbe7bdd6ff29c29da02a64.png',
            'episode': 'Episode 1',
            'episode_number': 1,
            'upload_date': '20220409',
        },
    }, {
        'url': 'https://www.biliintl.com/en/play/34613/341736',
        'only_matching': True,
    }, {
        # User-generated content (as opposed to a series licensed from a studio)
        'url': 'https://bilibili.tv/en/video/2019955076',
        'only_matching': True,
    }, {
        # No language in URL
        'url': 'https://www.bilibili.tv/video/2019955076',
        'only_matching': True,
    }, {
        # Uppercase language in URL
        'url': 'https://www.bilibili.tv/EN/video/2019955076',
        'only_matching': True,
    }]

    def _make_url(video_id, series_id=None):
        if series_id:
            return f'https://www.bilibili.tv/en/play/{series_id}/{video_id}'
        return f'https://www.bilibili.tv/en/video/{video_id}'

    def _extract_video_metadata(self, url, video_id, season_id):
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data.get('title'):
            return smuggled_data

        webpage = self._download_webpage(url, video_id)
        # Bstation layout
        initial_data = (
            self._search_json_BiliBili(r'window\.__INITIAL_(?:DATA|STATE)__\s*=', webpage, 'preload state', video_id, default={})
            or self._search_nuxt_data(webpage, video_id, '__initialState', fatal=False, traverse=None))
        video_data = traverse_obj(
            initial_data, ('OgvVideo', 'epDetail'), ('UgcVideo', 'videoData'), ('ugc', 'archive'), expected_type=dict) or {}

        if season_id and not video_data:
            # Non-Bstation layout, read through episode list
            season_json = self._call_api(f'/web/v2/ogv/play/episodes?season_id={season_id}&platform=web', video_id)
            video_data = traverse_obj(season_json, (
                'sections', ..., 'episodes', lambda _, v: str(v['episode_id']) == video_id
            ), expected_type=dict, get_all=False)

        # XXX: webpage metadata may not accurate, it just used to not crash when video_data not found
        return merge_dicts(
            self._parse_video_metadata(video_data), self._search_json_ld(webpage, video_id, fatal=False), {
                'title': self._html_search_meta('og:title', webpage),
                'description': self._html_search_meta('og:description', webpage)
            })

    def _get_comments_reply(self, root_id, next_id=0, display_id=None):
        comment_api_raw_data = self._download_json(
            'https://api.bilibili.tv/reply/web/detail', display_id,
            note=f'Downloading reply comment of {root_id} - {next_id}',
            query={
                'platform': 'web',
                'ps': 20,  # comment's reply per page (default: 3)
                'root': root_id,
                'next': next_id,
            })

        for replies in traverse_obj(comment_api_raw_data, ('data', 'replies', ...)):
            yield {
                'author': traverse_obj(replies, ('member', 'name')),
                'author_id': traverse_obj(replies, ('member', 'mid')),
                'author_thumbnail': traverse_obj(replies, ('member', 'face')),
                'text': traverse_obj(replies, ('content', 'message')),
                'id': replies.get('rpid'),
                'like_count': int_or_none(replies.get('like_count')),
                'parent': replies.get('parent'),
                'timestamp': unified_timestamp(replies.get('ctime_text'))
            }

        if not traverse_obj(comment_api_raw_data, ('data', 'cursor', 'is_end')):
            yield from self._get_comments_reply(
                root_id, comment_api_raw_data['data']['cursor']['next'], display_id)

    def _get_comments(self, video_id, ep_id):
        for i in itertools.count(0):
            comment_api_raw_data = self._download_json(
                'https://api.bilibili.tv/reply/web/root', video_id,
                note=f'Downloading comment page {i + 1}',
                query={
                    'platform': 'web',
                    'pn': i,  # page number
                    'ps': 20,  # comment per page (default: 20)
                    'oid': video_id,
                    'type': 3 if ep_id else 1,  # 1: user generated content, 3: series content
                    'sort_type': 1,  # 1: best, 2: recent
                })

            for replies in traverse_obj(comment_api_raw_data, ('data', 'replies', ...)):
                yield {
                    'author': traverse_obj(replies, ('member', 'name')),
                    'author_id': traverse_obj(replies, ('member', 'mid')),
                    'author_thumbnail': traverse_obj(replies, ('member', 'face')),
                    'text': traverse_obj(replies, ('content', 'message')),
                    'id': replies.get('rpid'),
                    'like_count': int_or_none(replies.get('like_count')),
                    'timestamp': unified_timestamp(replies.get('ctime_text')),
                    'author_is_uploader': bool(traverse_obj(replies, ('member', 'type'))),
                }
                if replies.get('count'):
                    yield from self._get_comments_reply(replies.get('rpid'), display_id=video_id)

            if traverse_obj(comment_api_raw_data, ('data', 'cursor', 'is_end')):
                break

    def _real_extract(self, url):
        season_id, ep_id, aid = self._match_valid_url(url).group('season_id', 'ep_id', 'aid')
        video_id = ep_id or aid
        chapters = None

        if ep_id:
            intro_ending_json = self._call_api(
                f'/web/v2/ogv/play/episode?episode_id={ep_id}&platform=web',
                video_id, fatal=False) or {}
            if intro_ending_json.get('skip'):
                # FIXME: start time and end time seems a bit off a few second even it corrext based on ogv.*.js
                # ref: https://p.bstarstatic.com/fe-static/bstar-web-new/assets/ogv.2b147442.js
                chapters = [{
                    'start_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'opening_start_time')), 1000),
                    'end_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'opening_end_time')), 1000),
                    'title': 'Intro'
                }, {
                    'start_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_start_time')), 1000),
                    'end_time': float_or_none(traverse_obj(intro_ending_json, ('skip', 'ending_end_time')), 1000),
                    'title': 'Outro'
                }]

        return {
            'id': video_id,
            **self._extract_video_metadata(url, video_id, season_id),
            'formats': self._get_formats(ep_id=ep_id, aid=aid),
            'subtitles': self.extract_subtitles(ep_id=ep_id, aid=aid),
            'chapters': chapters,
            #'__post_extractor': self.extract_comments(video_id, ep_id)
        }
