# coding=utf-8
# author=UlionTse

"""
Copyright (C) 2017  UlionTse

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Email: uliontse@outlook.com

translators  Copyright (C) 2017  UlionTse
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c' for details.
"""

import os
import re
import sys
import time
import json
import uuid
import hmac
import base64
import random
import hashlib
import datetime
import warnings
import functools
import urllib.parse
from typing import Optional, Union, Tuple, List

import tqdm
import httpx
import execjs
import requests
import niquests
import lxml.etree as lxml_etree
import pathos.multiprocessing as pathos_multiprocessing
import cryptography.hazmat.primitives.ciphers as cry_ciphers
import cryptography.hazmat.primitives.padding as cry_padding
import cryptography.hazmat.primitives.hashes as cry_hashes
import cryptography.hazmat.primitives.serialization as cry_serialization
import cryptography.hazmat.primitives.asymmetric.padding as cry_asym_padding


LangMapKwargsType = Union[str, bool]
ApiKwargsType = Union[str, int, float, bool, dict]
SessionType = Union[requests.sessions.Session, niquests.sessions.Session, httpx.Client]
ResponseType = Union[requests.models.Response, niquests.models.Response, httpx.Response]


__all__ = [
    'translate_text', 'translators_pool',# 'translate_html'

    'bing',

    '_bing'
]  # 37


class TranslatorError(Exception):
    pass


class Tse:
    def __init__(self):
        self.author = 'UlionTse'
        self.all_begin_time = time.time()
        self.default_session_freq = int(1e3)
        self.default_session_seconds = 1.5e3
        self.transform_en_translator_pool = ('itranslate', 'lingvanex', 'myMemory', 'apertium', 'cloudTranslation', 'translateMe')
        self.auto_pool = ('auto', 'detect', 'auto-detect', 'all')
        self.zh_pool = ('zh', 'zh-CN', 'zh-cn', 'zh-CHS', 'zh-Hans', 'zh-Hans_CN', 'cn', 'chi', 'Chinese')

    @staticmethod
    def time_stat(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_show_time_stat = kwargs.get('if_show_time_stat', False)
            show_time_stat_precision = kwargs.get('show_time_stat_precision', 2)
            sleep_seconds = kwargs.get('sleep_seconds', 0)

            if if_show_time_stat and sleep_seconds >= 0:
                t1 = time.time()
                result = func(*args, **kwargs)
                t2 = time.time()
                cost_time = round((t2 - t1 - sleep_seconds), show_time_stat_precision)
                sys.stderr.write(f'TimeSpent(function: {func.__name__[:-4]}): {cost_time}s\n')
                return result
            return func(*args, **kwargs)
        return _wrapper

    @staticmethod
    def get_timestamp() -> int:
        return int(time.time() * 1e3)

    @staticmethod
    def get_uuid() -> str:
        _uuid = ''
        for i in range(8):
            _uuid += hex(int(65536 * (1 + random.random())))[2:][1:]
            if 1 <= i <= 4:
                _uuid += '-'
        return _uuid

    @staticmethod
    def get_headers(host_url: str,
                    if_api: bool = False,
                    if_referer_for_host: bool = True,
                    if_ajax_for_api: bool = True,
                    if_json_for_api: bool = False,
                    if_multipart_for_api: bool = False,
                    if_http_override_for_api: bool = False
                    ) -> dict:

        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        host_headers = {
            'Referer' if if_referer_for_host else 'Host': host_url,
            "User-Agent": user_agent,
        }
        api_headers = {
            'Origin': f'https://{urllib.parse.urlparse(host_url.strip("/")).netloc}',
            'Referer': host_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "User-Agent": user_agent,
        }
        if if_api and not if_ajax_for_api:
            api_headers.pop('X-Requested-With')
            api_headers.update({'Content-Type': 'text/plain'})
        if if_api and if_json_for_api:
            api_headers.update({'Content-Type': 'application/json'})
        if if_api and if_multipart_for_api:
            api_headers.pop('Content-Type')
        if if_api and if_http_override_for_api:
            api_headers.update({'X-HTTP-Method-Override': 'GET'})
        return host_headers if not if_api else api_headers

    def check_en_lang(self, from_lang: str, to_lang: str, default_translator: Optional[str] = None, default_lang: str = 'en-US') -> Tuple[str, str]:
        if default_translator and default_translator in self.transform_en_translator_pool:
            from_lang = default_lang if from_lang == 'en' else from_lang
            to_lang = default_lang if to_lang == 'en' else to_lang
            from_lang = default_lang.replace('-', '_') if default_translator == 'lingvanex' and from_lang[:3] == 'en-' else from_lang
            to_lang = default_lang.replace('-', '_') if default_translator == 'lingvanex' and to_lang[:3] == 'en-' else to_lang
        return from_lang, to_lang

    def check_language(self,
                       from_language: str,
                       to_language: str,
                       language_map: dict,
                       output_auto: str = 'auto',
                       output_zh: str = 'zh',
                       output_en_translator: Optional[str] = None,
                       output_en: str = 'en-US',
                       if_check_lang_reverse: bool = True,
                       ) -> Tuple[str, str]:

        if output_en_translator:
            from_language, to_language = self.check_en_lang(from_language, to_language, output_en_translator, output_en)

        from_language = output_auto if from_language in self.auto_pool else from_language
        from_language = output_zh if from_language in self.zh_pool else from_language
        to_language = output_zh if to_language in self.zh_pool else to_language

        if from_language != output_auto and from_language not in language_map:
            raise TranslatorError('Unsupported from_language[{}] in {}.'.format(from_language, sorted(language_map.keys())))
        elif to_language not in language_map and if_check_lang_reverse:
            raise TranslatorError('Unsupported to_language[{}] in {}.'.format(to_language, sorted(language_map.keys())))
        elif from_language != output_auto and to_language not in language_map[from_language]:
            raise TranslatorError('Unsupported translation: from [{0}] to [{1}]!'.format(from_language, to_language))
        elif from_language == to_language:
            raise TranslatorError(f'from_language[{from_language}] and to_language[{to_language}] should not be same.')
        return from_language, to_language

    @staticmethod
    def warning_auto_lang(translator: str, default_from_language: str, if_print_warning: bool = True) -> str:
        if if_print_warning:
            warn_tips = f'Unsupported [from_language=auto({default_from_language} instead)] with [{translator}]!'
            warnings.warn(f'{warn_tips} Please specify it.')
        return default_from_language

    @staticmethod
    def debug_lang_kwargs(from_language: str, to_language: str, default_from_language: str, if_print_warning: bool = True) -> dict:
        kwargs = {
            'from_language': from_language,
            'to_language': to_language,
            'default_from_language': default_from_language,
            'if_print_warning': if_print_warning,
        }
        return kwargs

    @staticmethod
    def debug_language_map(func):
        def make_temp_language_map(from_language: str, to_language: str, default_from_language: str) -> dict:
            if from_language == to_language or to_language == 'auto':
                raise TranslatorError

            temp_language_map = {from_language: to_language}
            if from_language != 'auto':
                temp_language_map.update({to_language: from_language})
            elif default_from_language != to_language:
                temp_language_map.update({default_from_language: to_language, to_language: default_from_language})

            return temp_language_map

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                language_map = func(*args, **kwargs)
                if not language_map:
                    raise TranslatorError
                return language_map
            except Exception as e:
                if kwargs.get('if_print_warning', True):
                    warnings.warn(f'GetLanguageMapError: {str(e)}.\nThe function make_temp_language_map() works.')
                return make_temp_language_map(kwargs.get('from_language'), kwargs.get('to_language'), kwargs.get('default_from_language'))
        return _wrapper
    
    @staticmethod
    def check_input_limit(query_text: str, input_limit: int) -> None:
        if len(query_text) > input_limit:
            raise TranslatorError

    @staticmethod
    def check_query(func):
        def check_query_text(query_text: str, if_ignore_empty_query: bool, if_ignore_limit_of_length: bool, limit_of_length: int, bias_of_length: int = 10) -> str:
            if not isinstance(query_text, str):
                raise TranslatorError

            query_text = query_text.strip()
            qt_length = len(query_text)
            limit_of_length -= bias_of_length  # #154

            if qt_length == 0 and not if_ignore_empty_query:
                raise TranslatorError("The `query_text` can't be empty!")
            if qt_length >= limit_of_length and not if_ignore_limit_of_length:
                raise TranslatorError('The length of `query_text` exceeds the limit.')
            else:
                if qt_length >= limit_of_length:
                    warnings.warn(f'The length of `query_text` is {qt_length}, above {limit_of_length}.')
                    return query_text[:limit_of_length]
            return query_text

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_ignore_empty_query = kwargs.get('if_ignore_empty_query', True)
            if_ignore_limit_of_length = kwargs.get('if_ignore_limit_of_length', False)
            limit_of_length = kwargs.get('limit_of_length', 20000)
            is_detail_result = kwargs.get('is_detail_result', False)

            query_text = list(args)[1] if len(args) >= 2 else kwargs.get('query_text')
            query_text = check_query_text(query_text, if_ignore_empty_query, if_ignore_limit_of_length, limit_of_length)
            if not query_text and if_ignore_empty_query:
                return {'data': query_text} if is_detail_result else query_text

            if len(args) >= 2:
                new_args = list(args)
                new_args[1] = query_text
                return func(*tuple(new_args), **kwargs)
            return func(*args, **{**kwargs, **{'query_text': query_text}})
        return _wrapper

    @staticmethod
    def uncertified(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                raise_tips1 = f'The function {func.__name__[:-4]}() has been not certified yet.'
                raise_tips2_url = 'https://github.com/UlionTse/translators#supported-translation-services'
                raise_tips2 = f'Please read for details: Status of Translator on this webpage({raise_tips2_url}).'
                raise TranslatorError(f'{raise_tips1} {raise_tips2}')
        return _wrapper

    # @staticmethod
    # def certified(func):
    #     @functools.wraps(func)
    #     def _wrapper(*args, **kwargs):
    #         try:
    #             return func(*args, **kwargs)
    #         except Exception as e:
    #             raise TranslatorError(e)
    #     return _wrapper

    @staticmethod
    def get_client_session(http_client: str = 'requests', proxies: Optional[dict] = None) -> SessionType:
        if http_client not in ('requests', 'niquests', 'httpx'):
            raise TranslatorError

        if proxies is None:
            proxies = {}

        if http_client == 'requests':
            session = requests.Session()
            session.proxies = proxies
        elif http_client == 'niquests':
            session = niquests.Session(happy_eyeballs=True)
            session.proxies = proxies
        else:
            proxy_url = proxies.get('http') or proxies.get('https')
            session = httpx.Client(follow_redirects=True, proxy=proxy_url)
        return session


class Region(Tse):
    def __init__(self):
        super().__init__()
        self.get_addr_url = 'https://geolocation.onetrust.com/cookieconsentpub/v1/geo/location'
        self.get_ip_url = 'https://httpbin.org/ip'
        self.ip_api_addr_url = 'http://ip-api.com/json'  # must http.
        self.ip_tb_add_url = 'https://ip.taobao.com/outGetIpInfo'
        self.default_region = os.environ.get('translators_default_region', None)

    def get_region_of_server(self, if_judge_cn: bool = True, if_print_region: bool = True) -> str:
        if self.default_region:
            if if_print_region:
                sys.stderr.write(f'Using customized region {self.default_region} server backend.\n\n')
            return ('CN' if self.default_region == 'China' else 'EN') if if_judge_cn else self.default_region

        _headers_fn = lambda url: self.get_headers(url, if_api=False, if_referer_for_host=True)
        try:
            try:
                data = json.loads(requests.get(self.get_addr_url, headers=_headers_fn(self.get_addr_url)).text[9:-2])
                if if_print_region:
                    sys.stderr.write(f'Using region {data.get("stateName")} server backend.\n\n')
                return data.get('country') if if_judge_cn else data.get("stateName")
            except:
                ip_address = requests.get(self.get_ip_url, headers=_headers_fn(self.get_ip_url)).json()['origin']
                payload = {'ip': ip_address, 'accessKey': 'alibaba-inc'}
                data = requests.post(url=self.ip_tb_add_url, data=payload, headers=_headers_fn(self.ip_tb_add_url)).json().get('data')
                return data.get('country_id')  # region_id

        except requests.exceptions.ConnectionError:
            raise TranslatorError('Unable to connect the Internet.\n\n')
        except Exception:
            warnings.warn('Unable to find server backend.\n\n')
            region = input('Please input your server region need to visit:\neg: [Qatar, China, ...]\n\n')
            sys.stderr.write(f'Using region {region} server backend.\n\n')
            return 'CN' if region == 'China' else 'EN'

class Bing(Tse):
    def __init__(self, server_region='EN'):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = None
        self.cn_host_url = 'https://cn.bing.com/Translator'
        self.en_host_url = 'https://www.bing.com/Translator'
        self.server_region = server_region
        self.api_url = None
        self.host_headers = None
        self.api_headers = None
        self.language_map = None
        self.session = None
        self.tk = None
        self.ig_iid = None
        self.query_count = 0
        self.output_auto = 'auto-detect'
        self.output_zh = 'zh-Hans'
        self.input_limit = int(1e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(host_html)
        lang_list = et.xpath('//*[@id="tta_srcsl"]/option/@value') or et.xpath('//*[@id="t_srcAllLang"]/option/@value')
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    def get_ig_iid(self, host_html: str) -> dict:
        et = lxml_etree.HTML(host_html)
        iid = et.xpath('//*[@id="tta_outGDCont"]/@data-iid')[0]  # 'translator.5028'
        ig = re.compile('IG:"(.*?)"').findall(host_html)[0]
        return {'iid': iid, 'ig': ig}

    def get_tk(self, host_html: str) -> dict:
        result_str = re.compile('var params_AbusePreventionHelper = (.*?);').findall(host_html)[0]
        result = execjs.eval(result_str)
        return {'key': result[0], 'token': result[1]}

    @Tse.time_stat
    @Tse.check_query
    def bing_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en', **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://bing.com/Translator, https://cn.bing.com/Translator.
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx']
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_ignore_empty_query: bool, default False.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param if_use_cn_host: bool, default None.
        :return: str or dict
        """

        use_cn_condition = kwargs.get('if_use_cn_host', None) or self.server_region == 'CN'
        self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url
        self.api_url = self.host_url.replace('Translator', 'ttranslatev3')
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)

        timeout = kwargs.get('timeout', None)
        proxies = kwargs.get('proxies', None)
        sleep_seconds = kwargs.get('sleep_seconds', 0)
        http_client = kwargs.get('http_client', 'requests')
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.tk and self.ig_iid):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.tk = self.get_tk(host_html)
            self.ig_iid = self.get_ig_iid(host_html)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language, if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh, output_auto=self.output_auto)

        payload = {
            'text': query_text,
            'fromLang': from_language,
            'to': to_language,
            'tryFetchingGenderDebiasedTranslations': 'true'
        }
        payload = {**payload, **self.tk}
        api_url_param = f'?isVertical=1&&IG={self.ig_iid["ig"]}&IID={self.ig_iid["iid"]}'
        api_url = ''.join([self.api_url, api_url_param])
        r = self.session.post(api_url, headers=self.host_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        time.sleep(sleep_seconds)
        self.query_count += 1

        try:
            data = r.json()
            return data[0] if is_detail_result else data[0]['translations'][0]['text']
        except requests.exceptions.JSONDecodeError:  #122
            data_html = r.text
            et = lxml_etree.HTML(data_html)
            ss = et.xpath('//*/textarea/text()')
            return {'data': ss} if is_detail_result else ss[-1]


class TranslatorsServer:
    def __init__(self):
        self.cpu_cnt = os.cpu_count()
        self._region = Region()
        self.get_region_of_server = self._region.get_region_of_server
        self.server_region = self.get_region_of_server(if_print_region=False)
        # self._alibaba = AlibabaV2()
        # self.alibaba = self._alibaba.alibaba_api
        self._bing = Bing(server_region=self.server_region)
        self.bing = self._bing.bing_api
        self._translators_dict = {
            'bing': self._bing,
        }
        self.translators_dict = {
            'bing': self.bing,
        }
        self.translators_pool = list(self.translators_dict.keys())
        self.not_en_langs = {'utibet': 'ti', 'mglip': 'mon'}
        self.not_zh_langs = {'languageWire': 'fr', 'tilde': 'fr', 'elia': 'fr', 'apertium': 'spa', 'judic': 'de'}
        self.pre_acceleration_label = 0
        self.example_query_text = '你好。\n欢迎你！'
        self.success_translators_pool = []
        self.failure_translators_pool = []

    def translate_text(self,
                       query_text: str,
                       translator: str = 'bing',
                       from_language: str = 'auto',
                       to_language: str = 'en',
                       if_use_preacceleration: bool = False,
                       **kwargs: ApiKwargsType,
                       ) -> Union[str, dict]:
        """
        :param query_text: str, must.
        :param translator: str, default 'bing'.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param if_use_preacceleration: bool, default False.
        :param **kwargs:
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx']
                :param professional_field: str, support alibaba(), baidu(), caiyun(), cloudTranslation(), elia(), sysTran(), youdao(), volcEngine() only.
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_use_cn_host: bool, default False. Support google(), bing() only.
                :param reset_host_url: str, default None. Support google(), yandex() only.
                :param if_check_reset_host_url: bool, default True. Support google(), yandex() only.
                :param if_ignore_empty_query: bool, default True.
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param lingvanex_model: str, default 'B2C', choose from ("B2C", "B2B").
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str or dict
        """

        if translator not in self.translators_pool:
            raise TranslatorError

        if not self.pre_acceleration_label and if_use_preacceleration:
            _ = self.preaccelerate()

        return self.translators_dict[translator](query_text=query_text, from_language=from_language, to_language=to_language, **kwargs)

    # def translate_html(self,
    #                    html_text: str,
    #                    translator: str = 'bing',
    #                    from_language: str = 'auto',
    #                    to_language: str = 'en',
    #                    n_jobs: int = 1,
    #                    if_use_preacceleration: bool = False,
    #                    **kwargs: ApiKwargsType,
    #                    ) -> str:
    #     """
    #     Translate the displayed content of html without changing the html structure.
    #     :param html_text: str, must.
    #     :param translator: str, default 'bing'.
    #     :param from_language: str, default 'auto'.
    #     :param to_language: str, default 'en'.
    #     :param n_jobs: int, default 1. -1 means os.cpu_cnt().
    #     :param if_use_preacceleration: bool, default False.
    #     :param **kwargs:
    #             :param is_detail_result: bool, default False, must False.
    #             :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx']
    #             :param professional_field: str, support alibaba(), baidu(), caiyun(), cloudTranslation(), elia(), sysTran(), youdao(), volcEngine() only.
    #             :param timeout: Optional[float], default None.
    #             :param proxies: Optional[dict], default None.
    #             :param sleep_seconds: float, default 0.
    #             :param update_session_after_freq: int, default 1000.
    #             :param update_session_after_seconds: float, default 1500.
    #             :param if_use_cn_host: bool, default False. Support google(), bing() only.
    #             :param reset_host_url: str, default None. Support google(), argos(), yandex() only.
    #             :param if_check_reset_host_url: bool, default True. Support google(), yandex() only.
    #             :param if_ignore_empty_query: bool, default True.
    #             :param if_ignore_limit_of_length: bool, default False.
    #             :param limit_of_length: int, default 20000.
    #             :param if_show_time_stat: bool, default False.
    #             :param show_time_stat_precision: int, default 2.
    #             :param if_print_warning: bool, default True.
    #             :param lingvanex_model: str, default 'B2C', choose from ("B2C", "B2B").
    #             :param myMemory_mode: str, default "web", choose from ("web", "api").
    #     :return: str
    #     """
    #
    #     if translator not in self.translators_pool or kwargs.get('is_detail_result', False) or n_jobs > self.cpu_cnt:
    #         raise TranslatorError
    #
    #     if not self.pre_acceleration_label and if_use_preacceleration:
    #         _ = self.preaccelerate()
    #
    #     def _translate_text(sentence: str) -> Tuple[str, str]:
    #         return sentence, self.translators_dict[translator](query_text=sentence, from_language=from_language, to_language=to_language, **kwargs)
    #
    #     pattern = re.compile('>([\\s\\S]*?)<')  # not perfect
    #     sentence_list = list(set(pattern.findall(html_text)))
    #
    #     n_jobs = self.cpu_cnt if n_jobs <= 0 else n_jobs
    #     with pathos_multiprocessing.ProcessPool(n_jobs) as pool:
    #         result_list = pool.map(_translate_text, sentence_list)
    #
    #     result_dict = {text: f'>{ts_text}<' for text, ts_text in result_list}
    #     _get_result_func = lambda k: result_dict.get(k.group(1), '')
    #     return pattern.sub(repl=_get_result_func, string=html_text)

    def _test_translate(self, _ts: str, timeout: Optional[float] = None, if_show_time_stat: bool = False) -> str:
        from_language = self.not_zh_langs[_ts] if _ts in self.not_zh_langs else 'auto'
        to_language = self.not_en_langs[_ts] if _ts in self.not_en_langs else 'en'
        result = self.translators_dict[_ts](
            query_text=self.example_query_text,
            translator=_ts,
            from_language=from_language,
            to_language=to_language,
            if_print_warning=False,
            timeout=timeout,
            if_show_time_stat=if_show_time_stat
        )
        return result
    
    def get_languages(self, translator: str = 'bing'):
        language_map = self._translators_dict[translator].language_map
        if language_map:
            return language_map

        _ = self._test_translate(_ts=translator)
        return self._translators_dict[translator].language_map

    def preaccelerate(self, timeout: Optional[float] = None, if_show_time_stat: bool = True, **kwargs: str) -> dict:
        if self.pre_acceleration_label > 0:
            raise TranslatorError('Preacceleration can only be performed once.')

        self.example_query_text = kwargs.get('example_query_text', self.example_query_text)

        sys.stderr.write('Preacceleration-Process will take a few minutes.\n')
        sys.stderr.write('Tips: The smaller `timeout` value, the fewer translators pass the test '
                         'and the less time it takes to preaccelerate. However, the slow speed of '
                         'preacceleration does not mean the slow speed of later translation.\n\n')

        for i in tqdm.tqdm(range(len(self.translators_pool)), desc='Preacceleration Process', ncols=80):
            _ts = self.translators_pool[i]
            try:
                _ = self._test_translate(_ts, timeout, if_show_time_stat)
                self.success_translators_pool.append(_ts)
            except:
                self.failure_translators_pool.append(_ts)

            self.pre_acceleration_label += 1
        return {'success': self.success_translators_pool, 'failure': self.failure_translators_pool}

    def speedtest(self, **kwargs: List[str]) -> None:
        if self.pre_acceleration_label < 1:
            raise TranslatorError('Preacceleration first.')

        test_translators_pool = kwargs.get('test_translators_pool', self.success_translators_pool)

        sys.stderr.write('SpeedTest-Process will take a few seconds.\n\n')
        for i in tqdm.tqdm(range(len(test_translators_pool)), desc='SpeedTest Process', ncols=80):
            _ts = test_translators_pool[i]
            try:
                _ = self._test_translate(_ts, timeout=None, if_show_time_stat=True)
            except:
                pass
        return

    def preaccelerate_and_speedtest(self, timeout: Optional[float] = None, **kwargs: str) -> dict:
        result = self.preaccelerate(timeout=timeout, **kwargs)
        sys.stderr.write('\n\n')
        self.speedtest()
        return result


tss = TranslatorsServer()

# _alibaba = tss._alibaba
# alibaba = tss.alibaba
_bing = tss._bing
bing = tss.bing

translate_text = tss.translate_text
# translate_html = tss.translate_html
translators_pool = tss.translators_pool
get_languages = tss.get_languages
get_region_of_server = tss.get_region_of_server

preaccelerate = tss.preaccelerate
speedtest = tss.speedtest
preaccelerate_and_speedtest = tss.preaccelerate_and_speedtest
# sys.stderr.write(f'Support translators {translators_pool} only.\n')
