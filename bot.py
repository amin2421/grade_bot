
import csv
import logging
import os
import requests
import threading
import time
import socket
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from flask import Flask

# ==================== تنظیمات اولیه ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# 🔑 توکن ربات
TOKEN = os.getenv('BOT_TOKEN', '8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE')

# ==================== سیستم Keep-Alive ====================
def keep_awake():
    """هر ۵ دقیقه ربات را پینگ می‌کند تا نخوابد"""
    while True:
        try:
            requests.get("https://Amin_Greadebot.onrender.com", timeout=10)
            logger.info("✅ Keep-alive ping successful")
        except Exception as e:
            logger.warning(f"⚠️ Keep-alive failed: {e}")
        time.sleep(300)  # هر ۵ دقیقه

# ==================== پیدا کردن پورت آزاد ====================
def find_free_port(start_port=8080, max_attempts=10):
    """پیدا کردن یک پورت آزاد"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return start_port  # اگر پورت آزاد پیدا نشد، همان پورت پیشفرض

# ==================== سرور Flask برای Health Check ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات تلگرام نمره دانشجویان فعال است! ✅"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "telegram-grade-bot", "timestamp": time.time()}

@app.route('/ping')
def ping():
    return "pong"

def run_flask_server():
    """اجرای Flask در پس‌زمینه با پورت آزاد"""
    port = find_free_port(8080)
    logger.info(f"🌐 تلاش برای اجرای Flask روی پورت {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

# ==================== منطق اصلی ربات ====================
def search_grade(name: str, student_id: str) -> str:
    """جستجوی نمره در فایل CSV"""
    try:
        with open('grades.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (row['name'].strip().lower() == name.strip().lower() and 
                    row['student_id'].strip() == student_id.strip()):
                    return row['grade']
    except FileNotFoundError:
        logger.error("فایل grades.csv یافت نشد!")
        return None
    except Exception as e:
        logger.error(f"خطا در خواندن فایل: {e}")
    return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    """پردازش پیام‌های کاربر"""
    try:
        text = update.message.text.strip()
        
        if '،' in text:
            parts = text.split('،')
        elif ',' in text:
            parts = text.split(',')
        elif ' ' in text and len(text.split(' ')) >= 2:
            parts = text.split(' ', 1)
        else:
            await update.message.reply_text(
                '⚠️ فرمت صحیح: نام و نام خانوادگی،شماره دانشجویی\nمثال: بهنام احمدی،401123450'
            )
            return
        
        if len(parts) != 2:
            await update.message.reply_text('⚠️ لطفاً نام و شماره دانشجویی را با کاما جدا کنید.')
            return
            
        name, student_id = parts[0].strip(), parts[1].strip()
        
        logger.info(f"دریافت درخواست از: {name} - {student_id}")
        
        grade = search_grade(name, student_id)
        if grade:
            await update.message.reply_text(f'✅ نمره شما: {grade}')
            logger.info(f"نمره یافت شد: {grade}")
        else:
            await update.message.reply_text('❌ اطلاعات یافت نشد')
            logger.warning(f"نمره یافت نشد")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.')

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    user = update.effective_user
    await update.message.reply_text(
        f'سلام {user.first_name}! 👋\n'
        f'برای دریافت نمره، نام و شماره دانشجویی خود را ارسال کنید.\n\n'
        f'فرمت: نام و نام خانوادگی،شماره دانشجویی\n'
        f'مثال: بهنام احمدی،401123450'
    )

# ==================== تابع اصلی ساده شده ====================
def main():
    """تابع اصلی راه‌اندازی ربات"""
    logger.info("🚀 شروع راه‌اندازی ربات...")
    
    # شروع Keep-Alive
    keep_alive_thread = threading.Thread(target=keep_awake, daemon=True)
    keep_alive_thread.start()
    logger.info("🔄 Keep-Alive فعال شد")
    
    # شروع Flask (اگر پورت آزاد بود)
    try:
        flask_thread = threading.Thread(target=run_flask_server, daemon=True)
        flask_thread.start()
        logger.info("🌐 Flask شروع شد")
    except Exception as e:
        logger.warning(f"⚠️ Flask شروع نشد: {e}")
    
    # راه‌اندازی ربات تلگرام
    try:
        application = Application.builder().token(TOKEN).build()
        
        # اضافه کردن handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 ربات تلگرام در حال شروع...")
        
        # اجرای ساده ربات
        application.run_polling(
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=30,
            close_loop=False
        )
        
    except Exception as e:
        logger.critical(f"💥 خطا در ربات: {e}")
        raise

if __name__ == '__main__':
    # اجرای اصلی با restart اتوماتیک
    restart_count = 0
    max_restarts = 5
    
    while restart_count < max_restarts:
        try:
            logger.info(f"🔄 تلاش {restart_count + 1}/{max_restarts}")
            main()
        except KeyboardInterrupt:
            logger.info("توقف توسط کاربر")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"ربات متوقف شد: {e}")
            if restart_count < max_restarts:
                logger.info(f"⏳ صبر برای تلاش مجدد... (15 ثانیه)")
                time.sleep(15)
    
    logger.error("❌ ربات کاملاً متوقف شد")
