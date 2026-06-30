import re
from datetime import datetime, timedelta

class SmartCaptureService:
    def parse_input(self, text: str):
        text = text.strip()
        result = {
            "type": "task",
            "title": text,
            "due_date": None,
            "time": None,
            "confidence": 50
        }
        
        low_text = text.lower()
        
        if "reunião" in low_text or "call" in low_text or "visita" in low_text:
            result["type"] = "event"
            result["confidence"] += 20
        elif "ideia" in low_text or "insight" in low_text:
            result["type"] = "idea"
            result["confidence"] += 20
            
        today = datetime.now()
        if "hoje" in low_text:
            result["due_date"] = today.strftime("%Y-%m-%d")
            result["confidence"] += 10
        elif "amanhã" in low_text or "amanha" in low_text:
            result["due_date"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
            result["confidence"] += 10
        elif "sexta" in low_text:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            result["due_date"] = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            result["confidence"] += 10
            
        time_match = re.search(r'\b([01]?[0-9]|2[0-3])(?::([0-5][0-9]))?h?\b', low_text)
        if time_match and "h" in time_match.group(0):
             hr = time_match.group(1)
             mn = time_match.group(2) or "00"
             result["time"] = f"{hr.zfill(2)}:{mn}"
             result["confidence"] += 10
             
        clean_title = re.sub(r'\b(hoje|amanhã|amanha|sexta|às|as|\d{1,2}h)\b', '', text, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        if clean_title:
            result["title"] = clean_title
            
        return result
