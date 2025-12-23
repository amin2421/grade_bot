import csv
import logging
import os
import sys
from threading import Thread
import time
from waitress import serve  # تغییر: استفاده از Waitress برای production

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from flask import Flask

TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"

# ========== خطایابی ==========
print("=" * 50)
print(f"شروع اجرا در: {time.ctime()}")
print("=" * 50)

# ========== سرور وب Flask ==========
try:
    web_app = Flask(__name__)
    print("✅ Flask وارد شد")
except Exception as e:
    print(f"❌ خطای Flask: {e}")
    sys.exit(1)

@web_app.route('/')
def home():
    return "✅ ربات تلگرام نمره‌یاب فعال است"

@web_app.route('/health')
def health_check():
    return "OK", 200

def run_web_server():
    """اجرای سرور وب با Waitress (مناسب برای production)"""
    try:
        port = int(os.environ.get('PORT', 10000))
        print(f"🌐 سرور وب (Waitress) روی پورت {port} راه‌اندازی می‌شود...")
        
        # استفاده از Waitress به جای flask.run
        serve(web_app, host='0.0.0.0', port=port, threads=1)
        
    except Exception as e:
        print(f"❌ خطای سرور وب: {e}")

# ========== بقیه کد شما (بدون تغییر) ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def search_grade(name: str, student_id: str) -> str:
    try:
        if not os.path.exists('grades.csv'):
            print("❌ فایل grades.csv یافت نشد!")
            logger.error("فایل grades.csv یافت نشد!")
            return None
            
        with open('grades.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (row['name'].strip() == name.strip() and 
                    row['student_id'].strip() == student_id.strip()):
                    return row['grade']
        return None
    except Exception as e:
        logger.error(f"خطا در جستجوی نمره: {e}")
        return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text.strip()
        logger.info(f"پیام دریافتی: {text}")
        
        if '،' in text:
            parts = text.split('،')
        else:
            parts = text.split(',')
        
        if len(parts) != 2:
            await update.message.reply_text('⚠️ فرمت صحیح: «نام و نام خانوادگی، شماره دانشجویی»')
            return
        
        name, student_id = parts[0].strip(), parts[1].strip()
        grade = search_grade(name, student_id)
        
        if grade:
            await update.message.reply_text(f'✅ نمره شما: {grade}')
            logger.info(f"نمره یافت شد: {name} -> {grade}")
        else:
            await update.message.reply_text('❌ اطلاعات یافت نشد. لطفاً بررسی کنید.')
            logger.info(f"نمره یافت نشد: {name}, {student_id}")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    welcome_text = """
    سلام! 👋
    
    برای دریافت نمره، اطلاعات خود را به این شکل ارسال کنید:
    
    نام و نام خانوادگی، شماره دانشجویی
    
    مثال:
    بهنام احمدی،401123456 
    """
    await update.message.reply_text(welcome_text)

def main():
    print("🚀 در حال راه‌اندازی سرویس...")
    
    # راه‌اندازی سرور وب در نخ جداگانه
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    print("🌐 سرور وب (Waitress) فعال شد")
    time.sleep(2)
    
    # راه‌اندازی ربات تلگرام
    try:
        print("🤖 در حال راه‌اندازی ربات تلگرام...")
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ ربات تلگرام آماده است!")
        print("=" * 50)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        print(f"❌ خطای اصلی: {e}")
        logger.error(f"خطای اصلی: {e}")

if __name__ == '__main__':
    main()
