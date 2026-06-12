import requests
import time
import json
import logging
from datetime import datetime

# ========== الإعدادات ==========
TELEGRAM_TOKEN = "8817863207:AAFI3hSHwqiP8hhlA4SgFXz8gteNz7lwPDE"
CHAT_ID = "5636525853"
CHECK_INTERVAL = 60  # كل 60 ثانية

# مراكز VFS في الجزائر
CENTERS = {
    "Algiers":    "Algeria-Algiers",
    "Annaba":     "Algeria-Annaba",
    "Constantine":"Algeria-Constantine",
    "Oran":       "Algeria-Oran",
    "Adrar":      "Algeria-Adrar",
}

# أنواع الفيزا المطلوبة (يمكن تعديلها)
VISA_TYPES = ["Study", "Student"]

# ========== Logging ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("vfs_monitor.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ========== إرسال رسالة تيليجرام ==========
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            log.info("✅ تم إرسال الإشعار بنجاح")
        else:
            log.warning(f"⚠️ فشل الإرسال: {r.text}")
    except Exception as e:
        log.error(f"❌ خطأ في إرسال التيليجرام: {e}")

# ========== فحص مواعيد VFS ==========
def check_appointments():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://visa.vfsglobal.com/",
        "Origin": "https://visa.vfsglobal.com"
    }

    found_slots = []

    for city, center_code in CENTERS.items():
        try:
            # VFS Global API للتحقق من المواعيد
            url = f"https://visa.vfsglobal.com/api/appointments/slots?missionCode=ITA&locationCode={center_code}"
            
            response = requests.get(url, headers=headers, timeout=15)
            log.info(f"🔍 فحص {city}: status={response.status_code}")

            if response.status_code == 200:
                data = response.json()
                
                # البحث عن مواعيد متاحة
                if isinstance(data, list):
                    for slot in data:
                        visa_cat = slot.get("visaCategory", "")
                        available = slot.get("slots", 0)
                        date = slot.get("date", "")
                        
                        is_study = any(v.lower() in visa_cat.lower() for v in VISA_TYPES)
                        
                        if available and available > 0:
                            found_slots.append({
                                "city": city,
                                "visa_type": visa_cat,
                                "date": date,
                                "slots": available,
                                "is_study": is_study
                            })
                
                elif isinstance(data, dict):
                    slots_list = data.get("slots", data.get("appointments", data.get("data", [])))
                    for slot in slots_list:
                        visa_cat = slot.get("visaCategory", slot.get("category", ""))
                        available = slot.get("availableSlots", slot.get("slots", 0))
                        date = slot.get("date", slot.get("appointmentDate", ""))
                        
                        if available and int(available) > 0:
                            found_slots.append({
                                "city": city,
                                "visa_type": visa_cat,
                                "date": date,
                                "slots": available,
                                "is_study": any(v.lower() in visa_cat.lower() for v in VISA_TYPES)
                            })

            elif response.status_code == 401:
                log.warning(f"⚠️ {city}: يحتاج تسجيل دخول")
            elif response.status_code == 403:
                log.warning(f"⚠️ {city}: محجوب (403)")
            else:
                log.warning(f"⚠️ {city}: {response.status_code}")

        except requests.exceptions.Timeout:
            log.warning(f"⏱️ {city}: timeout")
        except Exception as e:
            log.error(f"❌ خطأ في فحص {city}: {e}")

    return found_slots

# ========== تنسيق الإشعار ==========
def format_notification(slots):
    study_slots = [s for s in slots if s["is_study"]]
    other_slots = [s for s in slots if not s["is_study"]]
    
    msg = "🇮🇹 <b>تنبيه VFS إيطاليا - الجزائر</b>\n"
    msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    if study_slots:
        msg += "📚 <b>مواعيد فيزا الدراسة:</b>\n"
        for s in study_slots:
            msg += f"  📍 <b>{s['city']}</b>\n"
            msg += f"  📅 التاريخ: {s['date']}\n"
            msg += f"  🎓 النوع: {s['visa_type']}\n"
            msg += f"  ✅ المواعيد المتاحة: {s['slots']}\n\n"

    if other_slots:
        msg += "🗂️ <b>مواعيد أخرى متاحة:</b>\n"
        for s in other_slots:
            msg += f"  📍 {s['city']} | {s['visa_type']} | {s['date']} | {s['slots']} مواعيد\n"

    msg += "\n🔗 <a href='https://visa.vfsglobal.com/dza/en/ita'>احجز الآن - VFS Global</a>"
    return msg

# ========== الحلقة الرئيسية ==========
def main():
    log.info("=" * 50)
    log.info("🤖 بدء تشغيل بوت مراقبة VFS إيطاليا - الجزائر")
    log.info(f"📍 المراكز: {', '.join(CENTERS.keys())}")
    log.info(f"⏱️ فترة الفحص: كل {CHECK_INTERVAL} ثانية")
    log.info("=" * 50)

    # إشعار بدء التشغيل
    send_telegram(
        "🤖 <b>بوت VFS إيطاليا يعمل الآن!</b>\n\n"
        f"📍 يراقب المراكز التالية:\n"
        + "\n".join([f"  • {city}" for city in CENTERS.keys()])
        + f"\n\n⏱️ فحص كل {CHECK_INTERVAL} ثانية\n"
        "📚 يبحث عن: فيزا دراسة + جميع الأنواع"
    )

    last_slots_hash = ""

    while True:
        try:
            log.info(f"\n🔄 جاري الفحص... {datetime.now().strftime('%H:%M:%S')}")
            
            slots = check_appointments()
            
            if slots:
                # تحويل النتائج لـ hash لتجنب الإشعارات المكررة
                slots_hash = json.dumps(slots, sort_keys=True)
                
                if slots_hash != last_slots_hash:
                    log.info(f"🎉 وجدنا {len(slots)} موعد متاح!")
                    notification = format_notification(slots)
                    send_telegram(notification)
                    last_slots_hash = slots_hash
                else:
                    log.info(f"ℹ️ نفس المواعيد السابقة ({len(slots)} موعد) - لا إشعار جديد")
            else:
                log.info("❌ لا توجد مواعيد متاحة حالياً")
                # إعادة تعيين الـ hash عند عدم وجود مواعيد
                last_slots_hash = ""

        except KeyboardInterrupt:
            log.info("\n⛔ تم إيقاف البوت يدوياً")
            send_telegram("⛔ تم إيقاف بوت VFS.")
            break
        except Exception as e:
            log.error(f"❌ خطأ غير متوقع: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
