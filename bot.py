#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This Bot uses the Updater class to handle the bot.
First, a few callback functions are defined as callback query handler. Then, those functions are
passed to the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot that uses inline keyboard that has multiple CallbackQueryHandlers arranged in a
ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line to stop the bot.
"""
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import youtube_dl
from hurry.filesize import size
from backends import google_drive

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# load env variables, passes silently if file is not existing
load_dotenv(dotenv_path='./bot.env')

BOT_TOKEN = os.getenv('BOT_TOKEN', None)

# error if there is no bot token passed
if BOT_TOKEN is None:
    logger.error("BOT_TOKEN is not set, exiting.")
    exit(1)

# TODO code cleanup!

# Stages
OUTPUT, STORAGE, DOWNLOAD = range(3)

# Callback data
CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_OVERCAST = "overcast"
CALLBACK_GOOGLE_DRIVE = "drive"
CALLBACK_BEST_FORMAT = "best"
CALLBACK_SELECT_FORMAT = "select_format"


def is_supported(url):
    extractors = youtube_dl.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True
    return False


def start(update, context):
    """Send message on `/start`."""

    # Get user that sent /start and log his name
    user = update.message.from_user

    # update global URL object
    url = update.message.text

    # save url to user context
    context.user_data["url"] = url
    logger.info("User %s started the conversation with '%s'.",
                user.first_name, url)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).
    if is_supported(url):
        keyboard = [
            [
                InlineKeyboardButton(
                    "Download Best Format", callback_data=CALLBACK_BEST_FORMAT),
                InlineKeyboardButton("Select Format", callback_data=CALLBACK_SELECT_FORMAT),
                # InlineKeyboardButton("Abort", callback_data=str(ONE)),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send message with text and appended InlineKeyboard
        update.message.reply_text(
            "Do you want me to download '%s' ?" % url, reply_markup=reply_markup)
        return OUTPUT
    else:
        update.message.reply_text("I can't download your request '%s' 😤" % url)
        ConversationHandler.END


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def selectFormat(update, context):
    """Show new choice of buttons"""
    logger.info("selectFormat")
    query = update.callback_query
    query.answer()
    # get formats
    url = context.user_data["url"]
    ydl_opts = {}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(
            url, download=False)
        formats = meta.get('formats', [meta])

    # dynamically build a format menu
    formats = sorted(formats, key=lambda k: k['ext'])
    button_list = []
    button_list.append(InlineKeyboardButton(
        "Best Quality", callback_data=CALLBACK_BEST_FORMAT))
    for f in formats:
        # {'format_id': '243', 'url': '...', 'player_url': '...', 'ext': 'webm', 'height': 266, 'format_note': '360p',
        # 'vcodec': 'vp9', 'asr': None, 'filesize': 2663114, 'fps': 24, 'tbr': 267.658, 'width': 640, 'acodec': 'none',
        # 'downloader_options': {'http_chunk_size': 10485760}, 'format': '243 - 640x266 (360p)', 'protocol': 'https',
        # 'http_headers': {'User-Agent': '...',
        # 'Accept-Charset': '...', 'Accept': '...',
        # 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en-us,en;q=0.5'}}
        format_text = f"{f['format_note']}, {f['height']}x{f['width']}, type: {f['ext']}, fps: {f['fps']}, {size(f['filesize']) if f['filesize'] else 'None'}"
        button_list.append(InlineKeyboardButton(
            format_text, callback_data=f['format_id']))
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))

    query.edit_message_text(
        text="Choose Format", reply_markup=reply_markup
    )
    return OUTPUT


def output(update, context):
    """Show new choice of buttons"""
    logger.info("output()")
    query = update.callback_query
    context.user_data[CALLBACK_SELECT_FORMAT] = query.data
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Audio", callback_data=CALLBACK_MP3),
            InlineKeyboardButton("Video", callback_data=CALLBACK_MP4),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Do you want the full video or just audio?", reply_markup=reply_markup
    )
    return STORAGE


def storage(update, context):
    """Show new choice of buttons"""
    logger.info("storage()")
    query = update.callback_query
    context.user_data["output"] = query.data
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton(
                "Google Drive", callback_data=CALLBACK_GOOGLE_DRIVE),
            InlineKeyboardButton("Overcast", callback_data=CALLBACK_OVERCAST),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Where shall I upload the file?", reply_markup=reply_markup
    )
    return DOWNLOAD


def download(update, context):
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over"""
    query = update.callback_query
    context.user_data["storage"] = query.data
    # print all settings
    # query.edit_message_text(text=context.user_data)
    query.edit_message_text(text="Downloading..")
    url = context.user_data["url"]
    selected_format = context.user_data[CALLBACK_SELECT_FORMAT]
    logger.info(url)
    # get url from context
    # some default configurations for video downloads
    MP3_EXTENSION = 'mp3'
    YOUTUBE_DL_OPTIONS = {
        'format': selected_format,
        'restrictfilenames': True,
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': MP3_EXTENSION,
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(YOUTUBE_DL_OPTIONS) as ydl:
        result = ydl.extract_info("{}".format(url))
        original_video_name = ydl.prepare_filename(result)

    raw_media_name = os.path.splitext(original_video_name)[0]
    final_media_name = "%s.%s" % (raw_media_name, MP3_EXTENSION)

    # upload the file
    backend_name = context.user_data["storage"]
    backend = None
    if backend_name == CALLBACK_GOOGLE_DRIVE:
        backend = google_drive.GoogleDriveStorage()
    elif backend_name == CALLBACK_OVERCAST:
        raise NotImplementedError
    else:
        logger.error("Invalid backend '%s'", backend)

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Uploading..")

    print(final_media_name)
    backend.upload(final_media_name)

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Done!")
    return ConversationHandler.END


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=BOT_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific

    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, start)],
        states={

            OUTPUT: [
                CallbackQueryHandler(
                    selectFormat, pattern="^%s$"%CALLBACK_SELECT_FORMAT),
                CallbackQueryHandler(output),
            ],
            STORAGE: [
                CallbackQueryHandler(storage)
            ],
            DOWNLOAD: [
                CallbackQueryHandler(download),
            ]
        },
        allow_reentry=False,
        per_user=True,
        fallbacks=[CommandHandler('start', start)],
    )

    # Add ConversationHandler to dispatcher that will be used for handling
    # updates
    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
