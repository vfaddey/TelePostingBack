import asyncio
from telebot.async_telebot import AsyncTeleBot

bot = AsyncTeleBot('6759802763:AAHFgRRSPBlgrhC735yJVB2IjB4pMu6CWCo')


async def get_bot_user_id():
    bot_info = await bot.get_me()
    print(f"Bot ID: {bot_info.id}")
    return bot_info.id


async def main():
    await get_bot_user_id()

if __name__ == "__main__":
    asyncio.run(main())
