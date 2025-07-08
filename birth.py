#!/usr/bin/env python
# pylint: disable=unused-argument

import os
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta, date
import logging
import locale
from pymorphy3 import MorphAnalyzer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

MOSCOW_TZ = timezone(timedelta(hours=3))

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
HOUR = 9
MINUTE = 0

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

morph = MorphAnalyzer()

def decline_name(name, case):
  parsed = morph.parse(name)[0]
  return parsed.inflect({case}).word.capitalize() if parsed.inflect({case}) else name

# База данных дней рождения
PERSONS = [
  {"name": "Платон", "birthday": date(2000, 1, 15)}, # 15.01.2000
  {"name": "Черный Витя", "birthday": date(2000, 5, 29)}, # 29.05.2000
  {"name": "Эмиль", "birthday": date(2000, 12, 8)}, # 08.12.2000
  {"name": "Аня Новицкая", "birthday": date(2017, 10, 22)}, # 22.10.2017
  {"name": "Нина Черная", "birthday": date(2020, 8, 18)}, # 18.08.2020
  {"name": "Агата", "birthday": date(2019, 6, 20)}, # 20.06.2019
  {"name": "Левон", "birthday": date(2018, 6, 10)}, # 10.06.2018
  {"name": "Миша", "birthday": date(2020, 10, 19)}, # 20.10.2020
  {"name": "Мила", "birthday": date(2020, 7, 19)}, # 19.07.2020
  {"name": "Аврора", "birthday": date(2021, 6, 19)}, # 19.06.2021
  {"name": "Вера", "birthday": date(2018, 5, 6)}, # 05.06.2018
  {"name": "Мира", "birthday": date(2020, 11, 6)}, # 06.11.2020
  {"name": "Вероника", "birthday": date(2000, 5, 4)}, # 04.05.2000
]

try:
  locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
  locale.setlocale(locale.LC_TIME, 'ru_RU')

def format_date(date):
  try:
    # Форматируем дату в нужный вид: "%d %B" → день + название месяца
    return date.strftime("%-d %B").lower()
  except (ValueError, AttributeError):
    month_names = {
      1: "января", 2: "февраля", 3: "марта", 4: "апреля",
      5: "мая", 6: "июня", 7: "июля", 8: "августа",
      9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    return f"{date.day} {month_names[date.month]}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Initializes the bot."""
  message_text = (
    f"🎂 <b>Привет!</b>\n\n"
    f"Я - <i>бот-о-днях-рождения-напоминатель</i>.\n"
    f"Вы выпустили меня из кувшина!\n<code>"
    f"⠀⠀⠀⠀⣶⣄⠀⠀⠀⠀⠀⠀⢀⣶⡆⠀⠀⠀\n"
    f"⠀⠀⠀⢸⣿⣿⡆⠀⠀⠀⠀⢀⣾⣿⡇⠀⠀⠀\n"
    f"⠀⠀⠀⠘⣿⣿⣿⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠀\n"
    f"⠀⠀⠀⠀⢿⣿⣿⣤⣤⣤⣤⣼⣿⡿⠃⠀⠀⠀\n"
    f"⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣆⠀⠀⠀\n"
    f"⠀⠀⢠⣿⡃⣦⢹⣿⣟⣙⣿⣿⠰⡀⣿⣇⠀⠀\n"
    f"⠠⠬⣿⣿⣷⣶⣿⣿⣿⣿⣿⣿⣷⣾⣿⣿⡭⠤\n"
    f"⠀⣼⣿⣿⣿⣿⠿⠛⠛⠛⠛⠻⢿⣿⣿⣿⣿⡀\n"
    f"⢰⣿⣿⣿⠋⠀⠀⠀⢀⣀⠀⠀⠀⠉⢿⣿⣿⣧\n"
    f"⢸⣿⣿⠃⠜⠛⠂⠀⠋⠉⠃⠐⠛⠻⠄⢿⣿⣿\n"
    f"⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿\n"
    f"⠘⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⡏\n"
    f"⠀⠈⠻⠿⣤⣀⡀⠀⠀⠀⠀⠀⣀⣠⠾⠟⠋⠀\n\n\n"
    f"... ждём 🎂...</code>"
  )
  await update.message.reply_text(
    text=message_text,
    parse_mode="HTML"
  )

  await schedule_birthday_tasks(update, context.job_queue)


def get_job_data(update: Update, person) -> tuple:
  """Generate job data"""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id

  name = person["name"]
  bday = person["birthday"]

  return chat_id, thread_id, name, bday


def get_job_name(update: Update, person) -> str:
  """Generate job name"""
  chat_id, thread_id, name, bday = get_job_data(update, person)
  # when = datetime.combine(bday, time(hour=9, minute=0), tzinfo=MOSCOW_TZ)
  return f"{chat_id}_{thread_id}_{name}_{bday}"


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Check what birthdays notifications we have"""

  for person in PERSONS:
    job_name = get_job_name(update, person)
    jobs = context.job_queue.get_jobs_by_name(job_name)
    if not jobs:
      text = f"🥸 Неужели пользователь {person['name']} не празднует день рождения?"
      await update.effective_message.reply_text(text)
    else:
      text = f"✅ Уведомление для {person['name']} установлено!"
      await update.effective_message.reply_text(text)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove the notification job."""
  for person in PERSONS:
    job_name = get_job_name(update, person)
    jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in jobs:
      job.schedule_removal()
    if jobs:
      text = f"✅ Уведомление для {person['name']} отменено!"
      await update.effective_message.reply_text(text)

  await update.message.reply_text(f"Бот уехал на каникулы! 🌴")


async def schedule_birthday_tasks(update: Update, job_queue) -> None:
  """Shedules tasks for sending birthday reminders."""
  now = datetime.now(MOSCOW_TZ)

  for person in PERSONS:
    chat_id, message_thread_id, name, bday = get_job_data(update, person)
    
    when = datetime.combine(bday.replace(year=now.year), time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)
    # when = datetime.combine(bday.replace(year=now.year), time(hour=now.hour, minute=now.minute, second=now.second + 3), tzinfo=MOSCOW_TZ)
    # early = datetime.combine(bday.replace(year=now.year) - timedelta(days=10), time(hour=HOUR + 1, minute=MINUTE), tzinfo=MOSCOW_TZ)
    early = datetime.combine(bday.replace(year=now.year) - timedelta(days=10), time(hour=now.hour, minute=now.minute, second=now.second + 3), tzinfo=MOSCOW_TZ)
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
    message_text = (
      f"🎉 Сегодня день рождения у <b>{decline_name(name, 'gent')}</b><code>!\n\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡖⠙⡢⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⡿⣿⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠶⠞⠛⠿⣿⣿⡿⣿⣇⡀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡾⠋⢠⠄⠀⠀⠀⠀⠈⠉⡉⠈⠛⢦⡀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⣤⠀⠀⠀⠀⠀⠻⢦⣴⣀⣀⠀⠀⠀⠀⢈⠁⣀⡄⠀⠹⣆⠀⠀⠀\n"
      f"⠀⠀⠀⠀⢰⠓⡄⠀⠀⠀⠀⠀⢸⡇⠉⠉⠙⠛⠛⠛⠛⠛⠉⠀⠀⠀⠹⣆⠀⠀\n"
      f"⢠⣒⣊⢍⣩⢙⣩⣍⡩⡇⠀⠀⢸⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡀⠀\n"
      f"⣸⣀⣈⣁⣀⣉⣀⣀⣠⣇⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡆⠘⣇⠀\n"
      f"⠉⠉⠉⠛⠿⠻⣯⠉⠉⠉⠀⢀⣾⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⢿⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠈⢳⣄⠀⢠⡞⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⢸⡇\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠋⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⠁⠀⠘⣇\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⠀⠀⠀⣿\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠟⠁⠀⠀⢻\n\n"
      f"... поздравляем ...</code>"
    )
    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )
  except Exception as e:
    logging.error(f"Ошибка отправки уведомления: {e}")
  
  # Planning the next birthday reminder (in the next year)
  next_year = datetime.now(MOSCOW_TZ).year + 1
  next_bday = birthday.replace(year=next_year)
  when = datetime.combine(next_bday, time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)

  context.job_queue.run_once(
    callback=send_birthday_reminder_and_create_next,
    when=when,
    data=job.data,
    name=job.name
  )
  logging.info(f"Перепланировано напоминание для {decline_name(name, 'gent')} на {when}")


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
      f"              ⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠀⠀⠀⢀⣞⠇⠀⠀⠀⣀⣤⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢶⣄⢸⢸⠀⢀⣴⡿⠋⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠤⣤⣠⠤⠤⣌⣻⣿⠘⣧⢻⡯⢚⡭⠒⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠳⠶⣆⣠⣔⡒⠚⠛⠓⠀⠈⠉⠀⠁⠉⠀⠉⠉⠉⠉⢑⠢⣄⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠚⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⣗⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⣰⢯⡶⠋⠁⠀⠀⠀⠀⠀⢀⠀⡴⡄⠠⣄⠀⠀⢀⠀⠀⠀⠀⠀⠈⢣⡀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⣡⠏⢀⠀⢀⣴⠂⡔⢀⣴⣏⡼⠁⠘⢦⡙⢷⢤⡈⢳⢤⡀⡀⢠⠸⣎⡇⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⣤⣞⣥⣾⡃⢠⠋⣼⣾⣣⠋⢸⠞⠀⠀⠀⠀⠈⠓⠷⠌⠻⠇⠙⢷⢸⢷⠋⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⢛⡟⠀⡇⡤⠟⠺⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠤⠠⢼⡞⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⣠⢎⣠⡴⠛⠠⣶⡆⠘⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠁⢰⣶⠀⡷⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠉⠩⢯⣦⠟⠦⣌⡠⠞⠀⠀⠀⠀⠀⠀⠃⠀⠀⠀⠈⠣⡄⣀⠴⡇⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡏⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠀⠤⢀⣀⠀⠀⠀⠀⠀⠀⢹⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢳⡀⠀⠀⠀⢀⡠⠖⠉⠀⠀⠀⠀⠀⠀⠉⠓⢦⡀⠀⠀⡜⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠒⠓⠦⣀⠀⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡠⠞⠢⣄⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⣠⠚⠁⠀⠀⠀⠀⢀⠉⠑⠒⠤⠄⠄⠤⠀⠤⠠⠤⠄⠒⠂⢡⠀⠀⠀⠈⠑⢦⡀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⢰⠃⠀⠀⠠⣀⡀⠀⢘⣆⢀⡤⠔⠒⠊⠈⠁⠈⠉⠒⠒⢤⣠⠃⠀⢀⣀⠀⠀⠀⣹⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠈⢧⡾⠋⠙⠶⢵⣤⠋⡞⢁⡠⠔⠂⠈⠀⠀⠀⠈⠉⠒⢦⡘⡏⡦⠥⠶⠮⠌⢲⠁⠀⠀\n"
      f"⠀⠀⠀⠀⢀⠴⡎⠀⠀⠀⠀⠀⢰⡁⢳⠊⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢱⢃⣼⠀⠀⠀⠀⠈⣧⠀⠀\n"
      f"⠀⠀⠀⡰⠋⠀⠳⣄⣀⣀⣀⡠⠤⣝⠲⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣠⢧⡀⠀⠀⠀⢀⡼⢤⡀\n"
      f"⠀⢀⡞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠒⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡏⠁⠀⠉⠒⠤⠒⠋⠀⠀⢹\n"
      f"⢠⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸\n"
      f"⠸⡤⠤⠒⠒⢲⡀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣆⠂⠈⠁⠉⠉⠉⠉⠉⢒⡼⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣜\n"
      f"⠀⠀⠀⠀⠀⢸⠱⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⣒⣒⣂⠤⠔⠒⠊⠉⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⡏⠀\n"
      f"⠀⠀⠀⠀⠀⠈⡄⠈⠒⠤⣀⣀⠤⠄⠒⠊⠉⠁⠀⠀⠈⠉⠑⠢⢄⣀⠀⠀⠀⠀⠀⣀⠤⠚⠁⠀⡇⠀\n"
      f"⠀⠀⠀⠀⠀⠀⢣⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠋⠉⠁⠀⠀⠀⠀⢸⠁⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠈⢧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠏⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠈⠑⠒⠘⠢⢄⣀⠀⠀⢄⣀⠠⠞⠉⢧⡀⠀⠀⠀⢀⠀⠀⣀⠤⠄⠚⠁⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⢸⠀⠀⠀⠀⠀⠉⠑⡖⠒⠈⡽⠉⠁⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡀⠀⢸⠘⠀⠀⠀⠀⠀⠀⡇⠀⢰⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⣀⡀⠀⢀⡠⠤⠒⠒⠒⠃⠀⠘⠦⢄⣀⡀⠀⠀⢠⠁⠀⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠻⠵⠶⠐⠒⢲⠞⠀⢀⡤⠀⠤⢄⢉⡶⠖⠋⠀⠀⠈⢭⡉⠉⠒⠲⠤⡀⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⢃⣠⠴⠋⠀⠀⠀⢠⢋⣀⠤⠒⠒⠒⠦⣄⠈⠻⡅⠉⠉⠁⠀⠀⠀\n"
      f"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⠀⠀⠀⠀⠀⠉⠀⠀⠀⠀⠀⠀⠀⠉⠓⠃⠀⠀⠀⠀⠀⠀\n\n"
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
  
  # Planning the next birthday reminder (in the next year)
  next_year = datetime.now(MOSCOW_TZ).year + 1
  next_bday = birthday.replace(year=next_year)
  early = datetime.combine(next_bday, time(hour=HOUR + 1, minute=MINUTE), tzinfo=MOSCOW_TZ)

  context.job_queue.run_once(
    callback=send_early_birthday_reminder_and_create_next,
    when=early,
    data=job.data,
    name=job.name
  )
  logging.info(f"Перепланировано напоминание для {decline_name(name, 'gent')} на {early}")


def main() -> None:
  if not TOKEN: return logging.error("Требуется TELEGRAM_TOKEN в .env")

  application = Application.builder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("stop", stop))
  application.add_handler(CommandHandler("check", check))

  # schedule_birthday_tasks(application.job_queue)

  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()