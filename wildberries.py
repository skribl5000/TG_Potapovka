import requests

from wb_creds import wb_token, wb_token_64
import pandas as pd


class WBConnector:
    BASE_API_URL = 'https://suppliers-stats.wildberries.ru/api/v1/supplier/'

    def __init__(self, token, request_object):
        self.request_url = self._collect_url(request_object)
        self.params = {'key': token}

    def _collect_url(self, request_object):
        return self.BASE_API_URL + request_object

    def get_data_dict(self, date_from, params={}):
        params.update(self.params)
        params.update({'dateFrom': date_from})

        response = requests.get(self.request_url, params=params)
        return response.json()

    def get_data_df(self, date_from, params={}):
        response_dict = self.get_data_dict(date_from, params=params)
        return pd.DataFrame(data=response_dict)
