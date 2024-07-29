from telebot.async_telebot import AsyncTeleBot
import asyncio
import multiprocessing


bot = AsyncTeleBot('6759802763:AAHFgRRSPBlgrhC735yJVB2IjB4pMu6CWCo')


@bot.message_handler(func=lambda message: True)
async def process(message):
    await bot.send_message(message.chat.id, message.text)


async def main():
    await bot.infinity_polling()


def run_bot():
    asyncio.run(main())


if __name__ == '__main__':
    process = multiprocessing.Process(target=run_bot)
    process.start()

