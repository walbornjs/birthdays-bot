import datetime

persons = [
  {"name": "Платон", "birthday": datetime.date(2000, 1, 15)}, # 15.01.2000
  {"name": "Черный Витя", "birthday": datetime.date(2000, 5, 29)}, # 29.05.2000
  {"name": "Эмиль", "birthday": datetime.date(2000, 12, 8)}, # 08.12.2000
  {"name": "Аня Новицкая", "birthday": datetime.date(2017, 10, 22)}, # 22.10.2017
  {"name": "Нина Черная", "birthday": datetime.date(2020, 8, 18)}, # 18.08.2020
  {"name": "Агата", "birthday": datetime.date(2019, 6, 20)}, # 20.06.2019
  {"name": "Левон", "birthday": datetime.date(2018, 6, 10)}, # 10.06.2018
  {"name": "Миша", "birthday": datetime.date(2020, 10, 19)}, # 20.10.2020
  {"name": "Мила", "birthday": datetime.date(2020, 7, 19)}, # 19.07.2020
  {"name": "Аврора", "birthday": datetime.date(2021, 6, 19)}, # 19.06.2021
  {"name": "Вера", "birthday": datetime.date(2018, 5, 6)}, # 05.06.2018
  {"name": "Мира", "birthday": datetime.date(2020, 11, 6)}, # 06.11.2020
  {"name": "Вероника", "birthday": datetime.date(2000, 5, 4)}, # 04.05.2000
]

datetime.datetime.now()

def parse_date(date_str: str) -> datetime.date:

  
  day = int(parts[0])
  month = int(parts[1])
  
  # Обработка года (если не указан, ставим 1900 или текущий)
  if len(parts) >= 3 and parts[2]:
    year = int(parts[2])
    if year < 100:  # Двузначный год (например, "19" → 2019)
      year += 2000 if year < 50 else 1900
  else:
    year = 1900  # Можно заменить на datetime.now().year
  
  return datetime(year=year, month=month, day=day).date()

result = []
for person in persons:
  try:
    result.append({
      "name": person["name"],
      "birthday": parse_date(person["birthday"])
    })
  except (ValueError, IndexError) as e:
    print(f"Ошибка в строке {person}: {e}")