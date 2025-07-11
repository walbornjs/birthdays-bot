import json
from datetime import datetime, time, timezone, timedelta, date

# Database of birthdays with JSON file persistence
# 
def load(file, default_value):
  """Load birthdays from JSON file."""
  try:
    with open(file, "r", encoding="utf-8") as f:
      data = json.load(f)
      return data.get("birthdays", default_value)
  except FileNotFoundError:
    # Create file with default data
    save_birthdays(default_value)
    return default_value
  except Exception as e:
    # logger.error(f"Error loading birthdays: {e}")
    return default_value

def save(birthdays):
  """Save birthdays to JSON file."""
  # try:
  data = {
    "birthdays": birthdays,
    "last_updated": datetime.now().isoformat()
  }
  with open("birthdays.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
  # except Exception as e:
    # logger.error(f"Error saving birthdays: {e}")

def get_persons(logger):
  """Get current list of persons with parsed dates."""
  birthdays = load('birthdays.json', [])
  persons = []
  for entry in birthdays:
    try:
      birthday = datetime.fromisoformat(entry["birthday"]).date()
      persons.append({
        "name": entry["name"],
        "birthday": birthday
      })
    except Exception as e:
      logger.error(f"Error parsing birthday for {entry.get('name', 'unknown')}: {e}")
  return persons