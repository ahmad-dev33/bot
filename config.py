import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    
    # إعدادات الإعلانات
    ADSTERRA_ADS = {
        1: {
            "url": f"https://www.profitableratecpm.com/u59nbgqv?key={os.getenv('ADSTERRA_ADS_KEY_1')}",
            "title": "إعلان Adsterra المميز",
            "reward": 3,
            "cooldown": 24
        },
        2: {
            "url": f"https://www.profitableratecpm.com/u59nbgqv?key={os.getenv('ADSTERRA_ADS_KEY_2')}",
            "title": "إعلان Adsterra العادي",
            "reward": 2,
            "cooldown": 12
        }
    }
