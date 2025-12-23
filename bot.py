import csv
import logging
import os
import requests
import threading
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from flask import Flask

# ==================== تنظیمات اولیه ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 بهتر است توکن از Environment Variable بخواند
TOKEN = os.getenv('BOT_TOKEN', '8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE')

# ==================== سیستم Keep-Alive ====================
def keep_awake():
    """هر ۴ دقیقه ربات را پینگ می‌کند تا نخوابد"""
    while True:
        try:
            requests.get("https://Amin_Greadebot.onrender.com", timeout=10)
            logger.info("✅ Keep-alive ping successful")
        except Exception as e:
            logger.warning(f"⚠️ Keep-alive failed: {e}")
        time.sleep(240)  # هر ۴ دقیقه

# ==================== سرور Flask برای Health Check ====================
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ربات نمره دانشجویان</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            h1 { color: #2c3e50; }
            .status { color: #27ae60; font-size: 20px; margin: 20px 0; }
            .info { background: #f8f9fa; padding: 20px; border-radius: 10px; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>🤖 ربات تلگرام نمره دانشجویان</h1>
        <div class="status">✅ سرویس فعال و در حال اجرا</div>
        <div class="info">
            <p><strong>آدرس ربات:</strong> https://Amin_Greadebot.onrender.com</p>
            <p><strong>آخرین بروزرسانی:</strong> """ + time.ctime() + """</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "service": "telegram-grade-bot", "timestamp": time.time()}

@app.route('/ping')
def ping():
    return "pong"

def run_flask_server():
    """اجرای Flask در پس‌زمینه"""
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

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
        return "خطا: فایل نمرات موجود نیست"
    except Exception as e:
        logger.error(f"خطا در خواندن فایل: {e}")
    return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    """پردازش پیام‌های کاربر"""
    try:
        text = update.message.text.strip()
        
        # پشتیبانی از جداکننده‌های مختلف
        if '،' in text:
            parts = text.split('،')
        elif ',' in text:
            parts = text.split(',')
        elif ' ' in text and len(text.split(' ')) >= 2:
            parts = text.split(' ', 1)
        else:
            await update.message.reply_text(
                '⚠️ فرمت صحیح:\n'
                '• نام و نام خانوادگی،شماره دانشجویی\n'
                '• نام و نام خانوادگی شماره دانشجویی\n'
                '\nمثال:\nبهنام احمدی،401123450\n'
                'یا\nبهنام احمدی 401123450'
            )
            return
        
        if len(parts) != 2:
            await update.message.reply_text('⚠️ لطفاً نام و شماره دانشجویی را با کاما یا فاصله جدا کنید.')
            return
            
        name, student_id = parts[0].strip(), parts[1].strip()
        
        # لاگ دریافت درخواست
        logger.info(f"دریافت درخواست از: {name} - {student_id}")
        
        grade = search_grade(name, student_id)
        if grade:
            await update.message.reply_text(f'✅ نمره شما: {grade}')
            logger.info(f"نمره یافت شد برای {name}: {grade}")
        else:
            await update.message.reply_text(
                '❌ اطلاعات یافت نشد\n'
                'لطفاً بررسی کنید:\n'
                '1. نام و نام خانوادگی را کامل وارد کرده باشید\n'
                '2. شماره دانشجویی را درست وارد کرده باشید\n'
                '3. از حروف فارسی استفاده کنید'
            )
            logger.warning(f"نمره یافت نشد برای: {name} - {student_id}")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.')

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    user = update.effective_user
    welcome_text = (
        f'سلام {user.first_name}! 👋\n'
        f'به ربات دریافت نمره خوش آمدید.\n\n'
        f'📝 برای دریافت نمره، نام و نام خانوادگی و شماره دانشجویی خود را ارسال کنید:\n\n'
        f'• فرمت اول: نام و نام خانوادگی،شماره دانشجویی\n'
        f'• فرمت دوم: نام و نام خانوادگی شماره دانشجویی\n\n'
        f'مثال‌ها:\n'
        f'`بهنام احمدی،401123450`\n'
        f'یا\n'
        f'`بهنام احمدی 401123450`\n\n'
        f'📍 آدرس وب سرویس: https://Amin_Greadebot.onrender.com\n'
        f'🔄 وضعیت سرویس: فعال ✅'
    )
    await update.message.reply_text(welcome_text)

async def status(update: Update, context: CallbackContext) -> None:
    """دستور /status برای چک وضعیت"""
    status_text = (
        '📊 وضعیت سرویس:\n'
        '• ربات: فعال ✅\n'
        '• سرور: Render\n'
        '• آدرس: https://Amin_Greadebot.onrender.com\n'
        '• آخرین بروزرسانی: ' + time.ctime() + '\n'
        '• Keep-alive: فعال (هر ۴ دقیقه)\n'
        '• Health Check: /health ✅'
    )
    await update.message.reply_text(status_text)

async def error_handler(update: Update, context: CallbackContext):
    """مدیریت خطاهای全局"""
    logger.error(f"خطا در پردازش آپدیت: {context.error}", exc_info=context.error)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                '⚠️ خطایی در پردازش درخواست شما رخ داد.\n'
                'لطفاً دوباره تلاش کنید.'
            )
        except:
            pass

# ==================== تابع اصلی ====================
def main():
    """تابع اصلی راه‌اندازی ربات"""
    logger.info("🚀 در حال راه‌اندازی سرویس...")
    
    # 1. شروع سیستم Keep-Alive
    keep_alive_thread = threading.Thread(target=keep_awake, daemon=True)
    keep_alive_thread.start()
    logger.info("🔄 سیستم Keep-Alive فعال شد (هر ۴ دقیقه)")
    
    # 2. شروع سرور Flask
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("🌐 سرور Flask فعال شد (پورت 8080)")
    
    # 3. راه‌اندازی ربات تلگرام
    try:
        telegram_app = Application.builder().token(TOKEN).build()
        
        # اضافه کردن handlers
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("status", status))
        telegram_app.add_handler(CommandHandler("ping", status))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # اضافه کردن error handler
        telegram_app.add_error_handler(error_handler)
        
        logger.info("🤖 ربات تلگرام در حال راه‌اندازی...")
        
        # تنظیمات polling برای پایداری بیشتر
        telegram_app.run_polling(
            drop_pending_updates=True,
            poll_interval=1.0,  # افزایش interval برای کاهش بار
            timeout=30,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=30,
            pool_timeout=30,
            bootstrap_retries=-1,  # تلاش بی‌نهایت برای reconnect
            allowed_updates=None
        )
        
    except Exception as e:
        logger.critical(f"💥 ربات متوقف شد: {e}")
        # تلاش مجدد پس از ۱۰ ثانیه
        logger.info("🔄 تلاش مجدد در ۱۰ ثانیه...")
        time.sleep(10)
        return False
    
    return True

if __name__ == '__main__':
    # راه‌اندازی با قابلیت restart اتوماتیک
    restart_count = 0
    max_restarts = 20
    
    while restart_count < max_restarts:
        logger.info(f"🔄 تلاش شماره {restart_count + 1} برای راه‌اندازی ربات...")
        
        if main():
            logger.info("ربات به طور طبیعی متوقف شد.")
            break
        else:
            restart_count += 1
            logger.warning(f"ربات crashed. تلاش مجدد... ({restart_count}/{max_restarts})")
    
    if restart_count >= max_restarts:
        logger.critical("❌ بیش از حد تلاش مجدد. ربات کاملاً متوقف شد.")
