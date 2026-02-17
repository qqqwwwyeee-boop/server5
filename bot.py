import telebot
from telebot import types
import requests
import json
from datetime import datetime
import time
import logging
import os

# إعداد التسجيل (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# قراءة المتغيرات من البيئة (Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8023858119:AAHcuoFVKwKgArs3cc6dnaEGY7XpN5Q6Vog")
DEVELOPER_ID = os.environ.get('DEVELOPER_ID', "5981205477")
SERVER_URL = os.environ.get('SERVER_URL', "https://server5-3.onrender.com")

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def server_request(method, endpoint, data=None, max_retries=3):
    """دالة محسنة مع إعادة المحاولة ومعالجة الأخطاء"""
    for attempt in range(max_retries):
        try:
            url = f"{SERVER_URL}/{endpoint}"
            logger.info(f"محاولة {attempt + 1}/{max_retries}: {method} {url}")
            
            if method == "GET":
                response = requests.get(url, timeout=120)  # زيادة المهلة إلى 120 ثانية
            else:
                response = requests.post(url, json=data, timeout=120)
            
            if response.status_code == 200:
                return response.json()
            elif attempt < max_retries - 1:
                logger.warning(f"إعادة محاولة {attempt + 1}/{max_retries} بعد 5 ثواني...")
                time.sleep(5)
                continue
            else:
                logger.error(f"فشل بعد {max_retries} محاولات. Status code: {response.status_code}")
                return {"error": f"http_error_{response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ مهلة الاتصال انتهت (محاولة {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return {"error": "timeout"}
            
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 خطأ في الاتصال (محاولة {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return {"error": "connection"}
            
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {str(e)}")
            return {"error": str(e)}
    
    return {"error": "max_retries_exceeded"}

@bot.message_handler(commands=['start', 'بدء'])
def send_welcome(message):
    if str(message.chat.id) != DEVELOPER_ID:
        bot.reply_to(message, "⛔ هذا البوت للمطور فقط")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔑 تفعيل", callback_data="activate")
    btn2 = types.InlineKeyboardButton("⛔ إيقاف", callback_data="deactivate")
    btn3 = types.InlineKeyboardButton("🔍 تحقق", callback_data="check")
    btn4 = types.InlineKeyboardButton("➕ تمديد", callback_data="extend")
    btn5 = types.InlineKeyboardButton("⏸️ تعليق", callback_data="suspend")
    btn6 = types.InlineKeyboardButton("▶️ استئناف", callback_data="resume")
    btn7 = types.InlineKeyboardButton("📊 إحصائيات", callback_data="stats")
    btn8 = types.InlineKeyboardButton("📋 قائمة", callback_data="list")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    
    welcome = f"""
🔥 بوت تفعيل أشرف
━━━━━━━━━━━━━━━━
👨‍💻 المطور: @AShrf_771117678
🌐 السيرفر: {SERVER_URL}
━━━━━━━━━━━━━━━━

📌 الأوامر:
/تفعيل KEY المدة
/إيقاف KEY
/تحقق KEY
/تمديد KEY المدة
/تعليق KEY ساعة
/استئناف KEY
/إحصائيات
/قائمة
"""
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if str(call.message.chat.id) != DEVELOPER_ID:
        bot.answer_callback_query(call.id, "⛔ غير مصرح")
        return
    
    chat_id = call.message.chat.id
    
    if call.data == "activate":
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("1 شهر", callback_data="months_1"),
            types.InlineKeyboardButton("3 شهور", callback_data="months_3"),
            types.InlineKeyboardButton("6 شهور", callback_data="months_6"),
            types.InlineKeyboardButton("12 شهر", callback_data="months_12"),
            types.InlineKeyboardButton("24 شهر", callback_data="months_24"),
            types.InlineKeyboardButton("دائم", callback_data="months_0"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back")
        )
        bot.send_message(chat_id, "🔑 اختر مدة التفعيل:", reply_markup=markup)
    
    elif call.data.startswith("months_"):
        months = call.data.replace("months_", "")
        if months == "0":
            months_text = "دائم"
        else:
            months_text = f"{months} أشهر"
        msg = bot.send_message(chat_id, f"📝 أرسل المفتاح لتفعيله لمدة {months_text}")
        bot.register_next_step_handler(msg, process_activation, months)
    
    elif call.data == "deactivate":
        msg = bot.send_message(chat_id, "⛔ أرسل المفتاح للإيقاف")
        bot.register_next_step_handler(msg, process_deactivation)
    
    elif call.data == "check":
        msg = bot.send_message(chat_id, "🔍 أرسل المفتاح للتحقق")
        bot.register_next_step_handler(msg, process_check)
    
    elif call.data == "extend":
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("1 شهر", callback_data="extend_1"),
            types.InlineKeyboardButton("3 شهور", callback_data="extend_3"),
            types.InlineKeyboardButton("6 شهور", callback_data="extend_6"),
            types.InlineKeyboardButton("12 شهر", callback_data="extend_12"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back")
        )
        bot.send_message(chat_id, "➕ اختر مدة التمديد:", reply_markup=markup)
    
    elif call.data.startswith("extend_"):
        months = call.data.replace("extend_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل المفتاح لتمديده {months} أشهر")
        bot.register_next_step_handler(msg, process_extend, months)
    
    elif call.data == "suspend":
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("1 ساعة", callback_data="suspend_1"),
            types.InlineKeyboardButton("3 ساعات", callback_data="suspend_3"),
            types.InlineKeyboardButton("6 ساعات", callback_data="suspend_6"),
            types.InlineKeyboardButton("12 ساعة", callback_data="suspend_12"),
            types.InlineKeyboardButton("24 ساعة", callback_data="suspend_24"),
            types.InlineKeyboardButton("48 ساعة", callback_data="suspend_48"),
            types.InlineKeyboardButton("أسبوع", callback_data="suspend_168"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back")
        )
        bot.send_message(chat_id, "⏸️ اختر مدة التعليق:", reply_markup=markup)
    
    elif call.data.startswith("suspend_"):
        hours = call.data.replace("suspend_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل المفتاح لتعليقه {hours} ساعة")
        bot.register_next_step_handler(msg, process_suspend, hours)
    
    elif call.data == "resume":
        msg = bot.send_message(chat_id, "▶️ أرسل المفتاح للاستئناف")
        bot.register_next_step_handler(msg, process_resume)
    
    elif call.data == "stats":
        result = server_request("GET", "stats")
        if result and not result.get("error"):
            stats = result
            msg = f"""
📊 إحصائيات النظام
━━━━━━━━━━━━━━━━
🔑 إجمالي المفاتيح: {stats.get('total_keys', 0)}
✅ نشط: {stats.get('active_keys', 0)}
⏸️ معلق: {stats.get('suspended_keys', 0)}
⛔ موقوف: {stats.get('inactive_keys', 0)}
━━━━━━━━━━━━━━━━
👨‍💻 المطور: @AShrf_771117678
"""
        else:
            msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية وحاول مرة أخرى"
        bot.send_message(chat_id, msg)
    
    elif call.data == "list":
        result = server_request("GET", "list")
        if result and not result.get("error"):
            keys = result.get('keys', [])
            if not keys:
                bot.send_message(chat_id, "📋 لا يوجد عملاء حالياً")
            else:
                msg = "📋 قائمة العملاء\n━━━━━━━━━━━━━━━━\n"
                for k in keys:
                    icon = "✅" if k['status'] == 'active' else "⏸️" if k['status'] == 'suspended' else "⛔"
                    expiry = k['expiry'].replace('T', ' ')[:16] if k['expiry'] != 'permanent' else 'دائم'
                    registered = "🔒" if k.get('registered') else "🆓"
                    msg += f"{icon} {registered} `{k['key']}` - {expiry}\n"
                bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية وحاول مرة أخرى")
    
    elif call.data == "back":
        send_welcome(call.message)
    
    bot.answer_callback_query(call.id)

def process_activation(message, months):
    if str(message.chat.id) != DEVELOPER_ID:
        return
    key = message.text.strip().upper()
    result = server_request("POST", "activate", {"key": key, "months": int(months)})
    if result and not result.get("error"):
        if months == "0":
            msg = f"✅ تم تفعيل المفتاح\n🔑 {key}\n📅 دائم"
        else:
            expiry = result.get('expiry', '').replace('T', ' ')[:16] if 'T' in result.get('expiry', '') else result.get('expiry', '')
            msg = f"✅ تم تفعيل المفتاح\n🔑 {key}\n⏰ المدة: {months} أشهر\n📅 ينتهي: {expiry}"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

def process_deactivation(message):
    if str(message.chat.id) != DEVELOPER_ID:
        return
    key = message.text.strip().upper()
    result = server_request("POST", "deactivate", {"key": key})
    if result and not result.get("error"):
        msg = f"⛔ تم إيقاف المفتاح\n🔑 {key}"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

def process_check(message):
    key = message.text.strip().upper()
    result = server_request("GET", f"check/{key}")
    if result and not result.get("error") and result.get('found'):
        status = result.get('status', 'unknown')
        expiry = result.get('expiry', '')
        expiry_text = 'دائم' if expiry == 'permanent' else expiry.replace('T', ' ')[:16] if expiry else 'غير محدد'
        resume = result.get('resume', '')
        if resume and status == 'suspended':
            expiry_text = f"معلق حتى {resume.replace('T', ' ')[:16]}"
        registered = "🔒 (مقفل)" if result.get('registered') else "🆓 (مفتوح)"
        status_icon = {'active': '✅ نشط', 'suspended': '⏸️ معلق', 'inactive': '⛔ موقوف'}.get(status, status)
        msg = f"🔍 معلومات المفتاح\n━━━━━━━━━━━━━━━━\n🔑 المفتاح: {key}\n📊 الحالة: {status_icon}\n📅 الانتهاء: {expiry_text}\n🔐 الحماية: {registered}"
    elif result and result.get('found') is False:
        msg = f"❌ المفتاح {key} غير موجود"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

def process_extend(message, months):
    if str(message.chat.id) != DEVELOPER_ID:
        return
    key = message.text.strip().upper()
    result = server_request("POST", "extend", {"key": key, "months": int(months)})
    if result and not result.get("error"):
        expiry = result.get('expiry', '').replace('T', ' ')[:16] if 'T' in result.get('expiry', '') else result.get('expiry', '')
        msg = f"➕ تم تمديد المفتاح\n🔑 {key}\n⏰ إضافة: {months} أشهر\n📅 ينتهي: {expiry}"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

def process_suspend(message, hours):
    if str(message.chat.id) != DEVELOPER_ID:
        return
    key = message.text.strip().upper()
    result = server_request("POST", "suspend", {"key": key, "hours": int(hours)})
    if result and not result.get("error"):
        resume = result.get('resume', '').replace('T', ' ')[:16]
        msg = f"⏸️ تم تعليق المفتاح\n🔑 {key}\n⏰ المدة: {hours} ساعة\n📅 يستأنف: {resume}"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

def process_resume(message):
    if str(message.chat.id) != DEVELOPER_ID:
        return
    key = message.text.strip().upper()
    result = server_request("POST", "resume", {"key": key})
    if result and not result.get("error"):
        msg = f"▶️ تم استئناف المفتاح\n🔑 {key}"
    else:
        msg = "❌ السيرفر يستجيب ببطء، انتظر 30 ثانية ثم أعد المحاولة"
    bot.reply_to(message, msg)

if __name__ == "__main__":
    print("✅ بوت أشرف - جميع الأوامر مفعلة")
    print(f"👨‍💻 المطور: @AShrf_771117678")
    print(f"🌐 السيرفر: {SERVER_URL}")
    print("🔄 بدء تشغيل البوت مع نظام إعادة الاتصال التلقائي...")
    
    # نظام إعادة الاتصال التلقائي
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            logger.error(f"❌ خطأ في الاتصال: {e}")
            logger.info("🔄 إعادة الاتصال بعد 10 ثواني...")
            time.sleep(10)
            continue