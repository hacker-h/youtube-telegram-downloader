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

# Check for default output format
DEFAULT_OUTPUT_FORMAT = os.getenv('DEFAULT_OUTPUT_FORMAT', '').lower()
if DEFAULT_OUTPUT_FORMAT:
    logger.info(f"DEFAULT_OUTPUT_FORMAT is set to: {DEFAULT_OUTPUT_FORMAT}")
    if DEFAULT_OUTPUT_FORMAT not in ['mp3', 'mp4']:
        logger.warning(f"Invalid DEFAULT_OUTPUT_FORMAT '{DEFAULT_OUTPUT_FORMAT}', must be 'mp3' or 'mp4'. Ignoring.")
        DEFAULT_OUTPUT_FORMAT = ''

# Stages - removed STORAGE stage since we only have local storage
OUTPUT, DOWNLOAD = range(2)

# Callback data
CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_LOCAL = "local"
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
    
    if is_supported(url):
        # If DEFAULT_OUTPUT_FORMAT is set, start downloading immediately
        if DEFAULT_OUTPUT_FORMAT:
            logger.info(f"Auto-downloading with default format: {DEFAULT_OUTPUT_FORMAT}")
            
            # Start download immediately with best format and default output
            # The DownloadTask will handle all progress messaging
            data = TaskData(url, CALLBACK_LOCAL, CALLBACK_BEST_FORMAT, update, DEFAULT_OUTPUT_FORMAT)
            task = DownloadTask(data)
            task.downloadVideo()
            return ConversationHandler.END
        else:
            # Show normal format selection if no default is configured
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
    If DEFAULT_OUTPUT_FORMAT is set, skip this and go directly to download.
    """
    logger.info("output()")
    query = update.callback_query
    context.user_data[CALLBACK_SELECT_FORMAT] = query.data
    query.answer()
    
    # Check if default output format is configured
    if DEFAULT_OUTPUT_FORMAT:
        logger.info(f"Using default output format: {DEFAULT_OUTPUT_FORMAT}")
        # Go directly to download with the default format
        return download_media_with_default_format(update, context)
    
    # Show format selection if no default is set
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
    return DOWNLOAD


def download_media_with_default_format(update, context):
    """
    Download media using the default output format (when DEFAULT_OUTPUT_FORMAT is set).
    """
    logger.info("download() with default format")
    selected_format = context.user_data[CALLBACK_SELECT_FORMAT]
    url = context.user_data["url"]
    output_format = DEFAULT_OUTPUT_FORMAT
    
    query = update.callback_query
    query.edit_message_text(text=f"Thank you for your order!🧑‍🍳\nI will start cooking following recipe🧾\n\nurl: {url} \nformat: {selected_format}\noutput: {output_format}\n😋😋😋😋",disable_web_page_preview=True)
    
    # Always use local storage now, pass output_format to TaskData
    data = TaskData(url, CALLBACK_LOCAL, selected_format, update, output_format)
    task = DownloadTask(data)
    task.downloadVideo()

    return ConversationHandler.END


def download_media(update, context):
    """
    A stage downloading the media and saving it to local storage.
    """
    logger.info("download()")
    query = update.callback_query
    selected_format = context.user_data[CALLBACK_SELECT_FORMAT]
    url = context.user_data["url"]
    output_format = query.data
    
    query.edit_message_text(text=f"Thank you for your order!🧑‍🍳\nI will start cooking following recipe🧾\n\nurl: {url} \nformat: {selected_format}\noutput: {output_format}\n😋😋😋😋",disable_web_page_preview=True)
    
    # Always use local storage now, pass output_format to TaskData
    data = TaskData(url, CALLBACK_LOCAL, selected_format, update, output_format)
    task = DownloadTask(data)
    task.downloadVideo()

    return ConversationHandler.END


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with simplified states (OUTPUT and DOWNLOAD only)
    # If DEFAULT_OUTPUT_FORMAT is set, we might skip the DOWNLOAD state for manual selection
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, start)],
        states={
            OUTPUT: [
                CallbackQueryHandler(select_source_format, pattern='^' + CALLBACK_SELECT_FORMAT + '$'),
                CallbackQueryHandler(select_output_format, pattern='^' + CALLBACK_BEST_FORMAT + '$'),
                CallbackQueryHandler(select_output_format, pattern='^[0-9]+$'),
            ],
            DOWNLOAD: [
                CallbackQueryHandler(download_media, pattern='^' + CALLBACK_MP3 + '$'),
                CallbackQueryHandler(download_media, pattern='^' + CALLBACK_MP4 + '$'),
            ],
        },
        fallbacks=[CommandHandler('whoami', whoami)],
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABORT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
