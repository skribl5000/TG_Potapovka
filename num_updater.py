from wb_creds import spec_token
from wildberries import SpecificationManager
from loc_secrets import SAMPLE_SPREADSHEET_ID


from module import GoogleSheet
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from wb_creds import wb_token, wb_token_64, sheet_id
import pandas as pd
from datetime import datetime

manager = SpecificationManager(spec_token)
df_nom = manager.get_nomenclature()

print(df_nom)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                               ['https://www.googleapis.com/auth/spreadsheets',
                                                                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
google_service = apiclient.discovery.build('sheets', 'v4', http=httpAuth, cache_discovery=False)

sheet = GoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
sheet.clear_and_upload_sheet_df('Nomenclature!A2:T10000', df_nom)

reporting_actual_on = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
sheet.put_value_to_cell('Nomenclature!B1:B1', [reporting_actual_on])
