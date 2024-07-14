from telebot.async_telebot import AsyncTeleBot
from telebot.apihelper import ApiTelegramException
import multiprocessing
import asyncio


class BotManager:
    def __init__(self, users_collection):
        self.bots: dict[str, AsyncTeleBot] = {}
        self.processes = {}
        self.terminate_flags = {}
        self.users_collection = users_collection
        asyncio.create_task(self.load_all_bots())

    async def add_bot(self, api_key: str):
        if api_key not in self.bots:
            if await self._check_bot(api_key):
                bot = AsyncTeleBot(api_key)
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
            # await bot.remove_webhook()
            # await bot.stop_polling()

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
        bot = AsyncTeleBot(api_key)
        setup_handlers(bot)

        async def polling():
            while not terminate_flag.is_set():
                try:
                    await bot.infinity_polling()
                except Exception as e:
                    print(f"Exception occurred: {e}")
                    await bot.stop_polling()
                    break

        asyncio.run(polling())


    async def load_all_bots(self):
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
                        await self.add_bot(bot['api_token'])

    def get_bot(self, api_key) -> AsyncTeleBot:
        return self.bots.get(api_key, None)

    async def _check_bot(self, api_key):
        try:
            bot = AsyncTeleBot(api_key)
            await bot.get_me()
            return True
        except ApiTelegramException:
            return False


def setup_handlers(bot: AsyncTeleBot):
    @bot.message_handler(commands=['start'])
    async def send_welcome(message):
        await bot.reply_to(message, "Welcome!")

    @bot.message_handler(func=lambda message: True)
    async def echo_all(message):
        await bot.reply_to(message, message.text)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('button'))
    async def handle_button_callback(call):
        answers = call.data.split('_')[1:]
        sub_text = answers[0]
        guest_text = answers[1]
        try:
            await bot.get_chat_member(call.message.chat.id, call.from_user.id)
            await bot.answer_callback_query(call.id, sub_text, show_alert=True)
        except ApiTelegramException:
            await bot.answer_callback_query(call.id, guest_text, show_alert=True)
        


class InvalidBotKeyException(Exception):
    pass


class BotAlreadyWorksException(Exception):
    pass