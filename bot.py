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
        # First check for obvious incomplete URLs
        if 'youtube.com/watch?v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
            if not video_id or video_id in ['VIDEO_ID', 'VIDEOID', 'your_video_id', 'example']:
                logger.info(f"Detected placeholder or empty video ID: '{video_id}'")
                return False
        
        # Check for incomplete YouTube URLs without video ID
        if url.endswith('youtube.com/watch?v') or url.endswith('youtube.com/watch?v='):
            logger.info("Detected incomplete YouTube URL without video ID")
            return False
        
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check if yt-dlp redirected to YouTube recommended (unwanted)
            if info and info.get('id') == 'recommended':
                logger.info("URL redirected to YouTube recommended page - treating as invalid")
                return False
            
            # Check if we got a playlist when we expected a single video
            if info and info.get('_type') == 'playlist':
                entries = info.get('entries', [])
                if not entries or len(entries) == 0:
                    logger.info("URL points to empty playlist - treating as invalid")
                    return False
            
            return True
    except yt_dlp.utils.DownloadError as e:
        logger.info(f"yt-dlp DownloadError for URL '{url}': {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error checking URL '{url}': {e}")
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


def ls_command(update, context):
    """List all media files in the storage directory"""
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info("Ignoring ls request from untrusted user '%s' with id '%s'", user.first_name, user.id)
        return
    
    try:
        storage_dir = os.getenv('LOCAL_STORAGE_DIR', './data')
        # Convert relative path to absolute path for directory listing
        if storage_dir.startswith('./'):
            storage_dir = '/home/bot/' + storage_dir[2:]
        
        if not os.path.exists(storage_dir):
            update.message.reply_text(f"📁 Storage directory not found: {storage_dir}")
            return
        
        # Get all media files
        media_extensions = {'.mp3', '.mp4', '.wav', '.flac', '.avi', '.mkv', '.webm', '.m4a', '.ogg'}
        media_files = []
        
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in media_extensions):
                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                    size_str = size(file_size)
                except:
                    size_str = "Unknown"
                
                media_files.append({
                    'name': filename,
                    'size': size_str,
                    'path': file_path
                })
        
        # Sort alphabetically by filename
        media_files.sort(key=lambda x: x['name'].lower())
        
        if not media_files:
            update.message.reply_text(f"📁 No media files found in: {storage_dir}")
            return
        
        # Format the list
        file_list = f"📁 **Media Files** ({len(media_files)} files)\n"
        file_list += f"📂 Location: `{storage_dir}`\n\n"
        
        for i, file_info in enumerate(media_files, 1):
            # Determine emoji based on file extension
            name = file_info['name']
            if name.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg')):
                emoji = "🎵"
            else:
                emoji = "🎬"
            
            file_list += f"{i:2d}. {emoji} `{name}`\n"
            file_list += f"     📊 Size: {file_info['size']}\n\n"
        
        # Split message if too long for Telegram
        max_length = 4000
        if len(file_list) > max_length:
            # Send in chunks
            lines = file_list.split('\n')
            current_chunk = lines[0] + '\n' + lines[1] + '\n\n'  # Header
            
            for line in lines[2:]:
                if len(current_chunk + line + '\n') > max_length:
                    update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            if current_chunk.strip():
                update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            update.message.reply_text(file_list, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in ls command: {e}")
        update.message.reply_text(f"❌ Error listing files: {str(e)[:100]}")


def help_command(update, context):
    """Show help information about all available commands"""
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info("Ignoring help request from untrusted user '%s' with id '%s'", user.first_name, user.id)
        return
    
    # Get current configuration
    default_format = os.getenv('DEFAULT_OUTPUT_FORMAT', '').upper()
    storage_dir = os.getenv('LOCAL_STORAGE_DIR', './data')
    
    help_text = f"""🤖 **YouTube Telegram Downloader Bot**

**📋 Available Commands:**

🔍 `/help` - Show this help message
👤 `/whoami` - Show your Telegram user ID
📁 `/ls` - List all downloaded media files
🔎 `/search <query>` - Search for files by title (case-insensitive)

**🎵 Download Features:**

📺 **Send any YouTube URL** to start downloading
• Automatic download with format: **{default_format or 'Not set'}**
• Real-time progress tracking with percentages
• Supports both audio (MP3) and video (MP4) formats
• Files saved to: `{storage_dir}`

**🎯 Supported Platforms:**
YouTube, and any platform supported by yt-dlp

**⚙️ Current Configuration:**
• Default output format: **{default_format or 'Manual selection'}**
• Storage location: `{storage_dir}`
• Auto-download: **{'✅ Enabled' if default_format else '❌ Manual selection required'}**

**📖 Usage Examples:**

1️⃣ **Download a video:**
   Send: `https://www.youtube.com/watch?v=VIDEO_ID`
   
2️⃣ **List downloaded files:**
   Send: `/ls`
   
3️⃣ **Search for files:**
   Send: `/search music` or `/search freak`
   
4️⃣ **Check your user ID:**
   Send: `/whoami`

**🔒 Security:**
Only trusted users can use this bot.

**💡 Tips:**
• Progress is shown in real-time during downloads
• Your original URL message is automatically deleted after download
• Use `/ls` to see all your downloaded files with sizes
• Use `/search` to find specific files quickly
• Both audio and video formats are supported

**🛠️ Technical Info:**
• Powered by yt-dlp for reliable downloads
• Local storage with configurable directory
• Automatic format conversion (MP4→MP3 for audio)
• Progress tracking with session IDs

Need help? Contact your bot administrator! 🚀"""

    update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)


def search_command(update, context):
    """Search for media files by title (case-insensitive)"""
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info("Ignoring search request from untrusted user '%s' with id '%s'", user.first_name, user.id)
        return
    
    # Get search query from command arguments
    search_query = ' '.join(context.args).strip()
    
    if not search_query:
        update.message.reply_text(
            "🔎 **Search Media Files**\n\n"
            "Usage: `/search <query>`\n\n"
            "**Examples:**\n"
            "• `/search music`\n"
            "• `/search infraction`\n"
            "• `/search .mp3` (search by file extension)\n\n"
            "Search is case-insensitive and matches anywhere in the filename.",
            parse_mode='Markdown'
        )
        return
    
    try:
        storage_dir = os.getenv('LOCAL_STORAGE_DIR', './data')
        # Convert relative path to absolute path for directory listing
        if storage_dir.startswith('./'):
            storage_dir = '/home/bot/' + storage_dir[2:]
        
        if not os.path.exists(storage_dir):
            update.message.reply_text(f"📁 Storage directory not found: {storage_dir}")
            return
        
        # Get all media files
        media_extensions = {'.mp3', '.mp4', '.wav', '.flac', '.avi', '.mkv', '.webm', '.m4a', '.ogg'}
        all_media_files = []
        
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in media_extensions):
                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                    size_str = size(file_size)
                except:
                    size_str = "Unknown"
                
                all_media_files.append({
                    'name': filename,
                    'size': size_str,
                    'path': file_path
                })
        
        # Filter files by search query (case-insensitive)
        search_query_lower = search_query.lower()
        matching_files = [
            file_info for file_info in all_media_files 
            if search_query_lower in file_info['name'].lower()
        ]
        
        # Sort alphabetically by filename
        matching_files.sort(key=lambda x: x['name'].lower())
        
        if not matching_files:
            update.message.reply_text(
                f"🔎 **No files found**\n\n"
                f"No files matching `{search_query}` found in storage.\n\n"
                f"📂 Searched in: `{storage_dir}`\n"
                f"📊 Total files in storage: {len(all_media_files)}\n\n"
                f"Use `/ls` to see all files.",
                parse_mode='Markdown'
            )
            return
        
        # Format the search results
        result_text = f"🔎 **Search Results** ({len(matching_files)} files found)\n"
        result_text += f"🔍 Query: `{search_query}`\n"
        result_text += f"📂 Location: `{storage_dir}`\n\n"
        
        for i, file_info in enumerate(matching_files, 1):
            # Determine emoji based on file extension
            name = file_info['name']
            if name.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg')):
                emoji = "🎵"
            else:
                emoji = "🎬"
            
            result_text += f"{i:2d}. {emoji} `{name}`\n"
            result_text += f"     📊 Size: {file_info['size']}\n\n"
        
        # Split message if too long for Telegram
        max_length = 4000
        if len(result_text) > max_length:
            # Send in chunks
            lines = result_text.split('\n')
            current_chunk = lines[0] + '\n' + lines[1] + '\n' + lines[2] + '\n\n'  # Header
            
            for line in lines[3:]:
                if len(current_chunk + line + '\n') > max_length:
                    update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            if current_chunk.strip():
                update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            update.message.reply_text(result_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in search command: {e}")
        update.message.reply_text(f"❌ Error searching files: {str(e)[:100]}")


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
    
    # handle ls command as plain string
    if message_text == "ls":
        ls_command(update, context)
        return ConversationHandler.END
    
    # handle help command as plain string
    if message_text == "help":
        help_command(update, context)
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
        
        # Provide more specific error messages
        error_msg = "❌ I can't download this URL"
        
        if url.endswith('youtube.com/watch?v') or url.endswith('youtube.com/watch?v='):
            error_msg = "❌ Incomplete YouTube URL!\n\n" \
                       "Please send a complete URL like:\n" \
                       "`https://www.youtube.com/watch?v=dQw4w9WgXcQ`"
        elif 'youtube.com/watch?v=' in url:
            video_id = url.split('v=')[1].split('&')[0] if 'v=' in url else ''
            if video_id in ['VIDEO_ID', 'VIDEOID', 'your_video_id', 'example']:
                error_msg = f"❌ Placeholder video ID detected: `{video_id}`\n\n" \
                           "Please replace with a real YouTube video ID!"
        elif not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'twitch.tv', 'vimeo.com']):
            error_msg = "❌ Unsupported platform!\n\n" \
                       "I support YouTube, Twitch, Vimeo and other platforms supported by yt-dlp.\n" \
                       "Send `/help` for more info."
        else:
            error_msg = f"❌ Cannot download from this URL: `{url[:50]}...`\n\n" \
                       "Please check if the URL is correct and accessible."
        
        update.message.reply_text(error_msg, parse_mode='Markdown')
        return ConversationHandler.END


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
    
    # Always use local storage now, pass output_format to TaskData
    # The DownloadTask will handle all progress messaging
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
    
    # Always use local storage now, pass output_format to TaskData
    # The DownloadTask will handle all progress messaging
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

    # Add dedicated command handlers
    dp.add_handler(CommandHandler('ls', ls_command))
    dp.add_handler(CommandHandler('whoami', whoami))
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(CommandHandler('search', search_command))
    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABORT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
