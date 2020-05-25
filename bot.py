# -*- coding: utf-8 -*-
import telebot
from module import Employee, EmployeesDB, EmployeeGoogleSheet, google_service, IncomeItemsGoogleSheet, PackingTrackerGoogleSheet
from loc_secrets import token, SAMPLE_SPREADSHEET_ID

bot = telebot.TeleBot(token)

PACKAGE_TYPES = ('Наклейка', 'Упаковка')
BOX_TYPES = ('Маленькая', 'Средняя', 'Большая')

start_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
start_keyboard.row('Список для упаковки', 'Записать упаковку')

package_type_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
package_type_keyboard.row(*PACKAGE_TYPES)

box_type_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
box_type_keyboard.row(*BOX_TYPES)

sheet = EmployeeGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
employees = EmployeesDB(sheet)
income_items = IncomeItemsGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
package_tracker = PackingTrackerGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)

users_package = dict()


@bot.message_handler(content_types=['text'])
def start_message(message):
    if message.text == '/start':
        user_id = message.from_user.id
        if not employees.is_employee_registered(user_id):
            bot.send_message(message.chat.id, 'Для новых сотрудников необходима регистрация. Введите своё имя:')
            bot.register_next_step_handler(message, register_employee)
        else:
            employee_name = employees.get_employee_name_by_id(user_id)
            bot.send_message(message.chat.id, "Здравствуйте," + str(employee_name), reply_markup=start_keyboard)
            bot.send_message(message.chat.id, "Выберите действие ниже.\n\nЕсли действия не отобразились, нажмите на "
                                              "иконку клавиатуры возле поля ввода", reply_markup=start_keyboard)
            bot.register_next_step_handler(message, action_choose)

    elif message.text == '/update':
        income_items.update_items_df()
        employees.update_employees()
        bot.send_message(message.chat.id, 'Данные артикулов и сотрудников обновлены')
    else:
        bot.send_message(message.chat.id, 'Я вас не понимаю. Для начала работы напишите /start')


def action_choose(message):
    message_text = message.text
    if message_text == 'Список для упаковки':
        bot.send_message(message.chat.id, 'Список того, что нужно упаковать:', reply_markup=start_keyboard)
        with open(income_items.get_income_items_file_name(), encoding='utf-8') as file:
            bot.send_document(message.chat.id, file)
        bot.register_next_step_handler(message, action_choose)
    elif message_text == 'Записать упаковку':
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
        users_package[message.from_user.id] = dict()
        users_package[message.from_user.id]['employee'] = employees.get_employee_name_by_id(message.from_user.id)
        users_package[message.from_user.id]['box_number'] = box_number
        bot.send_message(message.chat.id, 'Введите артикул:')
        bot.register_next_step_handler(message, get_package_art)


def get_package_art(message):
    global users_package
    art = message.text
    if not income_items.is_art_exists(art):
        bot.send_message(message.chat.id, 'Данного артикула нет в списке. Используйте существующий.')
        with open(income_items.get_income_items_file_name()) as file:
            bot.send_document(message.chat.id, file)
        bot.register_next_step_handler(message, get_package_art)
    else:
        users_package[message.from_user.id]['art'] = art
        bot.send_message(message.chat.id, 'Выберите тип упаковки:', reply_markup=package_type_keyboard)
        bot.register_next_step_handler(message, get_package_type)


def get_package_type(message):
    global users_package
    package_type = message.text
    if package_type in PACKAGE_TYPES:
        users_package[message.from_user.id]['package_type'] = package_type
        bot.send_message(message.chat.id, 'Выберите тип коробки:', reply_markup=box_type_keyboard)
        bot.register_next_step_handler(message, get_box_type)
    else:
        bot.send_message(message.chat.id, 'Неправильный тип упаковки', reply_markup=package_type_keyboard)
        bot.register_next_step_handler(message, get_package_type)


def get_box_type(message):
    global users_package
    box_type = message.text
    if box_type in BOX_TYPES:
        users_package[message.from_user.id]['box_type'] = box_type
        bot.send_message(message.chat.id, 'Введите количество:')
        bot.register_next_step_handler(message, get_package_count)
    else:
        bot.send_message(message.chat.id, 'Неправильный тип коробки, выберите из предложенных',
                         reply_markup=box_type_keyboard)
        bot.register_next_step_handler(message, get_box_type)


def get_package_count(message):
    global users_package
    count = None
    try:
        count = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'Значение должно быть числом, введите количество товара:')
        bot.register_next_step_handler(message, get_package_count)
    if count is not None:
        users_package[message.from_user.id]['count'] = count
        package_tracker.mark_packing_done(users_package[message.from_user.id])
        bot.send_message(message.chat.id, "Упаковка успешно записана")
        bot.send_message(message.chat.id,
                         "Информация об упаковке:\n" + str(get_employee_package_info(int(message.from_user.id))))


def get_employee_package_info(employee_id):
    global users_package
    result = ""
    for key, value in users_package[employee_id].items():
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


bot.polling(none_stop=True, interval=0)
