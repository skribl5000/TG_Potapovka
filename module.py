# -*- coding: utf-8 -*-
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import io
import re
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SAMPLE_SPREADSHEET_ID = '1fqgPpjMc6oR-0pTDWxkFHXMnG6rhBk9saPv6PhlkJUw'

CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                               ['https://www.googleapis.com/auth/spreadsheets',
                                                                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
google_service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)




class Employee:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class Packages:
    BOX_TYPES_ATTRS = ['box_type', 'box_number']

    def __init__(self):
        self.data = dict()

    def get_packing_info(self):
        pass

    def employee_has_package(self, employee_id):
        return True if employee_id in self.data else False

    def is_employee_box_info_empty(self, employee_id):
        if not self.employee_has_package(employee_id):
            return True
        for attr in self.BOX_TYPES_ATTRS:
            if self.data[employee_id].get(attr) is None:
                return True
        return False

    def clear_employee_box_info(self, employee_id):
        self.data[employee_id] = dict()


class GoogleSheet:
    def __init__(self, service, spread_id):
        self.service = service
        self.spread_id = spread_id

    def get_sheet_data(self,
                       range: str) -> list:
        return self.service.spreadsheets().values().get(
            spreadsheetId=self.spread_id,
            range=range,
            majorDimension='ROWS'
        ).execute().get('values', [])

    def append_rows(self,
                    range: str,
                    rows: list) -> None:
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spread_id,
            range=range,
            body={
                "majorDimension": "ROWS",
                "values": rows,
            },
            valueInputOption="USER_ENTERED"
        ).execute()


class EmployeeGoogleSheet(GoogleSheet):
    def __init__(self, service, spread_id):
        super().__init__(service, spread_id)
        self.service = service
        self.spread_id = spread_id

    def get_employees(self):
        values = self.get_sheet_data('Employees!A1:B10000')
        df = pd.DataFrame(data=values[1:], columns=values[0])
        df['ID'] = df['ID'].astype(int)
        return df.set_index('ID')['Name'].to_dict()

    def register_employee(self,
                          employee: Employee):
        employee_id = employee.id
        employee_name = employee.name
        self.append_rows('Employees!A2:B10000', [[employee_id, employee_name]])


class EmployeesDB:
    def __init__(self, sheet):
        self.employees = dict()
        self.sheet = sheet
        self.update_employees()

    def is_employee_registered(self, employee_id) -> bool:
        return True if employee_id in self.employees else False

    def register_employee(self, employee):
        self.sheet.register_employee(employee)
        self.update_employees()

    def update_employees(self):
        self.employees = self.sheet.get_employees()

    def get_employee_name_by_id(self, employee_id) -> str:
        return self.employees[employee_id]


class IncomeItemsGoogleSheet(GoogleSheet):
    def __init__(self, service, spread_id):
        super().__init__(service, spread_id)
        self.service = service
        self.spread_id = spread_id
        self.items_df = self.get_income_items()

    def get_income_items(self) -> pd.DataFrame:
        items = self.get_sheet_data('Prihod!A2:F1000')
        df = pd.DataFrame(data=items, columns=items[0])
        return df

    def update_items_df(self):
        self.items_df = self.get_income_items()

    def generate_income_items_list(self) -> str:
        df = self.items_df
        s_buf = io.StringIO()
        df = df[['Артикул', 'Наименование']]
        df.to_csv(s_buf, index=False, sep=' ')
        return s_buf.getvalue()

    def get_income_items_file_name(self) -> str:
        with open('temp.txt', 'w', encoding="utf-8") as f:
            f.write(self.generate_income_items_list())
        return 'temp.txt'

    def get_items_arts(self) -> set:
        return set(self.items_df['Артикул'])

    def is_art_exists(self, art) -> bool:
        return True if art in self.get_items_arts() else False


class PackingTrackerGoogleSheet(GoogleSheet):
    def __init__(self, service, spread_id):
        super().__init__(service, spread_id)
        self.service = service
        self.spread_id = spread_id

    def mark_packing_done(self,
                          packing_info: dict):
        rows = self._create_row_form_packing_dict(packing_info)
        self.append_rows('Sborka!A1:G1000', rows)

    @staticmethod
    def _create_row_form_packing_dict(packing_info: dict) -> list:
        rows = [[packing_info['box_number'], packing_info['art'], packing_info['employee'],
                 packing_info['package_type'], packing_info['box_type'], packing_info['count'],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                 ]]
        # TODO: new functional for date marking
        return rows

    @staticmethod
    def is_box_number_valid(box_number: str) -> bool:
        pattern = r'\d{6}/\d{1,2}'
        if re.fullmatch(pattern, box_number):
            return True
        return False


class AdminsManager(GoogleSheet):
    def __init__(self, service, spread_id, sheet_range):
        super().__init__(service, spread_id)
        self.service = service
        self.spread_id = spread_id
        self.sheet_range = sheet_range
        self.admin_chats = []

    def get_admin_chats(self):
        return self.admin_chats

    def get_admins_df(self):
        admins = self.get_sheet_data(self.sheet_range)
        df = pd.DataFrame(data=admins[1:], columns=admins[0])
        return df

    def _update_admins(self):
        df = self.get_admins_df()
        self.admin_chats = list(set(df['Chat']))

    def add_admin(self, admin_id, chat_id):
        self.append_rows(self.sheet_range, [[admin_id, chat_id]])
        self._update_admins()

    def alert_admins(self, tg_bot, alert_message):
        for chat in self.admin_chats:
            tg_bot.send_message(int(chat), alert_message)
