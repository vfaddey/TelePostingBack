from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
import multiprocessing


class BotManager:
    def __init__(self, users_collection):
        self.bots = {}
        self.processes = {}
        self.terminate_flags = {}
        self.users_collection = users_collection
        self.load_all_bots()

    def add_bot(self, api_key: str):
        if api_key not in self.bots:
            if self._check_bot(api_key):
                bot = TeleBot(api_key)
                self.bots[api_key] = bot

                terminate_flag = multiprocessing.Event()
                self.terminate_flags[api_key] = terminate_flag

                process = multiprocessing.Process(target=self.bot_polling_process, args=(api_key, terminate_flag))
                self.processes[api_key] = process
                process.start()
            else:
                raise InvalidBotKeyException('Неверный API ключ для бота')
        else:
            raise BotAlreadyWorksException('Такой бот уже работает')

    async def stop_bot(self, api_key):
        if api_key in self.bots:
            bot = self.bots[api_key]
            bot.remove_webhook()
            bot.stop_polling()

            self.terminate_flags[api_key].set()
            self.processes[api_key].terminate()
            self.processes[api_key].join()

            del self.processes[api_key]
            del self.terminate_flags[api_key]
            del self.bots[api_key]

            print(f"Bot with API key {api_key} has been stopped.")
        else:
            print(f"No bot found with API key {api_key}.")

    @staticmethod
    def bot_polling_process(api_key, terminate_flag):
        bot = TeleBot(api_key)
        setup_handlers(bot)

        while not terminate_flag.is_set():
            try:
                bot.polling(none_stop=True, timeout=60)
            except Exception as e:
                print(f"Exception occurred: {e}")
                bot.stop_polling()
                break


    def load_all_bots(self):
        result = self.users_collection.find({
            "bots": {
                "$elemMatch": {
                    "active": True
                }
            }
        })
        for user in result:
            if user['bots']:
                for bot in user['bots']:
                    if bot['active']:
                        self.add_bot(bot['api_token'])

    def get_bot(self, api_key):
        return self.bots.get(api_key, None)

    def _check_bot(self, api_key):
        try:
            bot = TeleBot(api_key)
            bot.get_me()
            return True
        except ApiTelegramException:
            return False


def setup_handlers(bot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "Welcome!")

    @bot.message_handler(func=lambda message: True)
    def echo_all(message):
        bot.reply_to(message, message.text)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('button'))
    def handle_button_callback(call):
        pass


class InvalidBotKeyException(Exception):
    pass


class BotAlreadyWorksException(Exception):
    pass