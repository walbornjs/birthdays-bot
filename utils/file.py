import json
from datetime import datetime

def load(file, values):
  """Load birthdays from JSON file."""
  try:
    with open(file, "r", encoding="utf-8") as f:
      data = json.load(f)
      return data.get("values", values)
  except FileNotFoundError:
    # Create file with default data
    save(file, values)
    return values
  except Exception as e:
    # logger.error(f"Error loading birthdays: {e}")
    return values
  

def save(file, values: list):
  """Save data to JSON file"""
  data = {
    "values": values,
    "updated_at": datetime.now().isoformat()
  }
  with open(file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
