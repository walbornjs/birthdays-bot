import locale

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
  
# def format_date(date_obj, logger):
#   """Format a date object to Russian date string."""
#   try:
#     # Try to set Russian locale
#     locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
#   except locale.Error:
#     try:
#       locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
#     except locale.Error:
#       logger.warning("Russian locale not available, using default")
  
#   try:
#     # Russian month names
#     month_names = [
#       "января", "февраля", "марта", "апреля", "мая", "июня",
#       "июля", "августа", "сентября", "октября", "ноября", "декабря"
#     ]
#     return f"{date_obj.day} {month_names[date_obj.month - 1]}"
#   except (IndexError, AttributeError):
#     return date_obj.strftime("%d.%m")