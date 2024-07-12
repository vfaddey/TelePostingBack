import threading

import telebot
from telebot.apihelper import ApiTelegramException
from motor.motor_asyncio import AsyncIOMotorCollection


class BotManager:
    def __init__(self):
        self.bots = {}
        self.threads = {}
        self.users_tokens = {}

    async def add_bot(self, api_key: str):
        if api_key not in self.bots:
            if self._check_bot(api_key):
                bot = telebot.TeleBot(api_key)
                self.bots[api_key] = bot
                thread = threading.Thread(target=self._start_bot, args=(bot,))
                self.threads[api_key] = thread
                thread.start()
            else:
                raise InvalidBotKeyException('Неверный API ключ для бота')
        else:
            raise BotAlreadyWorksException('Такой бот уже работает')

    async def stop_bot(self, api_key):
        bot = self.get_bot(api_key)
        if bot:
            bot.stop_polling()
            del self.bots[api_key]
            await self.threads[api_key].join()
            del self.threads[api_key]
            print(f"Bot with API key {api_key} has been stopped.")
        else:
            print(f"No bot found with API key {api_key}.")


    def get_bot(self, api_key):
        return self.bots.get(api_key, None)
    
    async def load_all_bots(self, users_collection: AsyncIOMotorCollection):
        result = await users_collection.find( {
                                                        "bots": {
                                                            "$elemMatch": {
                                                                "active": True
                                                            }
                                                        }
                                                    }
                                                    )
        for user in result:
            if user['bots']:
                for bot in user['bots']:
                    if bot['active']:
                        await self.add_bot(bot['api_token'])
        

    def _check_bot(self, api_key):
        try:
            bot = telebot.TeleBot(api_key)
            bot.get_me()
            return True
        except ApiTelegramException:
            return False

    async def _start_bot(self, bot):
        setup_handlers(bot)
        bot.polling()


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


bot_manager = BotManager()
