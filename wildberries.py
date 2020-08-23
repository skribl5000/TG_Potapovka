import requests
from datetime import datetime, timedelta

from wb_creds import wb_token, wb_token_64
import pandas as pd
from module import GoogleSheet
from loc_secrets import test_token, test_SPREADSHEET_ID
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                               ['https://www.googleapis.com/auth/spreadsheets',
                                                                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
google_service = apiclient.discovery.build('sheets', 'v4', http=httpAuth, cache_discovery=False)


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


class SpecificationManager:
    def __init__(self, token):
        self.token = token
        self.base_url = 'https://specifications.wildberries.ru/api/v1/Specification/'
        self.headers = {'accept': 'application/json',
            'X-Supplier-Cert-Serial': token}

    def get_specifications(self) -> dict:
        url = self.base_url + 'speclist'

        response = requests.get(url, headers=self.headers)
        return response.json()['Data']

    def get_nomenclature(self) -> pd.DataFrame:
        result = []
        mapping = {}

        useful_fields = ['Баркод', 'Марка', 'Артикул цвета', 'Предмет', 'Наименование', 'Страна производитель',
                         'Размер на бирке', 'ТНВЭД', 'Розничная цена', 'Цвет', 'Артикул поставщика', 'Код', 'Комплектация']

        specifications = self.get_specifications()
        for specification in specifications:
            a = requests.get('https://specifications.wildberries.ru/api/v1/Specification/specdata/' + specification[
                'specification_uid'], headers=self.headers)
            try:
                for field in a.json()['Data']['Fields']:
                    mapping[field['Id']] = field['Name']

                for item in a.json()['Data']['Data']:
                    item_data = {}
                    for field in item:
                        # if mapping[field['FieldId']] in useful_fields:
                        if True:
                            item_data[mapping[field['FieldId']]] = field['Value']
                    result.append(item_data)
            except Exception as e:
                print(e)
        df = pd.DataFrame(result).fillna('')
        df.to_excel('Data.xlsx', index=False)
        df.go_nahui()
        return pd.DataFrame(result).fillna('')


def get_reporting_date_by_gap(days: int) -> str:
    reporting_date = datetime.today() - timedelta(days=days)
    pattern = '%Y-%m-%d'
    return reporting_date.strftime(pattern)
