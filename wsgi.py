import os
from app import main
from telegram.ext import Application

# Инициализация приложения
app = main()

async def set_webhook():
  await app.bot.set_webhook(
    url="https://walborn.pythonanywhere.com/telegram",
    # Если используете секретный токен:
    # secret_token=os.getenv("WEBHOOK_SECRET")
  )

# Установка вебхука при запуске
if not app.running:
  app.run_webhook(
    listen="127.0.0.1",
    port=5000,
    webhook_url="https://walborn.pythonanywhere.com/telegram",
    secret_token=os.getenv('WEBHOOK_SECRET', ''),
    # cert="ВАШ_СЕРТИФИКАТ.pem"  # Если используете HTTPS
  )

# WSGI-совместимый обработчик
async def application(environ, start_response):
  if environ['PATH_INFO'] == '/telegram' and environ['REQUEST_METHOD'] == 'POST':
    # Передаем запрос в обработчик Telegram
    await app.update_queue.put(
      Update.de_json(
        await app.updater.request.json,
        app.bot
      )
    )
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'OK']
  else:
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found']