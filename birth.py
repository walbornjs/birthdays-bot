#!/usr/bin/env python
# pylint: disable=unused-argument

import os
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta, date
import logging


from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from utils.ansii import totoro, meow, kaomoji, disnay
from utils.decline import decline_name
from utils.date import format_date
from utils.file import load, save

MOSCOW_TZ = timezone(timedelta(hours=3))

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
HOUR = 9
MINUTE = 0

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

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

def get_persons():
  """Get current list of persons with parsed dates."""
  birthdays = load('birthdays.json', DEFAULT_PERSONS)
  persons = []
  for entry in birthdays:
    try:
      birthday = datetime.fromisoformat(entry["birthday"]).date()
      persons.append({
        "name": entry["name"],
        "birthday": birthday
      })
    except Exception as e:
      logging.error(f"Error parsing birthday for {entry.get('name', 'unknown')}: {e}")
  return persons


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Initializes the bot."""
  message_text = (
    f"🎂 <b>Привет!</b>\n\n"
    f"Я - <i>бот-о-днях-рождения-напоминатель</i>.\n"
    f"Вы выпустили меня из кувшина!\n<code>"
    f"<pre>{totoro}</pre>\n"
    f"\n\n... ждём 🎂...</code>"
  )
  await update.message.reply_text(
    text=message_text,
    parse_mode="HTML"
  )

  await schedule_birthday_tasks(update, context.job_queue)


def get_job_data(update: Update, person) -> tuple:
  """Generate job data"""
  chat_id = update.effective_chat.id # update.effective_message.chat_id
  message_thread_id = update.effective_message.message_thread_id # getattr(update.effective_message, 'message_thread_id', None)

  name = person["name"]
  bday = person["birthday"]

  return chat_id, message_thread_id, name, bday


def get_job_name(update: Update, person) -> str:
  """Generate job name"""
  chat_id, message_thread_id, name, bday = get_job_data(update, person)
  # when = datetime.combine(bday, time(hour=9, minute=0), tzinfo=MOSCOW_TZ)
  return f"{chat_id}_{message_thread_id}_{name}_{bday}"


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Check what birthday notifications we have"""
  try:
    jobs = context.job_queue.jobs()
    
    if not jobs:
      message = (
        "📅 <b>Нет активных уведомлений</b>\n\n"
        "Нужно вызвать команду /start"
      )
      return await update.message.reply_text(message, parse_mode="HTML")
    
    message_parts = []
    
    jobs = sorted([job for job in jobs], key=lambda x: (x.next_t.month, x.next_t.day))

    for job in jobs:
      if hasattr(job, 'data') and 'name' in job.data:
        name = job.data['name']
        when = job.next_t
        if when:
          when_str = when.strftime("%d.%m.%Y %H:%M")
          message_parts.append(f"• <b>{name}</b> - {when_str}")
    
    if not message_parts:
      message = (
        "📅 <b>Нет активных уведомлений</b>\n\n"
        "Нужно вызвать команду /start"
      )
      return await update.message.reply_text(message, parse_mode="HTML")
    
    full_message = "📅 <b>Запланированные уведомления:</b>\n\n" + "\n".join(message_parts)
    await update.message.reply_text(full_message, parse_mode="HTML")
      
  except Exception as e:
    logging.error(f"Error in /check command: {e}")
    await update.message.reply_text(f"Ошибка при проверке: {e}", parse_mode="HTML")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove all notification jobs."""
  try:
    jobs = context.job_queue.jobs()
    removed_count = 0
    
    # Remove all jobs for this chat
    for job in jobs:
      if (hasattr(job, 'data') and job.data.get('chat_id') == update.effective_chat.id):
        job.schedule_removal()
        removed_count += 1
    
    await update.message.reply_text(
      f"✋ Остановлено <b>{removed_count}</b> уведомлений\n\n"
      f"<b>Мавр</b> сделал своё дело,\n"
      f"<b>Мавр</b> может уходить! 🐼"
      f"\n\n<code>{disnay}</code>",
      parse_mode="HTML"
    )
    
  except Exception as e:
    logging.error(f"Error in stop command: {e}")
    await update.message.reply_text(f"Ошибка при остановке: {e}")

async def schedule_birthday_tasks(update: Update, job_queue) -> None:
  """Shedules tasks for sending birthday reminders."""
  now = datetime.now(MOSCOW_TZ)

  persons = get_persons()
  for person in persons:
    chat_id, message_thread_id, name, bday = get_job_data(update, person)
    
    when = datetime.combine(bday.replace(year=now.year), time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)
    # when = datetime.combine(bday.replace(year=now.year), time(hour=now.hour, minute=now.minute, second=now.second + 3), tzinfo=MOSCOW_TZ)
    early = datetime.combine(bday.replace(year=now.year) - timedelta(days=10), time(hour=HOUR + 1, minute=MINUTE), tzinfo=MOSCOW_TZ)
    # early = datetime.combine(bday.replace(year=now.year) - timedelta(days=10), time(hour=now.hour, minute=now.minute, second=now.second + 3), tzinfo=MOSCOW_TZ)
    if when < now: when = when.replace(year=now.year + 1)
    if early < now: early = early.replace(year=now.year + 1)
  
    job_data = {
      "chat_id": chat_id,
      "message_thread_id": message_thread_id,
      "name": name,
      "birthday": bday,
      "when": when,
      "early": early,
    }

    job_name = get_job_name(update, person)

    job_queue.run_once(
      callback=send_birthday_reminder_and_create_next,
      when=when,
      data=job_data,
      name=job_name
    )

    job_queue.run_once(
      callback=send_early_birthday_reminder_and_create_next,
      when=early,
      data=job_data,
      name=f"{job_name}_early"
    )
  
    logging.info(f"Запланировано напоминание для {decline_name(name, 'gent')} на {when}")


async def send_birthday_reminder_and_create_next(context: ContextTypes.DEFAULT_TYPE) -> None:
  """Sends a birthday reminder and schedules the next one"""
  job = context.job
  name = job.data["name"]
  birthday = job.data["birthday"]
  chat_id = job.data["chat_id"]
  message_thread_id = job.data["message_thread_id"]

  try:
    age = datetime.now().year - birthday.year
    message_text = (
      f"🎉 Сегодня день рождения у <b>{decline_name(name, 'gent')}</b><code>!\n\n"
      f"🎂 {decline_name(name, 'datv')} исполняется {age} лет!"
      f"<pre>{meow}</pre>\n\n"
      f"... поздравляем ...</code>"
    )
    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )

    logging.info(f"Sent birthday notification for {name}")
  except Exception as e:
    logging.error(f"Error sending birthday notification: {e}")
  
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
    logging.info(f"Rescheduled birthday notification for {decline_name(name, 'gent')} to {when}")
  except Exception as e:
    logging.error(f"Error rescheduling birthday notification: {e}")

async def send_early_birthday_reminder_and_create_next(context: ContextTypes.DEFAULT_TYPE) -> None:
  """Sends an early birthday reminder and schedules the next one"""
  job = context.job
  name = job.data["name"]
  birthday = job.data["birthday"]
  chat_id = job.data["chat_id"]
  message_thread_id = job.data["message_thread_id"]

  try:
    message_text = (
      f"⏳ <b>Скоро</b> день рождения у <b>{decline_name(name, 'gent')}</b>!\n\n"
      f"🎂 {format_date(birthday)}!\n\n<code>"
      f"<pre>{kaomoji}</pre>\n\n"
      f"... готовим подарки ...</code>"
    )
    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )
  except Exception as e:
    logging.error(f"Ошибка отправки уведомления: {e}")
  
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
    logging.info(f"Rescheduled early notification for {decline_name(name, 'gent')} to {early}")
  except Exception as e:
    logging.error(f"Error rescheduling early notification: {e}")

async def list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """List all birthdays"""
  try:
    persons = get_persons()
    # Sort by month and day
    persons.sort(key=lambda x: (x["birthday"].month, x["birthday"].day))
    
    chunks = ["🎂 <b>Список дней рождения:</b>\n"]
    
    for person in persons:
      name = person["name"]
      birthday = person["birthday"]
      # age = datetime.now().year - birthday.year
      
      # todo узнать у всех год рождения
      chunks.append(f"• <b>{name}</b> - {format_date(birthday)}") # ({age} лет)
    
    await update.message.reply_text("\n".join(chunks), parse_mode="HTML")
      
  except Exception as e:
    logging.error(f"Error in list_birthdays: {e}")
    await update.message.reply_text(f"Ошибка при получении списка: {e}")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Show help information."""
  help_text = (
    f"🎂 <b>Birthday Bot - Команды</b>\n\n"
    f"<b>/start</b> - Запустить бота и запланировать уведомления\n"
    f"<b>/list</b> - Показать все дни рождения\n"
    f"<b>/check</b> - Проверить запланированные уведомления\n"
    f"<b>/stop</b> - Остановить все уведомления\n"
    f"<b>/help</b> - Показать эту справку\n\n"
    f"<i>Бот автоматически отправляет уведомления о днях рождения в 9:00 МСК</i>"
  )

  await update.message.reply_text(help_text, parse_mode="HTML")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
    f"<b>Неизвестная команда</b>\n\n"
    f"Вот список доступных команд:\n",
    parse_mode="HTML"
  )
  await help(update, context)  # call /help

def main() -> None:
  if not TOKEN: return logging.error("Требуется TELEGRAM_TOKEN в .env")

  application = Application.builder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("stop", stop))
  application.add_handler(CommandHandler("check", check))
  application.add_handler(CommandHandler("list", list))
  application.add_handler(CommandHandler("help", help))

  # schedule_birthday_tasks(application.job_queue)

  # Обработчик для неизвестных команд
  application.add_handler(MessageHandler(filters.COMMAND, unknown))

  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()