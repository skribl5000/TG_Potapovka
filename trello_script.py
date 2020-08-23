from trello import TrelloClient, List
from trello_creds import tr_api_key, tr_token
from datetime import datetime
import logging

logging.basicConfig(level=logging.ERROR, filename='trello_update.log')

current_datetime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')


class TrelloListManager(List):
    def __init__(self, board, list_id):
        super().__init__(board, list_id)

    def add_new_nom_task(self, num_row, brand_dict={}):
        card_title = num_row['Наименование']
        size = num_row['Размер на бирке']
        color = num_row['Цвет']
        if size != '0':
            card_title += f' {size} '
        if color is not None:
            card_title += color
        description = brand_dict.get(row_nom['Бренд'], '')
        return self.add_card(card_title, desc=description)


trello_client = TrelloClient(
    api_key=tr_api_key,
    token=tr_token
)
pictures_board = trello_client.get_board('5f420a5bd42301124a8c69aa')
start_list = TrelloListManager(pictures_board, '5f420a5bd42301124a8c69ab')

from module import GoogleSheet, Nomenklature, BrandDescription
from loc_secrets import token, SAMPLE_SPREADSHEET_ID

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                               ['https://www.googleapis.com/auth/spreadsheets',
                                                                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
google_service = apiclient.discovery.build('sheets', 'v4', http=httpAuth, cache_discovery=False)
nomenclature = Nomenklature(google_service, SAMPLE_SPREADSHEET_ID, 'Nomenclature!A2:T10000')
nom_history = Nomenklature(google_service, SAMPLE_SPREADSHEET_ID, 'Nom_History!A1:B10000')
brand_instructions = BrandDescription(google_service, SAMPLE_SPREADSHEET_ID, 'Instructions!A1:T1000')

df_nom = nomenclature.get_df()
df_nom['Key'] = df_nom['Артикул поставщика'] + '_' + df_nom['Артикул цвета']
df_nom_prev = nom_history.get_df()

df_new_nom_items = df_nom[~df_nom['Key'].isin(df_nom_prev['Key'])]
brand_dict = brand_instructions.get_brand_description_mapping()

for index, row_nom in df_new_nom_items.iterrows():
    new_card = start_list.add_new_nom_task(row_nom, brand_dict)
    try:
        nom_history.append_rows('Nom_History!A1:B10000', [[row_nom['Key'], current_datetime]])
    except Exception as e:
        logging.error(new_card.name + ' - ' + str(e))
        new_card.delete()
