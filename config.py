import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    
    # إعدادات الإعلانات
    ADSTERRA_ADS = {
        1: {
            "url": "https://www.profitableratecpm.com/u59nbgqv?key=ca64d9af54ff14ecb858b7fef7562b6b",
            "title": "إعلان Adsterra المميز",
            "reward": 3,
            "cooldown": 24
        },
        2: {
            "url": "https://www.profitableratecpm.com/fc0e90z0?key=da338f12e6c8e1219f1ed0ad057ea6b5",
            "title": "إعلان Adsterra العادي",
            "reward": 2,
            "cooldown": 12
        }
    }
