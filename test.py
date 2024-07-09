from telebot import TeleBot

bot = TeleBot('6759802763:AAHFgRRSPBlgrhC735yJVB2IjB4pMu6CWCo')

print(bot.get_chat_member(chat_id='@opened_business', user_id=bot.user.id))
