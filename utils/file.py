import json
from datetime import datetime

def load(file, default_value):
  """Load birthdays from JSON file."""
  try:
    with open(file, "r", encoding="utf-8") as f:
      data = json.load(f)
      return data.get("birthdays", default_value)
  except FileNotFoundError:
    # Create file with default data
    save(default_value)
    return default_value
  except Exception as e:
    # logger.error(f"Error loading birthdays: {e}")
    return default_value
  

def save(name: str, data: list):
  """Save data to JSON file"""
  data = {
    name: data,
    "updated_at": datetime.now().isoformat()
  }
  with open("birthdays.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
