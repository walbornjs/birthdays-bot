#!/usr/bin/env python
# pylint: disable=unused-argument

import os
from dotenv import load_dotenv
from datetime import date, datetime, time, timezone, timedelta
import re
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

MOSCOW_TZ = timezone(timedelta(hours=3))

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

persons = [
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
  {"name": "Vasya Pupkin", "birthday": datetime.now() + timedelta(seconds=30)}, # 04.05.2000
]


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#   """Sends explanation on how to use the bot."""
#   await update.message.reply_text("Hi! Use `/notify HH:MM` to set notifications")


def format_timedelta(delta: timedelta) -> str:
  """Format timedelta to human-readable string."""
  total_seconds = int(delta.total_seconds())
  days, remainder = divmod(total_seconds, 86400)
  hours, remainder = divmod(remainder, 3600)
  minutes, seconds = divmod(remainder, 60)
  
  parts = []
  if days > 0:
    parts.append(f"{days} д.")
  if hours > 0:
    parts.append(f"{hours} ч.")
  if minutes > 0:
    parts.append(f"{minutes} мин.")
  if seconds > 0 or not parts:  # Показываем секунды, если нет других компонентов
    parts.append(f"{seconds} сек.")
  
  return " ".join(parts)


async def check_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Check time left until next notification"""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id
  job_name = f"notify_{chat_id}_{thread_id}"
  
  jobs = context.job_queue.get_jobs_by_name(job_name)
  if not jobs:
    await update.effective_message.reply_text("🥸 У вас нет активных уведомлений.")
    return
  
  # We have only one
  job = jobs[0]

  now = datetime.now(timezone.utc)
  next_run = job.next_t
  
  # Calculate time left until next run
  time_left = next_run - now
  
  # If time already passed (might happen due to exact match)
  if time_left.total_seconds() < 0:
    # Calculate time left until next run (tomorrow at the same time)
    next_run += timedelta(days=1)
    time_left = next_run - now
  
  # Format time left
  time_left_str = format_timedelta(time_left)
  
  next_run = next_run.astimezone(MOSCOW_TZ)
  next_time_str = next_run.strftime("%H:%M")

  message_text = (
    f"🚀 <b>Следующее уведомление</b>\n\n"
    f"• Время: <code>{next_time_str}</code> (МСК)\n"
    f"• Осталось: <b>{time_left_str}</b>"
  )
  await update.effective_message.reply_text(message_text, parse_mode="HTML")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
  """Remove job with given name. Returns whether job was removed."""
  current_jobs = context.job_queue.get_jobs_by_name(name)
  if not current_jobs:
    return False
  for job in current_jobs:
    job.schedule_removal()
  return True


async def scheduled_message(context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send the scheduled message."""
  job = context.job
  await context.bot.send_message(
    chat_id=job.data["chat_id"],
    message_thread_id=job.data["thread_id"],
    text=f"🔔 Напоминание! Время: <b>{job.data['scheduled_time']}</b>",
    parse_mode="HTML"
  )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Set birthdays notifications"""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id
  
  job_data = {
    "chat_id": chat_id,
    "thread_id": thread_id,
  }

  for person in persons:
    day = person["birthday"].day
    month = person["birthday"].month

    context.job_queue.run_once(
      callback=scheduled_message,
      time=time(9, 0, tzinfo=MOSCOW_TZ),
      day=day,
      month=month,
      name=f"{chat_id}_{thread_id}_{person['name']}",
      data=job_data
    )


    text = f"⏰ Посмотрим, посмотрим, когда там у кого-то день рождения!"
    await update.effective_message.reply_text(text)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove the notification job."""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id

  for person in persons:
    name=f"{chat_id}_{thread_id}_{person['name']}"
    jobs = context.job_queue.get_jobs_by_name(name)
    for job in jobs:
      job.schedule_removal()
    if jobs:
      text = f"✅ Уведомление для {person['name']} отменено!"
      await update.effective_message.reply_text(text)
    
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Приветственное сообщение"""
#     await update.message.reply_text(
#         "🎂 Бот-напоминатель о днях рождения!\n"
#         "Я буду автоматически оповещать о днях рождения каждый день в 9:00 по МСК."
#     )
    
#     # Если это первый запуск, устанавливаем задачу
#     if not context.job_queue.get_jobs_by_name("birthday_checker"):
#         context.job_queue.run_daily(
#             check_birthdays,
#             time=time(hour=9, minute=0, tzinfo=MOSCOW_TZ),
#             days=tuple(range(7)),
#             name="birthday_checker"
#         )

def main() -> None:
  """Run bot."""
  # Create the Application and pass it your bot's token.
  application = Application.builder().token(TOKEN).build()

  # on different commands - answer in Telegram
  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("stop", stop))

  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()
