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
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_errors.log')
    ]
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
            body { font-family: Tahoma, sans-serif; text-align: center; padding: 50px; direction: rtl; }
            h1 { color: #2c3e50; }
            .status { color: #27ae60; font-size: 20px; margin: 20px 0; }
            .info { background: #f8f9fa; padding: 20px; border-radius: 10px; display: inline-block; margin: 20px auto; }
            .footer { margin-top: 30px; color: #7f8c8d; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>🤖 ربات تلگرام نمره دانشجویان</h1>
        <div class="status">✅ سرویس فعال و در حال اجرا</div>
        <div class="info">
            <p><strong>آدرس ربات:</strong> https://Amin_Greadebot.onrender.com</p>
            <p><strong>وضعیت:</strong> آنلاین</p>
            <p><strong>آخرین بروزرسانی:</strong> """ + time.ctime() + """</p>
            <p><strong>Health Check:</strong> <a href="/health">/health</a></p>
        </div>
        <div class="footer">
            ربات طراحی شده برای دریافت نمرات دانشجویان
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
        return None
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
                '• نام و نام خانوادگی شماره دانشجویی\n\n'
                'مثال:\n'
                '`بهنام احمدی،401123450`\n'
                'یا\n'
                '`بهنام احمدی 401123450`'
            )
            return
        
        if len(parts) != 2:
            await update.message.reply_text('⚠️ لطفاً نام و شماره دانشجویی را با کاما یا فاصله جدا کنید.')
            return
            
        name, student_id = parts[0].strip(), parts[1].strip()
        
        # لاگ دریافت درخواست
        logger.info(f"📥 دریافت درخواست از: {name} - {student_id}")
        
        grade = search_grade(name, student_id)
        if grade:
            response = f'✅ نمره شما: {grade}'
            await update.message.reply_text(response)
            logger.info(f"📤 پاسخ داده شد: {name} → {grade}")
        else:
            response = (
                '❌ اطلاعات یافت نشد\n\n'
                'لطفاً بررسی کنید:\n'
                '• نام و نام خانوادگی را کامل وارد کرده باشید\n'
                '• شماره دانشجویی را درست وارد کرده باشید\n'
                '• از حروف فارسی استفاده کنید'
            )
            await update.message.reply_text(response)
            logger.warning(f"⚠️ نمره یافت نشد برای: {name} - {student_id}")
            
    except Exception as e:
        logger.error(f"💥 خطا در پردازش پیام: {e}", exc_info=True)
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.')

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    user = update.effective_user
    welcome_text = (
        f'سلام {user.first_name}! 👋\n\n'
        f'به ربات دریافت نمره خوش آمدید.\n\n'
        f'📝 **دستورالعمل استفاده:**\n'
        f'نام و نام خانوادگی و شماره دانشجویی خود را به یکی از فرمت‌های زیر ارسال کنید:\n\n'
        f'• `نام و نام خانوادگی،شماره دانشجویی`\n'
        f'• `نام و نام خانوادگی شماره دانشجویی`\n\n'
        f'**مثال‌ها:**\n'
        f'`بهنام احمدی،401123450`\n'
        f'`بهنام احمدی 401123450`\n\n'
        f'📍 **آدرس وب سرویس:**\n'
        f'https://Amin_Greadebot.onrender.com\n\n'
        f'🔧 **دستورات قابل استفاده:**\n'
        f'/start - راهنمایی\n'
        f'/status - وضعیت ربات\n'
        f'/ping - تست پاسخ‌دهی'
    )
    await update.message.reply_text(welcome_text)

async def status(update: Update, context: CallbackContext) -> None:
    """دستور /status برای چک وضعیت"""
    status_text = (
        '📊 **وضعیت سرویس:**\n\n'
        '• 🤖 ربات: فعال ✅\n'
        '• 🖥️ سرور: Render\n'
        '• 🌐 آدرس: https://Amin_Greadebot.onrender.com\n'
        '• 🕐 آخرین بروزرسانی: ' + time.ctime() + '\n'
        '• 🔄 Keep-alive: فعال (هر ۴ دقیقه)\n'
        '• 🩺 Health Check: /health ✅\n\n'
        '📈 **آمار:**\n'
        '• Uptime: ' + str(round(time.time() - start_time)) + ' ثانیه'
    )
    await update.message.reply_text(status_text)

async def error_handler(update: Update, context: CallbackContext):
    """مدیریت خطاهای全局"""
    logger.error(f"🔥 خطا در پردازش آپدیت: {context.error}", exc_info=True)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                '⚠️ خطایی در پردازش درخواست شما رخ داد.\n'
                'لطفاً دوباره تلاش کنید.'
            )
        except:
            pass

# ==================== تابع اصلی ====================
def run_bot():
    """تابع اصلی راه‌اندازی ربات"""
    global start_time
    start_time = time.time()
    
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
        # ساخت Application
        application = Application.builder().token(TOKEN).build()
        
        # اضافه کردن handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("ping", status))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # اضافه کردن error handler
        application.add_error_handler(error_handler)
        
        logger.info("🤖 ربات تلگرام در حال راه‌اندازی...")
        
        # اجرای ربات با run_polling (روش صحیح در v20)
        application.run_polling(
            drop_pending_updates=True,      # حذف آپدیت‌های قدیمی
            allowed_updates=Update.ALL_TYPES,
            poll_interval=1.0,              # فاصله بین polling
            poll_timeout=30.0,              # timeout برای polling
            close_loop=False,               # جلوگیری از بسته شدن loop
            stop_signals=None               # غیرفعال کردن سیگنال‌های توقف
        )
        
    except Exception as e:
        logger.critical(f"💥 ربات متوقف شد: {e}", exc_info=True)
        raise e

def main():
    """تابع اصلی با restart اتوماتیک"""
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        try:
            logger.info(f"🔄 تلاش شماره {restart_count + 1} برای راه‌اندازی ربات...")
            run_bot()
            
        except KeyboardInterrupt:
            logger.info("👋 ربات توسط کاربر متوقف شد.")
            break
            
        except Exception as e:
            restart_count += 1
            logger.error(f"💥 ربات crashed. تلاش مجدد {restart_count}/{max_restarts}")
            logger.error(f"خطا: {e}")
            
            if restart_count < max_restarts:
                logger.info(f"⏳ صبر برای تلاش مجدد... (۱۰ ثانیه)")
                time.sleep(10)
            else:
                logger.critical("❌ بیش از حد تلاش مجدد. ربات کاملاً متوقف شد.")
                break

if __name__ == '__main__':
    main()
