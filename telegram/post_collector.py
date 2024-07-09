from bson import ObjectId
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def prepare_markup(buttons: dict, post_id: ObjectId):
    markup = InlineKeyboardMarkup(row_width=2)
    for index, button in enumerate(buttons):
        if button['type'] == 'url':
            url_button = InlineKeyboardButton(button['text'], url=button['url'])
            markup.add(url_button)
        elif button['type'] == 'text':
            text_button = InlineKeyboardButton(button['text'], callback_data=f'button_{post_id}_{index}')
            markup.add(text_button)
    return markup
