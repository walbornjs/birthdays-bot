#!/usr/bin/env python3
"""
Working Telegram Birthday Bot - Direct Installation Version
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta, date
import logging
import locale
import json
import asyncio

# Try to install python-telegram-bot if not available
try:
  import telegram
  from telegram import Update
  from telegram.ext import Application, CommandHandler, ContextTypes
  print("telegram imported successfully")
except ImportError as e:
  print(f"Import error: {e}")
  print("Attempting to install python-telegram-bot...")
  import subprocess
  import sys
  
  try:
    # Remove conflicting package first
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "telegram"])
  except:
    pass
  
  # Install correct package
  subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==21.0.1"])
  
  # Try import again
  try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    print("Successfully installed and imported python-telegram-bot")
  except ImportError as e2:
    print(f"Still cannot import after installation: {e2}")
    sys.exit(1)

try:
  from pymorphy3 import MorphAnalyzer
  MORPH_AVAILABLE = True
except ImportError:
  MORPH_AVAILABLE = False

MOSCOW_TZ = timezone(timedelta(hours=3))

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
HOUR = 9
MINUTE = 0

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize morphological analyzer if available
morph = None
if MORPH_AVAILABLE:
  try:
    morph = MorphAnalyzer()
    logger.info("Morphological analyzer initialized")
  except Exception as e:
    logger.warning(f"Failed to initialize morphological analyzer: {e}")
    MORPH_AVAILABLE = False

def decline_name(name, case):
  """Decline a Russian name to the specified grammatical case."""
  if not MORPH_AVAILABLE or not morph:
    return name
    
  try:
    parsed = morph.parse(name)
    if parsed:
      inflected = parsed[0].inflect({case})
      if inflected:
        return inflected.word.capitalize()
  except Exception as e:
    logger.debug(f"Failed to decline name '{name}': {e}")
    
  return name

# Database of birthdays with JSON file persistence
DEFAULT_PERSONS = [
  {"name": "Платон", "birthday": "2000-01-15"},
  {"name": "Черный Витя", "birthday": "2000-05-29"},
  {"name": "Эмиль", "birthday": "2000-12-08"},
  {"name": "Аня Новицкая", "birthday": "2017-10-22"},
  {"name": "Нина Черная", "birthday": "2020-08-18"},
  {"name": "Агата", "birthday": "2019-06-20"},
  {"name": "Левон", "birthday": "2018-06-10"},
  {"name": "Миша", "birthday": "2020-10-19"},
  {"name": "Мила", "birthday": "2020-07-19"},
  {"name": "Аврора", "birthday": "2021-06-19"},
  {"name": "Вера", "birthday": "2018-05-06"},
  {"name": "Мира", "birthday": "2020-11-06"},
  {"name": "Вероника", "birthday": "2000-05-04"},
]

def load_birthdays():
  """Load birthdays from JSON file."""
  try:
    with open("birthdays.json", "r", encoding="utf-8") as f:
      data = json.load(f)
      return data.get("birthdays", DEFAULT_PERSONS)
  except FileNotFoundError:
    # Create file with default data
    save_birthdays(DEFAULT_PERSONS)
    return DEFAULT_PERSONS
  except Exception as e:
    logger.error(f"Error loading birthdays: {e}")
    return DEFAULT_PERSONS

def save_birthdays(birthdays):
  """Save birthdays to JSON file."""
  try:
    data = {
      "birthdays": birthdays,
      "last_updated": datetime.now().isoformat()
    }
    with open("birthdays.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except Exception as e:
    logger.error(f"Error saving birthdays: {e}")

def get_persons():
  """Get current list of persons with parsed dates."""
  birthdays = load_birthdays()
  persons = []
  for entry in birthdays:
    try:
      birthday = datetime.fromisoformat(entry["birthday"]).date()
      persons.append({
        "name": entry["name"],
        "birthday": birthday
      })
    except Exception as e:
      logger.error(f"Error parsing birthday for {entry.get('name', 'unknown')}: {e}")
  return persons

def format_date(date_obj):
  """Format a date object to Russian date string."""
  try:
    # Try to set Russian locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
  except locale.Error:
    try:
      locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
    except locale.Error:
      logger.warning("Russian locale not available, using default")
  
  try:
    # Russian month names
    month_names = [
      "января", "февраля", "марта", "апреля", "мая", "июня",
      "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{date_obj.day} {month_names[date_obj.month - 1]}"
  except (IndexError, AttributeError):
    return date_obj.strftime("%d.%m")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Initialize the bot and schedule birthday notifications."""
  try:
    await update.message.reply_text("🎉 Birthday Bot запущен! Планирую уведомления о днях рождения...")
    
    # Schedule all birthday tasks
    await schedule_birthday_tasks(update, context.job_queue)
    
    await update.message.reply_text(
      "✅ Все уведомления запланированы!\n\n"
      "Используйте /help для списка команд."
    )
    
  except Exception as e:
    logger.error(f"Error in start command: {e}")
    await update.message.reply_text(f"Ошибка при запуске: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Show help information."""
  help_text = """
🎂 <b>Birthday Bot - Команды</b>

/start - Запустить бота и запланировать уведомления
/list - Показать все дни рождения
/check - Проверить запланированные уведомления
/stop - Остановить все уведомления
/help - Показать эту справку

<i>Бот автоматически отправляет уведомления о днях рождения в 9:00 МСК</i>
"""
  
  await update.message.reply_text(help_text, parse_mode="HTML")

async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """List all birthdays."""
  try:
    persons = get_persons()
    
    if not persons:
      await update.message.reply_text("📝 Список дней рождения пуст.")
      return
    
    # Sort by month and day
    persons.sort(key=lambda x: (x["birthday"].month, x["birthday"].day))
    
    message_parts = ["🎂 <b>Список дней рождения:</b>\n"]
    
    for person in persons:
      name = person["name"]
      birthday = person["birthday"]
      age = datetime.now().year - birthday.year
      
      message_parts.append(
        f"👤 <b>{name}</b> - {format_date(birthday)} ({age} лет)"
      )
    
    # Split message if too long
    full_message = "\n".join(message_parts)
    if len(full_message) > 4000:
      # Send in chunks
      chunk_size = 4000
      for i in range(0, len(full_message), chunk_size):
        chunk = full_message[i:i + chunk_size]
        await update.message.reply_text(chunk, parse_mode="HTML")
    else:
      await update.message.reply_text(full_message, parse_mode="HTML")
      
  except Exception as e:
    logger.error(f"Error in list_birthdays: {e}")
    await update.message.reply_text(f"Ошибка при получении списка: {e}")

def get_job_data(update, person):
  """Generate job data"""
  return {
    "name": person["name"],
    "birthday": person["birthday"],
    "chat_id": update.effective_chat.id,
    "message_thread_id": getattr(update.effective_message, 'message_thread_id', None)
  }

def get_job_name(update, person):
  """Generate job name"""
  thread_id = getattr(update.effective_message, 'message_thread_id', None)
  thread_suffix = f"_{thread_id}" if thread_id else ""
  return f"birthday_{update.effective_chat.id}{thread_suffix}_{person['name']}_{person['birthday']}"

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Check what birthday notifications we have"""
  try:
    jobs = context.job_queue.jobs()
    
    if not jobs:
      await update.message.reply_text("📅 Нет запланированных уведомлений.")
      return
    
    message_parts = ["📅 <b>Запланированные уведомления:</b>\n"]
    
    for job in jobs:
      if hasattr(job, 'data') and 'name' in job.data:
        name = job.data['name']
        when = job.next_t
        if when:
          when_str = when.strftime("%d.%m.%Y %H:%M")
          message_parts.append(f"🎂 {name} - {when_str}")
    
    if len(message_parts) == 1:
      await update.message.reply_text("📅 Нет активных уведомлений.")
    else:
      full_message = "\n".join(message_parts)
      await update.message.reply_text(full_message, parse_mode="HTML")
      
  except Exception as e:
    logger.error(f"Error in check command: {e}")
    await update.message.reply_text(f"Ошибка при проверке: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove all notification jobs."""
  try:
    jobs = context.job_queue.jobs()
    removed_count = 0
    
    # Remove all jobs for this chat
    for job in jobs:
      if (hasattr(job, 'data') and 
        job.data.get('chat_id') == update.effective_chat.id):
        job.schedule_removal()
        removed_count += 1
    
    await update.message.reply_text(
      f"🛑 Остановлено {removed_count} уведомлений."
    )
    
  except Exception as e:
    logger.error(f"Error in stop command: {e}")
    await update.message.reply_text(f"Ошибка при остановке: {e}")

async def schedule_birthday_tasks(update, job_queue):
  """Schedule tasks for sending birthday reminders."""
  try:
    persons = get_persons()
    now = datetime.now(MOSCOW_TZ)
    scheduled_count = 0
    
    for person in persons:
      job_data = get_job_data(update, person)
      job_name = get_job_name(update, person)
      
      # Remove existing job if any
      current_jobs = job_queue.get_jobs_by_name(job_name)
      for job in current_jobs:
        job.schedule_removal()
      
      # Calculate next birthday
      birthday = person["birthday"]
      this_year = now.year
      
      # Try this year first
      next_birthday = datetime.combine(
        birthday.replace(year=this_year),
        time(hour=HOUR, minute=MINUTE),
        tzinfo=MOSCOW_TZ
      )
      
      # If birthday already passed this year, schedule for next year
      if next_birthday <= now:
        next_birthday = datetime.combine(
          birthday.replace(year=this_year + 1),
          time(hour=HOUR, minute=MINUTE),
          tzinfo=MOSCOW_TZ
        )
      
      # Schedule the job
      job_queue.run_once(
        callback=send_birthday_reminder_and_create_next,
        when=next_birthday,
        data=job_data,
        name=job_name
      )
      
      # Schedule early reminder (10 days before)
      early_reminder = next_birthday - timedelta(days=10)
      early_reminder = early_reminder.replace(hour=HOUR + 1)  # One hour later
      
      if early_reminder > now:
        early_job_name = f"early_{job_name}"
        job_queue.run_once(
          callback=send_early_birthday_reminder_and_create_next,
          when=early_reminder,
          data=job_data,
          name=early_job_name
        )
      
      scheduled_count += 1
      logger.info(f"Scheduled birthday for {person['name']} at {next_birthday}")
    
    logger.info(f"Scheduled {scheduled_count} birthday notifications")
    
  except Exception as e:
    logger.error(f"Error scheduling birthday tasks: {e}")
    raise

async def send_birthday_reminder_and_create_next(context):
  """Send a birthday reminder and schedule the next one"""
  job = context.job
  name = job.data["name"]
  birthday = job.data["birthday"]
  chat_id = job.data["chat_id"]
  message_thread_id = job.data["message_thread_id"]

  try:
    age = datetime.now().year - birthday.year
    
    message_text = f"""🎉 <b>Сегодня день рождения у {decline_name(name, 'gent')}!</b>

🎂 {decline_name(name, 'datv')} исполняется {age} лет!

<code>
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⠤⠒⠊⠉⠉⠉⠒⠲⢤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢦⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡜⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢣⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⢠⠖⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠤⡀⠀⢸⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⢠⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡄⢸⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⡜⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢱⢸⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢀⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡜⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡟⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⢻⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠈⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠀⠀⠀⠈⠻⣿⣿⣿⣿⠟⠁⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡇⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢸⡷⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⢾⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡜⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡜⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡜⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠒⠤⣀⣀⣀⣀⣀⣀⡠⠤⠒⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀
</code>

🎁 Поздравляем с днем рождения! 🎁"""

    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )
    
    logger.info(f"Sent birthday notification for {name}")
    
  except Exception as e:
    logger.error(f"Error sending birthday notification: {e}")
  
  # Schedule next year's notification
  try:
    next_year = datetime.now(MOSCOW_TZ).year + 1
    next_bday = birthday.replace(year=next_year)
    when = datetime.combine(next_bday, time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)

    context.job_queue.run_once(
      callback=send_birthday_reminder_and_create_next,
      when=when,
      data=job.data,
      name=job.name
    )
    logger.info(f"Rescheduled birthday notification for {decline_name(name, 'gent')} to {when}")
  except Exception as e:
    logger.error(f"Error rescheduling birthday notification: {e}")

async def send_early_birthday_reminder_and_create_next(context):
  """Send an early birthday reminder and schedule the next one"""
  job = context.job
  name = job.data["name"]
  birthday = job.data["birthday"]
  chat_id = job.data["chat_id"]
  message_thread_id = job.data["message_thread_id"]

  try:
    message_text = f"""⏳ <b>Скоро</b> день рождения у <b>{decline_name(name, 'gent')}</b>!

🎂 {format_date(birthday).capitalize()}!

<code>
 ⠀⠀⠀⢀⠠⠤⠀⢀⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠐⠀⠐⠀⠀⢀⣾⣿⡇⠀⠀⠀⠀⠀⢀⣼⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⠀⠀⠀⠀⣴⣿⣿⠇⠀⠀
⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣇⠀⠀⢀⣾⣿⣿⣿⠀⠀⠀
⠀⠀⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠐
⠀⠀⠀⠀⢰⡿⠉⠀⡜⣿⣿⣿⡿⠿⢿⣿⣿⡃⠀⠀⠂
⠀⠀⠒⠒⠸⣿⣄⡘⣃⣿⣿⡟⢰⠃⠀⢹⣿⡇⠀⠀⠀
⠀⠀⠚⠉⠀⠊⠻⣿⣿⣿⣿⣿⣮⣤⣤⣿⡟⠁⠘⠠⠁
⠀⠀⠀⠀⠀⠠⠀⠀⠈⠙⠛⠛⠛⠛⠛⠁⠀⠒⠤⠀⠀
⠨⠠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠑⠀⠀⠀⠀
⠁⠃⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
</code>

🎁 Готовим подарки! 🎁"""

    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )
    
    logger.info(f"Sent early birthday notification for {name}")
    
  except Exception as e:
    logger.error(f"Error sending early birthday notification: {e}")
  
  # Schedule next year's early reminder
  try:
    next_year = datetime.now(MOSCOW_TZ).year + 1
    next_bday = birthday.replace(year=next_year)
    early = datetime.combine(next_bday - timedelta(days=10), time(hour=HOUR + 1, minute=MINUTE), tzinfo=MOSCOW_TZ)

    context.job_queue.run_once(
      callback=send_early_birthday_reminder_and_create_next,
      when=early,
      data=job.data,
      name=job.name
    )
    logger.info(f"Rescheduled early notification for {decline_name(name, 'gent')} to {early}")
  except Exception as e:
    logger.error(f"Error rescheduling early notification: {e}")

def main():
  """Main function to run the bot."""
  if not TOKEN:
    logger.error("TELEGRAM_TOKEN is required in environment variables")
    return

  try:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("list", list_birthdays))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
  except Exception as e:
    logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
  main()