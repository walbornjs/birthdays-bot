#!/usr/bin/env python
# pylint: disable=unused-argument

import os
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Sends explanation on how to use the bot."""
  await update.message.reply_text("Hi! Use `/notify HH:MM` to set notifications")


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
    text=f"🔔 Напоминание! Время: **{job.data['scheduled_time']}**",
    parse_mode="MarkdownV2" 
  )

async def start_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Set daily notification at specified time."""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id
  
  try:
    # Проверяем аргументы команды
    if not context.args:
      raise ValueError("Не указано время")
    
    time_str = context.args[0]
    
    # Проверяем формат времени с помощью регулярного выражения
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_str):
      raise ValueError("Неверный формат времени")
    
    # Разбираем время
    hour, minute = map(int, time_str.split(':'))
    
    # Создаем объект времени
    time_obj = time(hour, minute, tzinfo=MOSCOW_TZ)
    
    # Создаем уникальное имя задания
    job_name = f"notify_{chat_id}_{thread_id}"
    
    # Удаляем старое задание если существует
    job_removed = remove_job_if_exists(job_name, context)
    
    # Создаем данные для задания
    job_data = {
      "chat_id": chat_id,
      "thread_id": thread_id,
      "scheduled_time": time_str
    }
    
    # Создаем задание
    context.job_queue.run_daily(
      callback=scheduled_message,
      time=time_obj,
      days=tuple(range(7)),  # Все дни недели
      name=job_name,
      data=job_data
    )
    
    text = f"⏰ Ежедневное уведомление установлено на {time_str} по MSK!"
    if job_removed:
      text += "\n(Предыдущее уведомление заменено)"
    await update.effective_message.reply_text(text)
    
  except (ValueError, IndexError) as e:
    error_msg = str(e) if str(e) else "Неверный формат времени"
    await update.effective_message.reply_text(
      f"❌ Ошибка: {error_msg}\n"
      "Используйте: /notify ЧЧ:ММ\n"
      "Пример: /notify 09:00"
    )


async def stop_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove the notification job."""
  chat_id = update.effective_message.chat_id
  thread_id = update.effective_message.message_thread_id
  job_name = f"notify_{chat_id}_{thread_id}"
  
  job_removed = remove_job_if_exists(job_name, context)
  text = "❌ Все уведомления отменены!" if job_removed else "🌴 Нет активных уведомлений"
  await update.effective_message.reply_text(text)


def main() -> None:
  """Run bot."""
  # Create the Application and pass it your bot's token.
  application = Application.builder().token(TOKEN).build()

  # on different commands - answer in Telegram
  application.add_handler(CommandHandler(["start", "help"], start))
  application.add_handler(CommandHandler("notify", start_notify))
  application.add_handler(CommandHandler("stop_notify", stop_notify))
  application.add_handler(CommandHandler("check", check_notify))

  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()
