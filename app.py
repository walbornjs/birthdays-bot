#!/usr/bin/env python
# pylint: disable=unused-argument

import os
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta, date
import logging
import re

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from utils.ansii import totoro, meow, kaomoji, disnay
from utils.decline import decline_name
from utils.date import format_date
from utils.file import load, save

MOSCOW_TZ = timezone(timedelta(hours=3))

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
# HOUR = 9
# MINUTE = 0

HOUR = datetime.now(MOSCOW_TZ).hour
MINUTE = datetime.now(MOSCOW_TZ).minute + 1

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
  chat_id = update.effective_chat.id
  message_thread_id = update.effective_message.message_thread_id

  name = person["name"]
  bday = person["birthday"]

  return chat_id, message_thread_id, name, bday


def get_job_name(update: Update, person) -> str:
  """Generate job name"""
  chat_id, message_thread_id, name, bday = get_job_data(update, person)
  return f"{chat_id}_{message_thread_id}_{name}_{bday}"


def remove_existing_jobs(job_queue, job_name_base):
  """Remove existing jobs for a person"""
  removed_count = 0
  for job in job_queue.jobs():
    if job.name.startswith(job_name_base):
      job.schedule_removal()
      removed_count += 1
      logging.info(f"Removed existing job: {job.name}")
  return removed_count


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
    sorted_jobs = sorted(jobs, key=lambda x: x.next_t)
    
    for job in sorted_jobs:
      if hasattr(job, 'data') and 'name' in job.data:
        name = job.data['name']
        when = job.next_t.astimezone(MOSCOW_TZ)
        when_str = when.strftime("%d.%m.%Y %H:%M")
        reminder_type = "⏳ Предупреждение" if "early" in job.name else "🎂 День рождения"
        message_parts.append(f"• {reminder_type}: <b>{name}</b> - {when_str}")
    
    full_message = "📅 <b>Запланированные уведомления:</b>\n\n" + "\n".join(message_parts)
    await update.message.reply_text(full_message, parse_mode="HTML")
      
  except Exception as e:
    logging.error(f"Error in /check command: {e}", exc_info=True)
    await update.message.reply_text(f"❌ Ошибка при проверке: {e}", parse_mode="HTML")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove all notification jobs."""
  try:
    jobs = context.job_queue.jobs()
    removed_count = 0
    
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
    logging.error(f"Error in stop command: {e}", exc_info=True)
    await update.message.reply_text(f"❌ Ошибка при остановке: {e}", parse_mode="HTML")

async def schedule_birthday_tasks(update: Update, job_queue) -> None:
  """Schedules tasks for sending birthday reminders."""
  now = datetime.now(MOSCOW_TZ)
  persons = get_persons()

  for person in persons:
    chat_id, message_thread_id, name, bday = get_job_data(update, person)
    
    when = datetime.combine(bday.replace(year=now.year), time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)
    early = datetime.combine(bday.replace(year=now.year) - timedelta(days=10), time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)
    
    if when < now: 
      when = when.replace(year=now.year + 1)
    if early < now: 
      early = early.replace(year=now.year + 1)
  
    job_data = {
      "chat_id": chat_id,
      "message_thread_id": message_thread_id,
      "name": name,
      "birthday": bday,
      "when": when,
      "early": early,
    }

    base_job_name = get_job_name(update, person)
    
    # Удаляем существующие задания для этого человека
    remove_existing_jobs(job_queue, base_job_name)

    # Создаем новые задания
    job_queue.run_once(
      callback=send_birthday_reminder_and_create_next,
      when=when,
      data=job_data,
      name=base_job_name
    )

    job_queue.run_once(
      callback=send_early_birthday_reminder_and_create_next,
      when=early,
      data=job_data,
      name=f"{base_job_name}_early"
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
      f"🎉 Сегодня день рождения у <b>{decline_name(name, 'gent')}</b>!\n\n"
      f"🎂 {decline_name(name, 'datv')} исполняется {age} лет!\n\n"
      f"<code>{meow}</code>\n\n"
      f"... поздравляем ..."
    )
    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )

    logging.info(f"Sent birthday notification for {name}")
  except Exception as e:
    logging.error(f"Error sending birthday notification: {e}", exc_info=True)
  
  # Schedule next year's notification
  try:
    next_year = datetime.now(MOSCOW_TZ).year + 1
    next_bday = birthday.replace(year=next_year)
    when = datetime.combine(next_bday, time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)

    # Обновляем данные для нового задания
    job.data["when"] = when
    job.data["birthday"] = next_bday
    
    context.job_queue.run_once(
      callback=send_birthday_reminder_and_create_next,
      when=when,
      data=job.data,
      name=job.name
    )
    logging.info(f"Rescheduled birthday notification for {decline_name(name, 'gent')} to {when}")
  except Exception as e:
    logging.error(f"Error rescheduling birthday notification: {e}", exc_info=True)


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
      f"🎂 {format_date(birthday)}!\n\n"
      f"<pre>{kaomoji}</pre>\n\n"
      f"... готовим подарки ..."
    )
    await context.bot.send_message(
      chat_id=chat_id,
      message_thread_id=message_thread_id,
      text=message_text,
      parse_mode="HTML",
    )
  except Exception as e:
    logging.error(f"Ошибка отправки уведомления: {e}", exc_info=True)
  
  # Schedule next year's early reminder
  try:
    next_year = datetime.now(MOSCOW_TZ).year + 1
    next_bday = birthday.replace(year=next_year)
    early = datetime.combine(next_bday - timedelta(days=10), time(hour=HOUR, minute=MINUTE), tzinfo=MOSCOW_TZ)

    # Обновляем данные
    job.data["early"] = early
    job.data["birthday"] = next_bday
    
    context.job_queue.run_once(
      callback=send_early_birthday_reminder_and_create_next,
      when=early,
      data=job.data,
      name=job.name
    )
    logging.info(f"Rescheduled early notification for {decline_name(name, 'gent')} to {early}")
  except Exception as e:
    logging.error(f"Error rescheduling early notification: {e}", exc_info=True)


async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """List all birthdays"""
  try:
    persons = get_persons()
    persons.sort(key=lambda x: (x["birthday"].month, x["birthday"].day))
    
    chunks = ["🎂 <b>Список дней рождения:</b>\n"]
    current_year = datetime.now().year
    
    for person in persons:
      name = person["name"]
      birthday = person["birthday"]
      age = current_year - birthday.year
      chunks.append(f"• <b>{name}</b> - {format_date(birthday)} ({age} лет)")
    
    await update.message.reply_text("\n".join(chunks), parse_mode="HTML")
      
  except Exception as e:
    logging.error(f"Error in list_birthdays: {e}", exc_info=True)
    await update.message.reply_text(f"❌ Ошибка при получении списка: {e}", parse_mode="HTML")


async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Add new birthday to the list"""
  try:
    args = context.args
    if len(args) < 2:
      await update.message.reply_text(
        "❌ Неверный формат команды\n"
        "Используйте: /add <Имя> <ДД.ММ.ГГГГ>\n"
        "Пример: /add Анна 15.05.1990"
      )
      return

    name = " ".join(args[:-1])
    date_str = args[-1]
    
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
      await update.message.reply_text(
        "❌ Неверный формат даты\n"
        "Используйте ДД.ММ.ГГГГ (например: 15.05.1990)"
      )
      return

    try:
      birth_date = datetime.strptime(date_str, "%d.%m.%Y").date()
      if birth_date > date.today():
        await update.message.reply_text("❌ Дата рождения не может быть в будущем")
        return
    except ValueError:
      await update.message.reply_text("❌ Некорректная дата")
      return

    persons = get_persons()
    if any(p["name"].lower() == name.lower() for p in persons):
      await update.message.reply_text(f"❌ Имя '{name}' уже существует в списке")
      return

    new_entry = {"name": name, "birthday": birth_date.isoformat()}
    current_data = load('birthdays.json', DEFAULT_PERSONS)
    current_data.append(new_entry)
    save('birthdays.json', current_data)

    await schedule_birthday_tasks(update, context.job_queue)
    
    await update.message.reply_text(
      f"✅ <b>{name}</b> добавлен(а) в список!\n"
      f"Дата рождения: {format_date(birth_date)}",
      parse_mode="HTML"
    )
    
  except Exception as e:
    logging.error(f"Error in add_birthday: {e}", exc_info=True)
    await update.message.reply_text(f"❌ Ошибка при добавлении: {e}", parse_mode="HTML")


async def remove_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Remove birthday from the list"""
  try:
    if not context.args:
      await update.message.reply_text(
        "❌ Укажите имя для удаления\n"
        "Используйте: /remove <Имя>\n"
        "Пример: /remove Анна"
      )
      return

    name_to_remove = " ".join(context.args).strip()
    if not name_to_remove:
      await update.message.reply_text("❌ Имя не может быть пустым")
      return

    current_data = load('birthdays.json', DEFAULT_PERSONS)
    original_count = len(current_data)
    
    # Фильтрация с учетом регистра
    filtered_data = [p for p in current_data if p["name"].lower() != name_to_remove.lower()]
    
    if len(filtered_data) == original_count:
      await update.message.reply_text(f"❌ Не найдено: '{name_to_remove}'")
      return

    save('birthdays.json', filtered_data)
    
    # Удаляем связанные задания
    persons = get_persons()
    removed_person = next((p for p in persons if p["name"].lower() == name_to_remove.lower()), None)
    
    if removed_person:
      chat_id = update.effective_chat.id
      message_thread_id = update.effective_message.message_thread_id
      base_job_name = f"{chat_id}_{message_thread_id}_{removed_person['name']}_{removed_person['birthday']}"
      jobs_removed = remove_existing_jobs(context.job_queue, base_job_name)
    else:
      jobs_removed = 0

    await update.message.reply_text(
      f"✅ <b>{name_to_remove}</b> удален(а) из списка!\n"
      f"Удалено заданий: {jobs_removed}",
      parse_mode="HTML"
    )
    
    # Покажем обновленный список
    await list_birthdays(update, context)
    
  except Exception as e:
    logging.error(f"Error in remove_birthday: {e}", exc_info=True)
    await update.message.reply_text(f"❌ Ошибка при удалении: {e}", parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Show help information."""
  help_text = (
    f"🎂 <b>Birthday Bot - Команды</b>\n\n"
    f"<b>/start</b> - Запустить бота и запланировать уведомления\n"
    f"<b>/add &lt;Имя&gt; &lt;ДД.ММ.ГГГГ&gt;</b> - Добавить новый день рождения\n"
    f"<b>/remove &lt;Имя&gt;</b> - Удалить день рождения\n"
    f"<b>/list</b> - Показать все дни рождения\n"
    f"<b>/check</b> - Проверить запланированные уведомления\n"
    f"<b>/stop</b> - Остановить все уведомления\n"
    f"<b>/help</b> - Показать эту справку\n\n"
    f"<i>Бот автоматически отправляет уведомления:</i>\n"
    f"• За 10 дней до дня рождения\n"
    f"• В сам день рождения\n"
    f"<i>Время: 9:00 МСК</i>"
  )

  await update.message.reply_text(help_text, parse_mode="HTML")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
    f"<b>❌ Неизвестная команда</b>\n\n"
    f"Используйте /help для списка команд",
    parse_mode="HTML"
  )


def main() -> None:
  if not TOKEN: 
    return logging.error("Требуется TELEGRAM_TOKEN в .env")

  application = Application.builder().token(TOKEN).build()

  # Регистрация обработчиков команд
  handlers = [
    CommandHandler("start", start),
    CommandHandler("stop", stop),
    CommandHandler("check", check),
    CommandHandler("list", list_birthdays),
    CommandHandler("add", add_birthday),
    CommandHandler("remove", remove_birthday),
    CommandHandler("help", help_command),
    MessageHandler(filters.COMMAND, unknown)
  ]
  
  for handler in handlers:
    application.add_handler(handler)

  # application.run_polling(allowed_updates=Update.ALL_TYPES)

  return application 


if __name__ == "__main__":
  main()