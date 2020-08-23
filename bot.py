# -*- coding: utf-8 -*-

import telebot
from module import Employee, EmployeesDB, EmployeeGoogleSheet, IncomeItemsGoogleSheet, PackingTrackerGoogleSheet, \
    Packages, AdminsManager, Nomenklature

from loc_secrets import token, SAMPLE_SPREADSHEET_ID
import logging
import time
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

# token = test_token
# SAMPLE_SPREADSHEET_ID = test_SPREADSHEET_ID

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                               ['https://www.googleapis.com/auth/spreadsheets',
                                                                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
google_service = apiclient.discovery.build('sheets', 'v4', http=httpAuth, cache_discovery=False)

FORMAT = u"[%(asctime)s] %(levelname).1s %(message)s"
log_file = 'log.log'
logger = logging.getLogger(log_file)

bot = telebot.TeleBot(token)

PACKAGE_TYPES = ('Наклейка', 'Упаковка', 'Без маркировки')
BOX_TYPES = ('Маленькая', 'Средняя', 'Большая')

start_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
start_keyboard.row('Записать упаковку')

package_type_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
package_type_keyboard.row(*PACKAGE_TYPES)

box_type_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
box_type_keyboard.row(*BOX_TYPES)

sheet = EmployeeGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
employees = EmployeesDB(sheet)
income_items = IncomeItemsGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
package_tracker = PackingTrackerGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)

admins = AdminsManager(google_service, SAMPLE_SPREADSHEET_ID, 'Admins!A1:B1000')

finish_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
finish_keyboard.row('Продолжить текущий короб')
finish_keyboard.row('Начать новый короб')
finish_keyboard.row('Закончить работу')

accept_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
accept_keyboard.row(*('Да', 'Нет'))

items_mapping = {
    'Баркод': 'bar_code',
    'Размер товара': 'item_size',
    'Количество': 'count'
}

items_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
items_keyboard.row(*tuple(items_mapping.keys()))

users_package = Packages()

nom = Nomenklature(google_service, SAMPLE_SPREADSHEET_ID, 'Nomenclature!A2:T10000')


@bot.message_handler(content_types=['text'])
def start_message(message):
    user_id = message.from_user.id
    if not employees.is_employee_registered(user_id):
        bot.send_message(message.chat.id, 'Для новых сотрудников необходима регистрация. Введите своё имя:')
        bot.register_next_step_handler(message, register_employee)
        return
    employee_name = employees.get_employee_name_by_id(user_id)
    if message.text == '/start':
        bot.send_message(message.chat.id, "Здравствуйте," + str(employee_name), reply_markup=start_keyboard)
        bot.send_message(message.chat.id, "Выберите действие ниже.\n\nЕсли действия не отобразились, нажмите на "
                                          "иконку клавиатуры возле поля ввода", reply_markup=start_keyboard)
        admins.alert_admins(bot, str(employee_name) + ' приступает к работе.')
        bot.register_next_step_handler(message, action_choose)

    elif message.text == '/update':
        income_items.update_items_df()
        employees.update_employees()
        bot.send_message(message.chat.id, 'Данные артикулов и сотрудников обновлены')

    elif message.text == '/update_barcodes':
        nom.update_nomenklature()
        nom.update_map()
        bot.send_message(message.chat.id, 'Данные номенклатуры обновлены')

    elif message.text == '/new_admin':
        admins.add_admin(user_id, message.chat.id)
        bot.send_message(message.chat.id,
                         str(employee_name) + ', данный чат зарегистрирован как чат с администратором.')
    else:
        bot.send_message(message.chat.id, 'Я вас не понимаю. Для начала работы напишите /start')


def action_choose(message):
    message_text = message.text
    users_package.clear_employee_box_info(message.from_user.id)
    # if message_text == 'Список для упаковки':
    #     bot.send_message(message.chat.id, 'Список того, что нужно упаковать:', reply_markup=start_keyboard)
    #     with open(income_items.get_income_items_file_name(), encoding='utf-8') as file:
    #         bot.send_document(message.chat.id, file)
    #     bot.register_next_step_handler(message, action_choose)
    if message_text == 'Записать упаковку':
        bot.send_message(message.chat.id, 'Введите номер короба:')
        bot.register_next_step_handler(message, get_box_number)
    else:
        bot.send_message(message.chat.id, 'Неизвествная команда, выберите действие из предложенных:',
                         reply_markup=start_keyboard)
        bot.register_next_step_handler(message, action_choose)


def get_box_number(message):
    global users_package
    box_number = message.text
    if not package_tracker.is_box_number_valid(box_number):
        bot.send_message(message.chat.id, "Номер короба должен быть в формате ******/**."
                                          " \nВведите правильный номер короба:")
        bot.register_next_step_handler(message, get_box_number)
    else:
        users_package.data[message.from_user.id] = dict()
        users_package.data[message.from_user.id]['employee'] = employees.get_employee_name_by_id(message.from_user.id)
        users_package.data[message.from_user.id]['box_number'] = box_number

        bot.send_message(message.chat.id, 'Выберите размер коробки:', reply_markup=box_type_keyboard)
        bot.register_next_step_handler(message, get_box_type)


def get_box_type(message):
    global users_package
    box_type = message.text
    if box_type in BOX_TYPES:
        users_package.data[message.from_user.id]['box_type'] = box_type
        bot.send_message(message.chat.id, 'Введите баркод:')
        bot.register_next_step_handler(message, get_package_bar_code)
    else:
        bot.send_message(message.chat.id, 'Неправильный размер коробки, выберите из предложенных',
                         reply_markup=box_type_keyboard)
        bot.register_next_step_handler(message, get_box_type)


def get_package_bar_code(message):
    global users_package
    bar_code = message.text
    if package_tracker.is_bar_code_valid(bar_code):
        item_title = nom.get_item_title(bar_code)
        if item_title is not None:
            users_package.data[message.from_user.id]['bar_code'] = bar_code

            bot.send_message(message.chat.id, f'Вы упаковываете {item_title} ?', reply_markup=accept_keyboard)
            bot.register_next_step_handler(message, accept_bar_code)
        else:
            bot.send_message(message.chat.id, "Такой баркод не зарегистрирован. Введите корректный.")
            bot.register_next_step_handler(message, get_package_bar_code)
    else:
        bot.send_message(message.chat.id, "Баркод состоит из 13 цифр. Введите корректный баркод.")
        bot.register_next_step_handler(message, get_package_bar_code)


def accept_bar_code(message):
    global users_package
    choice = message.text
    if choice == 'Да':
        bot.send_message(message.chat.id, "Выберите тип упаковки:", reply_markup=package_type_keyboard)
        bot.register_next_step_handler(message, get_package_type)
    elif choice == 'Нет':
        bot.send_message(message.chat.id, "Введите баркод ещё раз.", reply_markup=items_keyboard)
        bot.register_next_step_handler(message, get_package_bar_code)
    else:
        bot.send_message(message.chat.id, "Правильный ли был введен баркод?", reply_markup=items_keyboard)
        bot.register_next_step_handler(message, accept_bar_code)


def get_package_type(message):
    global users_package
    package_type = message.text
    if package_type in PACKAGE_TYPES:
        users_package.data[message.from_user.id]['package_type'] = package_type
        bot.send_message(message.chat.id, 'Введите количество:')
        bot.register_next_step_handler(message, get_package_count)
    else:
        bot.send_message(message.chat.id, 'Неправильный тип упаковки', reply_markup=package_type_keyboard)
        bot.register_next_step_handler(message, get_package_type)


def get_package_count(message):
    global users_package
    count = None
    try:
        count = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'Значение должно быть числом, введите количество товара:')
        bot.register_next_step_handler(message, get_package_count)
    if count is not None:
        users_package.data[message.from_user.id]['count'] = count
        bot.send_message(message.chat.id,
                         "Информация об упаковке:\n" + str(get_employee_package_info(int(message.from_user.id))))
        bot.send_message(message.chat.id, "Всё ли верно?", reply_markup=accept_keyboard)
        bot.register_next_step_handler(message, accept_package)


def accept_package(message):
    global users_package
    choice = message.text
    if choice == 'Да':
        package_tracker.mark_packing_done(users_package.data[message.from_user.id])
        bot.send_message(message.chat.id, "Упаковка успешно записана.")
        bot.send_message(message.chat.id, "Выберите следующее действие:", reply_markup=finish_keyboard)
        bot.register_next_step_handler(message, finish_step)
    else:
        bot.send_message(message.chat.id, "Что нужно изменить?", reply_markup=items_keyboard)
        bot.register_next_step_handler(message, change_smth)


def change_smth(message):
    global users_package
    item = message.text
    users_package.data[message.from_user.id]['to_change'] = item
    if item not in items_mapping:
        bot.send_message(message.chat.id, "Нужно выбрать из предложенного:", reply_markup=items_keyboard)
    else:
        bot.send_message(message.chat.id, "Введите новое значение для " + str(item))
        bot.register_next_step_handler(message, change_value)


def change_value(message):
    global users_package
    global items_mapping
    value = message.text
    users_package.data[message.from_user.id][items_mapping[users_package.data[message.from_user.id]['to_change']]] = value

    bot.send_message(message.chat.id,
                     "Информация об упаковке:\n" + str(get_employee_package_info(int(message.from_user.id))))
    bot.send_message(message.chat.id, "Теперь всё верно?", reply_markup=accept_keyboard)
    bot.register_next_step_handler(message, accept_package)


def finish_step(message):
    message_text = message.text
    if message_text == 'Закончить работу':
        bot.send_message(message.chat.id, 'Работа завершена. Для начала введите /start')
        admins.alert_admins(bot, employees.get_employee_name_by_id(message.from_user.id) + ' закончил(а) работу.')
    elif message_text == 'Продолжить текущий короб':
        bot.send_message(message.chat.id, 'Введите артикул:')
        bot.register_next_step_handler(message, get_package_bar_code)
    elif message_text == 'Начать новый короб':
        admins.alert_admins(bot, employees.get_employee_name_by_id(message.from_user.id) + ' упаковал(а) коробку.')
        bot.send_message(message.chat.id, 'Введите номер следующего короба:')
        bot.register_next_step_handler(message, get_box_number)
    else:
        bot.send_message(message.chat.id, 'Я вас не понимаю. Выберите действие из предложенных.')


def get_employee_package_info(employee_id):
    global users_package
    result = ""
    for key, value in users_package.data[employee_id].items():
        if key == 'to_change':
            continue
        result += str(value) + "\n"
    return result


def register_employee(message):
    """
    Employee Registration using telegram account id.
    """
    employee_name = message.text
    employee_id = message.from_user.id
    employee = Employee(employee_id, employee_name)

    employees.register_employee(employee)
    bot.send_message(message.chat.id, "Добро пожаловать," + str(employee_name) + ". Теперь вы можете выбрать действие" +
                     "\n\nЕсли действия не отобразились, нажмите на " +
                     "иконку клавиатуры возле поля ввода",
                     reply_markup=start_keyboard)
    bot.register_next_step_handler(message, action_choose)


try:
    print('Production bot starts...')
    bot.polling(none_stop=True, interval=0)
except Exception as e:
    time.sleep(20)

    with open('LOG.txt', 'w+') as f:
        f.write(str(e))
