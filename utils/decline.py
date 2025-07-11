from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()

def decline_name(name, case):
  parsed = morph.parse(name)[0]
  return parsed.inflect({case}).word.capitalize() if parsed.inflect({case}) else name
