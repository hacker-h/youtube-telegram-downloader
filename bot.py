#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This bot uses an inline keyboard to interact with the user.

Press Ctrl-C on the command line to stop the bot.
Optimized Dockerfile for better layer caching.
"""
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import yt_dlp
from hurry.filesize import size
from task import TaskData, DownloadTask
from backends.storage_manager import StorageManager
from backends.storage_monitor import get_storage_monitor
import subprocess

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

# Stages - added STORAGE stage for backend selection
STORAGE, OUTPUT, DOWNLOAD = range(3)

# Callback data
CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_LOCAL = "local"
CALLBACK_BEST_FORMAT = "best"
CALLBACK_SELECT_FORMAT = "select_format"
CALLBACK_ABORT = "abort"

# Initialize storage manager
storage_manager = StorageManager()


def quick_url_check(url):
    """
    Fast static URL validation without API calls.
    Returns: (is_likely_valid, error_message)
    """
    # Check for obvious incomplete URLs
    if 'youtube.com/watch?v=' in url:
        video_id = url.split('v=')[1].split('&')[0]
        if not video_id or video_id in ['VIDEO_ID', 'VIDEOID', 'your_video_id', 'example']:
            return False, f"❌ Placeholder video ID detected: `{video_id}`\n\nPlease replace with a real YouTube video ID!"
    
    # Check for incomplete YouTube URLs without video ID
    if url.endswith('youtube.com/watch?v') or url.endswith('youtube.com/watch?v='):
        return False, "❌ Incomplete YouTube URL!\n\nPlease send a complete URL like:\n`https://www.youtube.com/watch?v=dQw4w9WgXcQ`"
    
    # Check for supported platforms
    supported_domains = ['youtube.com', 'youtu.be', 'twitch.tv', 'vimeo.com', 'soundcloud.com', 'bandcamp.com']
    if not any(domain in url.lower() for domain in supported_domains):
        return False, "❌ Unsupported platform!\n\nI support YouTube, Twitch, Vimeo and other platforms supported by yt-dlp.\nSend `/help` for more info."
    
    # Basic URL format check
    if not url.startswith(('http://', 'https://')):
        return False, "❌ Invalid URL format!\n\nPlease send a complete URL starting with http:// or https://"
    
    return True, None



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
    
    # Check if we should ask for backend selection
    backend = get_backend_for_command(update, context, "ls")
    if backend is None:
        # Multiple backends available, ask user to choose
        show_backend_selection_for_command(update, context, "ls")
        return
    
    # Execute ls command with determined backend
    backend_name = storage_manager.get_backend_display_name(backend)
    execute_ls_command(update, backend, backend_name)


def storage_command(update, context):
    """Show storage status for all configured backends"""
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info("Ignoring storage request from untrusted user '%s' with id '%s'", user.first_name, user.id)
        return
    
    try:
        # Get storage monitor instance
        storage_monitor = get_storage_monitor(BOT_TOKEN)
        
        # Send initial message
        status_msg = update.message.reply_text("🔍 Checking storage status...")
        
        # Get all available backends
        available_backends = storage_manager.get_available_backends()
        
        if not available_backends:
            status_msg.edit_text("❌ No storage backends configured!")
            return
        
        # Check storage for each backend
        storage_statuses = []
        
        for backend in available_backends:
            backend_name = storage_manager.get_backend_display_name(backend)
            
            if backend == 'local':
                # For local storage, show directory size
                try:
                    storage_path = storage_manager.ensure_storage_path(backend)
                    
                    # Calculate directory size
                    total_size = 0
                    file_count = 0
                    for dirpath, dirnames, filenames in os.walk(storage_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            try:
                                total_size += os.path.getsize(filepath)
                                file_count += 1
                            except (OSError, IOError):
                                pass
                    
                    # Format size
                    size_str = storage_monitor.format_storage_size(total_size)
                    
                    # Get filesystem status for local backend
                    filesystem_status = storage_monitor.get_storage_status(backend, storage_path)
                    if filesystem_status:
                        storage_statuses.append(
                            f"{filesystem_status}\n"
                            f"• Files in directory: {file_count}\n"
                            f"• Directory size: {size_str}\n"
                            f"• Path: {storage_path}"
                        )
                    else:
                        storage_statuses.append(
                            f"💾 **{backend_name}**\n"
                            f"• Files: {file_count}\n"
                            f"• Directory size: {size_str}\n"
                            f"• Path: {storage_path}\n"
                            f"• Filesystem: ❌ Unable to check"
                        )
                    
                except Exception as e:
                    storage_statuses.append(
                        f"💾 **{backend_name}**\n"
                        f"• Status: ❌ Error checking local storage\n"
                        f"• Error: {str(e)[:50]}..."
                    )
            else:
                # For cloud backends, use rclone to check storage
                status = storage_monitor.get_storage_status(backend)
                if status:
                    storage_statuses.append(status)
                else:
                    storage_statuses.append(
                        f"☁️ **{backend_name}**\n"
                        f"• Status: ❌ Unable to check storage\n"
                        f"• Check connection and configuration"
                    )
        
        # Combine all statuses
        if storage_statuses:
            final_message = "📊 **Storage Status Report**\n\n" + "\n\n".join(storage_statuses)
            
            # Add threshold information
            warning_gb = int(os.getenv('STORAGE_WARNING_THRESHOLD_GB', '1'))
            
            final_message += f"\n\n⚙️ **Warning Thresholds:**\n"
            final_message += f"• Warning: {warning_gb} GB"
            
        else:
            final_message = "❌ No storage information available"
        
        # Update the message with final status
        status_msg.edit_text(final_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in storage command: {e}")
        update.message.reply_text(f"❌ Error checking storage status:\n{str(e)[:100]}...")


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
📊 `/storage` - Check storage status for all backends

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
   
4️⃣ **Check storage status:**
   Send: `/storage`
   
5️⃣ **Check your user ID:**
   Send: `/whoami`

**🔒 Security:**
Only trusted users can use this bot.

**💡 Tips:**
• Progress is shown in real-time during downloads
• Your original URL message is automatically deleted after download
• Use `/ls` to see all your downloaded files with sizes
• Use `/search` to find specific files quickly
• Use `/storage` to monitor cloud storage space
• Both audio and video formats are supported

**🛠️ Technical Info:**
• Powered by yt-dlp for reliable downloads
• Multi-backend storage support (local, Google Drive, Nextcloud, etc.)
• Automatic format conversion (MP4→MP3 for audio)
• Progress tracking with session IDs
• Storage monitoring with low-space warnings

**⚠️ Storage Warnings:**
• You'll receive notifications when storage space is low
• Applies to both cloud storage and local filesystem
• Warning threshold: {os.getenv('STORAGE_WARNING_THRESHOLD_GB', '1')} GB

Need help? Send `/help` anytime!"""

    update.message.reply_text(help_text, parse_mode='Markdown')


def sanitize_search_query(query):
    """
    Sanitize search query to prevent any potential security issues.
    Remove potentially dangerous characters and limit length.
    """
    import re
    
    # Remove control characters, null bytes, and other dangerous chars
    # Keep only alphanumeric, spaces, dots, hyphens, underscores
    safe_query = re.sub(r'[^\w\s\.\-]', '', query)
    
    # Limit length to prevent abuse
    safe_query = safe_query[:100]
    
    # Remove excessive whitespace
    safe_query = ' '.join(safe_query.split())
    
    return safe_query.strip()


def get_media_files_from_gdrive():
    """
    Get all media files from Google Drive using rclone.
    Returns list of file info dictionaries.
    """
    try:
        # Use rclone directly instead of docker run
        # The rclone config should be mounted at /home/bot/rclone-config/rclone.conf
        cmd = [
            'rclone', 'ls', 'gdrive:youtube-downloads',
            '--config', '/home/bot/rclone-config/rclone.conf'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.warning(f"Failed to list Google Drive files: {result.stderr}")
            return []
        
        # Parse rclone ls output
        # Format: "    12345 filename.mp3"
        media_extensions = {'.mp3', '.mp4', '.wav', '.flac', '.avi', '.mkv', '.webm', '.m4a', '.ogg'}
        media_files = []
        
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
                
            # Split by whitespace, first part is size, rest is filename
            parts = line.strip().split(None, 1)
            if len(parts) != 2:
                continue
                
            size_bytes, filename = parts
            
            # Check if it's a media file
            if any(filename.lower().endswith(ext) for ext in media_extensions):
                try:
                    # Convert size to human readable format
                    size_int = int(size_bytes)
                    size_str = size(size_int)
                except:
                    size_str = "Unknown"
                
                media_files.append({
                    'name': filename,
                    'size': size_str,
                    'path': f"gdrive:youtube-downloads/{filename}"
                })
        
        # Sort alphabetically by filename
        media_files.sort(key=lambda x: x['name'].lower())
        
        logger.info(f"Found {len(media_files)} media files in Google Drive")
        return media_files
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout listing Google Drive files")
        return []
    except Exception as e:
        logger.error(f"Error getting media files from Google Drive: {e}")
        return []


def get_media_files_from_path(storage_path, backend=None):
    """
    Get all media files from a specific storage path or cloud backend.
    Returns list of file info dictionaries.
    """
    # For Google Drive backend, use rclone to list files
    if backend == 'gdrive':
        return get_media_files_from_gdrive()
    
    # For local storage, use filesystem
    try:
        if not os.path.exists(storage_path):
            logger.info(f"Storage path does not exist: {storage_path}")
            return []
        
        # Get all media files
        media_extensions = {'.mp3', '.mp4', '.wav', '.flac', '.avi', '.mkv', '.webm', '.m4a', '.ogg'}
        media_files = []
        
        for filename in os.listdir(storage_path):
            file_path = os.path.join(storage_path, filename)
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
        
        return media_files
    except Exception as e:
        logger.error(f"Error getting media files from {storage_path}: {e}")
        return []


def get_media_files_list():
    """
    Legacy function for backward compatibility.
    Now uses the default backend or local storage.
    """
    try:
        # Use default backend if available, otherwise local
        default_backend = storage_manager.get_default_backend()
        if default_backend:
            storage_path = storage_manager.get_storage_path(default_backend)
        else:
            # Fallback to local backend
            storage_path = storage_manager.get_storage_path("local")
        
        media_files = get_media_files_from_path(storage_path)
        return media_files, storage_path
    except Exception as e:
        logger.error(f"Error in get_media_files_list: {e}")
        return None, None


def format_file_list(media_files, title="📁 **Media Files**", backend=None, max_length=4000):
    """
    Format media files list for display with automatic chunking.
    Returns list of message chunks.
    """
    if not media_files:
        return []
    
    file_list = f"{title} ({len(media_files)} files)\n"
    
    # Show appropriate location based on backend
    if backend == 'gdrive':
        file_list += f"☁️ Google Drive: `gdrive:youtube-downloads`\n\n"
    else:
        file_list += f"📂 Location: `{os.getenv('LOCAL_STORAGE_DIR', './data')}`\n\n"
    
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
    if len(file_list) <= max_length:
        return [file_list]
    
    # Split into chunks
    chunks = []
    lines = file_list.split('\n')
    current_chunk = lines[0] + '\n' + lines[1] + '\n\n'  # Header
    
    for line in lines[2:]:
        if len(current_chunk + line + '\n') > max_length:
            if current_chunk.strip():
                chunks.append(current_chunk)
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    
    if current_chunk.strip():
        chunks.append(current_chunk)
    
    return chunks


def search_command(update, context):
    """Search for media files by title (case-insensitive) - SECURITY HARDENED"""
    user = update.message.from_user
    if not is_trusted(user.id):
        logger.info("Ignoring search request from untrusted user '%s' with id '%s'", user.first_name, user.id)
        return
    
    # Get and sanitize search query from command arguments
    raw_search_query = ' '.join(context.args).strip()
    search_query = sanitize_search_query(raw_search_query)
    
    if not search_query:
        update.message.reply_text(
            "🔎 **Search Media Files**\n\n"
            "Usage: `/search <query>`\n\n"
            "**Examples:**\n"
            "• `/search music`\n"
            "• `/search infraction`\n"
            "• `/search mp3` (search by file extension)\n\n"
            "Search is case-insensitive and matches anywhere in the filename.\n"
            "⚠️ Only alphanumeric characters, spaces, dots, hyphens and underscores are allowed.",
            parse_mode='Markdown'
        )
        return
    
    # Warn if query was sanitized
    if search_query != raw_search_query:
        logger.warning(f"Search query sanitized: '{raw_search_query}' -> '{search_query}'")
    
    # Check if we should ask for backend selection
    backend = get_backend_for_command(update, context, "search")
    if backend is None:
        # Multiple backends available, ask user to choose
        show_backend_selection_for_command(update, context, "search", context.args)
        return
    
    # Execute search command with determined backend
    backend_name = storage_manager.get_backend_display_name(backend)
    execute_search_command(update, backend, backend_name, context.args)


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
    
    # Fast static URL validation first
    is_valid_quick, error_msg = quick_url_check(url)
    if not is_valid_quick:
        update.message.reply_text(error_msg, parse_mode='Markdown')
        return ConversationHandler.END
    
    # Send immediate feedback that bot is alive and processing
    checking_msg = update.message.reply_text("🔍 Checking URL...")
    
    # Delete the "checking" message
    try:
        checking_msg.delete()
    except:
        pass
    
    # Check if we should ask for storage backend
    if storage_manager.should_ask_for_backend():
        # Multiple backends available, ask user to choose
        return select_storage_backend(update, context)
    else:
        # Use default backend or only available backend
        default_backend = storage_manager.get_default_backend()
        if default_backend:
            context.user_data["storage_backend"] = default_backend
            logger.info(f"Using default storage backend: {default_backend}")
        else:
            # Only local storage available
            context.user_data["storage_backend"] = "local"
            logger.info("Using local storage (only backend available)")
        
        # Proceed to format selection or direct download
        return proceed_to_format_selection(update, context)


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
    backend = context.user_data.get("storage_backend", "local")
    
    # Pass storage_manager to TaskData
    data = TaskData(url, backend, selected_format, update, output_format, storage_manager)
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
    backend = context.user_data.get("storage_backend", "local")
    
    # Pass storage_manager to TaskData
    data = TaskData(url, backend, selected_format, update, output_format, storage_manager)
    task = DownloadTask(data)
    task.downloadVideo()

    return ConversationHandler.END


def select_storage_backend(update, context):
    """
    A stage asking the user for the storage backend.
    """
    logger.info("select_storage_backend()")
    
    available_backends = storage_manager.get_available_backends()
    
    # If only one backend available, skip selection
    if len(available_backends) == 1:
        backend = list(available_backends.keys())[0]
        context.user_data["storage_backend"] = backend
        logger.info(f"Only one backend available, auto-selecting: {backend}")
        return proceed_to_format_selection(update, context)
    
    # Build keyboard with available backends
    button_list = []
    for backend_id, backend_name in available_backends.items():
        if backend_id == "local":
            emoji = "💾"
        else:
            emoji = "☁️"
        button_list.append(InlineKeyboardButton(
            f"{emoji} {backend_name}", callback_data=f"storage_{backend_id}"))
    
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    
    url = context.user_data["url"]
    update.message.reply_text(
        f"🗂️ **Choose Storage Backend**\n\nWhere should I save the download from:\n`{url}`", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return STORAGE


def handle_storage_selection(update, context):
    """
    Handle storage backend selection and proceed to format selection.
    """
    logger.info("handle_storage_selection()")
    query = update.callback_query
    query.answer()
    
    # Extract backend from callback data (format: "storage_backend_name")
    backend = query.data.replace("storage_", "")
    context.user_data["storage_backend"] = backend
    
    backend_name = storage_manager.get_backend_display_name(backend)
    logger.info(f"User selected storage backend: {backend} ({backend_name})")
    
    # Update message to show selection
    query.edit_message_text(
        f"✅ **Storage Selected:** {backend_name}\n\nProceeding to format selection...",
        parse_mode='Markdown'
    )
    
    return proceed_to_format_selection(update, context)


def proceed_to_format_selection(update, context):
    """
    Proceed to format selection after storage backend is determined.
    """
    url = context.user_data["url"]
    
    # If DEFAULT_OUTPUT_FORMAT is set, start downloading immediately
    if DEFAULT_OUTPUT_FORMAT:
        logger.info(f"Auto-downloading with default format: {DEFAULT_OUTPUT_FORMAT}")
        
        # Start download immediately with best format and default output
        backend = context.user_data.get("storage_backend", "local")
        data = TaskData(url, backend, CALLBACK_BEST_FORMAT, update, DEFAULT_OUTPUT_FORMAT, storage_manager)
        task = DownloadTask(data)
        task.downloadVideo()
        return ConversationHandler.END
    else:
        # Show format selection for manual downloads
        keyboard = [
            [
                InlineKeyboardButton(
                    "Download Best Format", callback_data=CALLBACK_BEST_FORMAT),
                InlineKeyboardButton(
                    "Select Format", callback_data=CALLBACK_SELECT_FORMAT),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send new message or edit existing one
        if hasattr(update, 'callback_query') and update.callback_query:
            # We came from storage selection, edit the message
            update.callback_query.edit_message_text(
                f"Do you want me to download '{url}' ?", 
                reply_markup=reply_markup
            )
        else:
            # Direct entry, send new message
            update.message.reply_text(
                f"Do you want me to download '{url}' ?", 
                reply_markup=reply_markup
            )
        return OUTPUT


def get_backend_for_command(update, context, command_name):
    """
    Get the backend to use for ls/search commands.
    Returns backend name or None if user needs to choose.
    """
    # Check if default backend is set
    default_backend = storage_manager.get_default_backend()
    if default_backend:
        logger.info(f"{command_name} using default backend: {default_backend}")
        return default_backend
    
    # Check if only one backend available
    available_backends = storage_manager.get_available_backends()
    if len(available_backends) == 1:
        backend = list(available_backends.keys())[0]
        logger.info(f"{command_name} using only available backend: {backend}")
        return backend
    
    # Multiple backends available, need to ask user
    return None


def show_backend_selection_for_command(update, context, command_name, command_args=None):
    """
    Show backend selection for ls/search commands.
    """
    available_backends = storage_manager.get_available_backends()
    
    # Build keyboard with available backends
    button_list = []
    for backend_id, backend_name in available_backends.items():
        if backend_id == "local":
            emoji = "💾"
        else:
            emoji = "☁️"
        
        # Create callback data with command and args
        callback_data = f"cmd_{command_name}_{backend_id}"
        if command_args:
            # For search, we'll store args in user_data
            context.user_data[f"{command_name}_args"] = command_args
        
        button_list.append(InlineKeyboardButton(
            f"{emoji} {backend_name}", callback_data=callback_data))
    
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    
    if command_name == "search" and command_args:
        message_text = f"🔎 **Choose Backend for Search**\n\nSearch query: `{' '.join(command_args)}`\nWhich storage backend should I search?"
    else:
        message_text = f"📁 **Choose Backend for {command_name.upper()}**\n\nWhich storage backend should I list?"
    
    update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def handle_command_backend_selection(update, context):
    """
    Handle backend selection for ls/search commands.
    """
    query = update.callback_query
    query.answer()
    
    # Parse callback data: cmd_command_backend
    parts = query.data.split('_')
    if len(parts) != 3 or parts[0] != 'cmd':
        query.edit_message_text("❌ Invalid command selection")
        return
    
    command_name = parts[1]
    backend = parts[2]
    
    backend_name = storage_manager.get_backend_display_name(backend)
    logger.info(f"User selected backend {backend} for {command_name} command")
    
    # Execute the command with selected backend
    if command_name == "ls":
        execute_ls_command(query, backend, backend_name)
    elif command_name == "search":
        # Get search args from user_data
        search_args = context.user_data.get("search_args", [])
        execute_search_command(query, backend, backend_name, search_args)
        # Clean up
        context.user_data.pop("search_args", None)


def execute_ls_command(update_or_query, backend, backend_name):
    """
    Execute ls command for a specific backend.
    """
    try:
        storage_path = storage_manager.get_storage_path(backend)
        media_files = get_media_files_from_path(storage_path, backend)
        
        if not media_files:
            if backend == 'gdrive':
                message = f"📁 No media files found in: {backend_name}\n☁️ Google Drive: `gdrive:youtube-downloads`"
            else:
                message = f"📁 No media files found in: {backend_name}\n📂 Path: `{storage_path}`"
        else:
            # Format and send the file list
            title = f"📁 **{backend_name} Files** ({len(media_files)} files)"
            chunks = format_file_list(media_files, title, backend)
            message = chunks[0] if chunks else "📁 No files found"
        
        # Check if this is from a callback query (button) or direct command
        if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
            # From button selection - use edit_message_text
            update_or_query.callback_query.edit_message_text(message, parse_mode='Markdown')
        elif hasattr(update_or_query, 'edit_message_text'):
            # This is a CallbackQuery object directly
            update_or_query.edit_message_text(message, parse_mode='Markdown')
        else:
            # From direct command - use reply_text
            update_or_query.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in ls command for backend {backend}: {e}")
        error_msg = f"❌ Error listing files from {backend_name}: {str(e)[:100]}"
        
        # Same logic for error messages
        if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
            update_or_query.callback_query.edit_message_text(error_msg)
        elif hasattr(update_or_query, 'edit_message_text'):
            update_or_query.edit_message_text(error_msg)
        else:
            update_or_query.message.reply_text(error_msg)


def execute_search_command(update_or_query, backend, backend_name, search_args):
    """
    Execute search command for a specific backend.
    """
    try:
        search_query = ' '.join(search_args).strip()
        if not search_query:
            message = "🔎 No search query provided"
        else:
            search_query = sanitize_search_query(search_query)
            storage_path = storage_manager.get_storage_path(backend)
            all_media_files = get_media_files_from_path(storage_path, backend)
            
            # Filter files by search query (case-insensitive)
            search_query_lower = search_query.lower()
            matching_files = [
                file_info for file_info in all_media_files 
                if search_query_lower in file_info['name'].lower()
            ]
            
            if not matching_files:
                if backend == 'gdrive':
                    location_info = "☁️ Google Drive: `gdrive:youtube-downloads`"
                else:
                    location_info = f"📂 Searched in: `{storage_path}`"
                
                message = (f"🔎 **No files found**\n\n"
                          f"No files matching `{search_query}` found in {backend_name}.\n\n"
                          f"{location_info}\n"
                          f"📊 Total files in backend: {len(all_media_files)}")
            else:
                # Format the search results
                title = f"🔎 **Search Results in {backend_name}**\n🔍 Query: `{search_query}`"
                chunks = format_file_list(matching_files, title, backend)
                message = chunks[0] if chunks else "🔎 No results found"
        
        # Check if this is from a callback query (button) or direct command
        if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
            # From button selection - use edit_message_text
            update_or_query.callback_query.edit_message_text(message, parse_mode='Markdown')
        elif hasattr(update_or_query, 'edit_message_text'):
            # This is a CallbackQuery object directly
            update_or_query.edit_message_text(message, parse_mode='Markdown')
        else:
            # From direct command - use reply_text
            update_or_query.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in search command for backend {backend}: {e}")
        error_msg = f"❌ Error searching in {backend_name}: {str(e)[:100]}"
        
        # Same logic for error messages
        if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
            update_or_query.callback_query.edit_message_text(error_msg)
        elif hasattr(update_or_query, 'edit_message_text'):
            update_or_query.edit_message_text(error_msg)
        else:
            update_or_query.message.reply_text(error_msg)


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with storage selection
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, start)],
        states={
            STORAGE: [
                CallbackQueryHandler(handle_storage_selection, pattern='^storage_'),
            ],
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
    dp.add_handler(CommandHandler('storage', storage_command))
    dp.add_handler(CallbackQueryHandler(handle_command_backend_selection, pattern='^cmd_'))
    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABORT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
