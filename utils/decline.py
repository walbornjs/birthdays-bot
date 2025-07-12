from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()

# def decline_name(name, case):
#   parsed = morph.parse(name)[0]
#   return parsed.inflect({case}).word.capitalize() if parsed.inflect({case}) else name


def decline_name(name: str, case: str) -> str:
  """
  Склоняет имя или имя + фамилию в нужный падеж.
  Поддерживаемые падежи: 'nomn', 'gent', 'datv', 'accs', 'ablt', 'loct'.
  
  Примеры:
    decline_name("Алексей", 'gent') -> "Алексея"
    decline_name("Алексей Иванов", 'datv') -> "Алексею Иванову"
  """
  parts = name.split()
  
  declined_parts = []

  for part in parts:
    parsed = morph.parse(part)[0]
    if parsed.tag.POS == 'NOUN' or 'Name' in parsed.tag:
      declined_part = parsed.inflect({case}).word if parsed.inflect({case}) else part
      declined_parts.append(declined_part.capitalize())
    else:
      declined_parts.append(part)  # Не склоняем, если не имя/фамилия
  
  return ' '.join(declined_parts)