import telebot
from module import Employee, EmployeesDB, EmployeeGoogleSheet, google_service
from loc_secrets import token, SAMPLE_SPREADSHEET_ID


bot = telebot.TeleBot(token)

start_keyboard = telebot.types.ReplyKeyboardMarkup()
start_keyboard.row('Список для упаковки', 'Записать упаковку')

sheet = EmployeeGoogleSheet(google_service, SAMPLE_SPREADSHEET_ID)
employees = EmployeesDB(sheet)


@bot.message_handler(content_types=['text'])
def start_message(message):
    print(message)
    if message.text == '/start':
        user_id = message.from_user.id
        if not employees.is_employee_registered(user_id):
            bot.send_message(message.chat.id, 'Для новых сотрудников необходима регистрация. Введите своё имя:')
            bot.register_next_step_handler(message, register_employee)
        else:
            employee_name = employees.get_employee_name_by_id(user_id)
            bot.send_message(message.chat.id, f'Здравствуйте, {employee_name}', reply_markup=start_keyboard)
            bot.send_message(message.chat.id, "Выберите действие ниже.\n\nЕсли действия не отобразились, нажмите на "
                                              "иконку клавиатуры возле поля ввода", reply_markup=start_keyboard)
            bot.register_next_step_handler(message, action_choose)
    else:
        bot.send_message(message.chat.id, 'Я вас не понимаю. Для начала работы напишите /start')


def action_choose(message):
    message_text = message.text
    if message_text == 'Список для упаковки':
        bot.send_message(message.chat.id, 'Тут будет список того, что нужно упаковать')
        bot.register_next_step_handler(message, action_choose)
    elif message_text == 'Записать упаковку':
        bot.send_message(message.chat.id, 'Тут будет порядок действий для заметки об упаковке')
        bot.register_next_step_handler(message, mark_packing_done)
    else:
        bot.send_message(message.chat.id, 'Неизвествная команда, выберите действие из предложенных:',
                         reply_markup=start_keyboard)


def mark_packing_done(message):
    """
    function for marking work results
    """
    pass


def register_employee(message):
    """
    Employee Registration using telegram account id.
    """
    employee_name = message.text
    employee_id = message.from_user.id
    employee = Employee(employee_id, employee_name)

    employees.register_employee(employee)
    bot.send_message(message.chat.id, f'Добро пожаловать, {employee_name}. Теперь вы можете выбрать действие',
                     reply_markup=start_keyboard)
    bot.register_next_step_handler(message, action_choose)


bot.polling(none_stop=True, interval=0)
