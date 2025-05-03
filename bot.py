#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This bot uses an inline keyboard to interact with the user.

Press Ctrl-C on the command line to stop the bot.
"""
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import yt_dlp
from hurry.filesize import size
from task import TaskData, DownloadTask

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# load env variables, passes silently if file is not existing
load_dotenv(dotenv_path='./bot.env')

BOT_TOKEN = os.getenv('BOT_TOKEN', None)

# error if there is no bot token set
if BOT_TOKEN is None:
    logger.error("BOT_TOKEN is not set, exiting.")
    exit(1)

# parse trusted user ids
TRUST_ANYBODY = 'anybody'
_TRUSTED_USER_IDS = os.getenv('TRUSTED_USER_IDS', '')
TRUSTED_USER_IDS = _TRUSTED_USER_IDS.split(',')
# trust anybody if unset
if TRUSTED_USER_IDS is [] or TRUSTED_USER_IDS == [""]:
    TRUSTED_USER_IDS = TRUST_ANYBODY
    logger.info("TRUSTED_USER_IDS was not set, bot will trust anybody.")

# Stages
OUTPUT, STORAGE, DOWNLOAD = range(3)

# Callback data
CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_OVERCAST = "overcast"
CALLBACK_GOOGLE_DRIVE = "drive"
CALLBACK_BEST_FORMAT = "best"
CALLBACK_SELECT_FORMAT = "select_format"
CALLBACK_ABORT = "abort"


def is_supported(url):
    """
    Checks whether the URL type is eligible for yt-dlp.\n
    Returns True or False.
    """
    try:
        with yt_dlp.YoutubeDL() as ydl:
            ydl.extract_info(url, download=False)
            return True
    except yt_dlp.utils.DownloadError:
        return False


def is_trusted(user_id):
    # convert to string if necessary
    if type(user_id) == int:
        user_id = str(user_id)

    if TRUSTED_USER_IDS == TRUST_ANYBODY:
        # bot trusts anybody
        return True

    # bot trusts only defined user ids
    return user_id in TRUSTED_USER_IDS


def whoami(update, context):
    # reply user
    user = update.message.from_user
    if is_trusted(user.id):
        update.message.reply_text(user.id)


def start(update, context):
    """
    Invoked on every user message to create an interactive inline conversation.
    """

    # Get user who sent the message
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info(
            "Ignoring request of untrusted user '%s' with id '%s'", user.first_name, user.id)
        logger.debug("I only trust these user ids: %s", str(TRUSTED_USER_IDS))
        return None
    # retrieve content of message
    message_text = update.message.text

    # also handle whoami command as plain string
    if message_text == "whoami":
        whoami(update, context)
        return ConversationHandler.END

    # update global URL object
    url = message_text

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
                InlineKeyboardButton(
                    "Select Format", callback_data=CALLBACK_SELECT_FORMAT),
                # TODO add abort button
                # InlineKeyboardButton("Abort", callback_data=CALLBACK_ABORT),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send message with text and appended InlineKeyboard
        update.message.reply_text(
            "Do you want me to download '%s' ?" % url, reply_markup=reply_markup)
        return OUTPUT
    else:
        logger.info("Invalid url requested: '%s'", url)
        update.message.reply_text("I can't download your request '%s' 😤" % url)
        ConversationHandler.END


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    """
    Creates an interactive button menu for the user.
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def select_source_format(update, context):
    """
    A stage asking the user for the source format to be downloaded.
    """
    logger.info("select_format")
    query = update.callback_query
    query.answer()
    # get formats
    url = context.user_data["url"]
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(url, download=False)
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


def select_output_format(update, context):
    """
    A stage asking the user for the desired output media format.
    """
    logger.info("output()")
    query = update.callback_query
    context.user_data[CALLBACK_SELECT_FORMAT] = query.data
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("MP4", callback_data=CALLBACK_MP4),
            InlineKeyboardButton("MP3", callback_data=CALLBACK_MP3),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Choose Output Format", reply_markup=reply_markup
    )
    return STORAGE


def select_storage(update, context):
    """
    A stage asking the user for the desired storage backend.
    """
    logger.info("storage()")
    query = update.callback_query
    context.user_data["output_format"] = query.data
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Google Drive", callback_data=CALLBACK_GOOGLE_DRIVE),
            # InlineKeyboardButton("Overcast", callback_data=CALLBACK_OVERCAST),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Choose Storage Backend", reply_markup=reply_markup
    )
    return DOWNLOAD


def download_media(update, context):
    """
    A stage downloading the media and uploading it to the selected storage backend.
    """
    logger.info("download()")
    query = update.callback_query
    # query.answer()
    # storage_backend = query.data
    # output_format = context.user_data["output_format"]
    # url = context.user_data["url"]
    # format_id = context.user_data.get(CALLBACK_SELECT_FORMAT, None)

    # # Build youtube-dl options
    # YT_DLP_OPTIONS = {
    #     'format': format_id if format_id else 'best',
    #     'outtmpl': '%(title)s.%(ext)s',
    #     'quiet': True,
    #     'no_warnings': True,
    #     'extract_audio': output_format == CALLBACK_MP3,
    #     'audio_format': 'mp3' if output_format == CALLBACK_MP3 else None,
    #     'postprocessors': [{
    #         'key': 'FFmpegExtractAudio',
    #         'preferredcodec': 'mp3',
    #         'preferredquality': '192',
    #     }] if output_format == CALLBACK_MP3 else [],
    # }

    # # Download media
    # try:
    #     with yt_dlp.YoutubeDL(YT_DLP_OPTIONS) as ydl:
    #         info = ydl.extract_info(url, download=True)
    #         filename = ydl.prepare_filename(info)
    #         if output_format == CALLBACK_MP3:
    #             filename = filename.rsplit('.', 1)[0] + '.mp3'

    #     # Upload to storage backend
    #     if storage_backend == CALLBACK_GOOGLE_DRIVE:
    #         google_drive.upload(filename)
    #         query.edit_message_text(
    #             text="Uploaded to Google Drive: %s" % filename)
    #     else:
    #         query.edit_message_text(
    #             text="Unknown storage backend: %s" % storage_backend)
    # except Exception as e:
    #     logger.error("Error downloading media: %s", str(e))
    #     query.edit_message_text(
    #         text="Error downloading media: %s" % str(e))
    selected_format = context.user_data[CALLBACK_SELECT_FORMAT]
    url = context.user_data["url"]
    storage = query.data
    query.edit_message_text(text=f"Thank you for your order!🧑‍🍳\nI will start cooking following recipe🧾\n\nurl: {url} \nstorage: {storage} \nformat: {selected_format}\n😋😋😋😋",disable_web_page_preview=True)
    data = TaskData(url, storage,selected_format,update)
    task = DownloadTask(data)
    task.downloadVideo()

    return ConversationHandler.END


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states OUTPUT, STORAGE and DOWNLOAD
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, start)],
        states={
            OUTPUT: [
                CallbackQueryHandler(select_source_format, pattern='^' + CALLBACK_SELECT_FORMAT + '$'),
                CallbackQueryHandler(select_output_format, pattern='^' + CALLBACK_BEST_FORMAT + '$'),
                CallbackQueryHandler(select_output_format, pattern='^[0-9]+$'),
            ],
            STORAGE: [
                CallbackQueryHandler(select_storage, pattern='^' + CALLBACK_MP3 + '$'),
                CallbackQueryHandler(select_storage, pattern='^' + CALLBACK_MP4 + '$'),
            ],
            DOWNLOAD: [
                CallbackQueryHandler(download_media, pattern='^' + CALLBACK_GOOGLE_DRIVE + '$'),
                CallbackQueryHandler(download_media, pattern='^' + CALLBACK_OVERCAST + '$'),
            ],
        },
        fallbacks=[CommandHandler('whoami', whoami)],
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
