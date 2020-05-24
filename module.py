import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

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
        self._update_employees()

    def is_employee_registered(self, employee_id):
        return True if employee_id in self.employees else False

    def register_employee(self, employee):
        self.sheet.register_employee(employee)
        self._update_employees()

    def _update_employees(self):
        self.employees = self.sheet.get_employees()

    def get_employee_name_by_id(self, employee_id):
        return self.employees[employee_id]


class IncomeItemsGoogleSheet(GoogleSheet):
    def __init__(self, service, spread_id):
        super().__init__(service, spread_id)
        self.service = service
        self.spread_id = spread_id

    def get_income_items(self):
        items = self.get_sheet_data('Prihod!A1:F1000')
        df = pd.DataFrame(data=items[1:], columns=items[0])
        return df
