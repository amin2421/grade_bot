import csv
import logging
import os
from threading import Thread

# کتابخانه‌های اصلی تلگرام
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# کتابخانه برای سرور وب (ضروری برای Render)
from flask import Flask

# 🔑 **توکن ربات شما - اینجا قرار دهید**
TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"

# ==================== بخش ۱: سرور وب برای Render ====================
# این بخش باعث می‌شود Render بفهمد سرویس شما زنده است
web_app = Flask(__name__)

@web_app.route('/')
def home():
    """صفحه اصلی برای چک سلامت سرویس"""
    return "✅ ربات تلگرام نمره‌یاب فعال و آنلاین است! 🤖"

@web_app.route('/health')
def health_check():
    """برای بررسی وضعیت سرویس"""
    return "OK", 200

def run_web_server():
    """اجرای سرور وب در پس‌زمینه"""
    # خواندن پورت از متغیر محیطی Render (یا 10000 به صورت پیش‌فرض)
    port = int(os.environ.get('PORT', 10000))
    # اجرا در حالت غیر دیباگ برای محیط عملیاتی
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
# ==================== پایان بخش سرور وب ====================

# ==================== بخش ۲: منطق اصلی ربات ====================
# تنظیمات گزارش‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def search_grade(name: str, student_id: str) -> str:
    """جستجوی نمره در فایل CSV"""
    try:
        with open('grades.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (row['name'].strip() == name.strip() and 
                    row['student_id'].strip() == student_id.strip()):
                    return row['grade']
    except FileNotFoundError:
        logger.error("❌ فایل grades.csv یافت نشد!")
        return None
    except Exception as e:
        logger.error(f"❌ خطا در خواندن فایل: {e}")
        return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    """پردازش پیام ارسالی کاربر"""
    text = update.message.text.strip()
    
    # جدا کردن نام و شماره دانشجویی (هم فارسی هم انگلیسی)
    if '،' in text:  # کامای فارسی
        parts = text.split('،')
    else:  # کامای انگلیسی
        parts = text.split(',')
    
    if len(parts) != 2:
        await update.message.reply_text('⚠️ لطفاً اطلاعات را به شکل «نام خانوادگی، شماره دانشجویی» ارسال کنید.')
        return
    
    name, student_id = parts[0].strip(), parts[1].strip()
    grade = search_grade(name, student_id)
    
    if grade:
        await update.message.reply_text(f'✅ نمره شما: {grade}')
    else:
        await update.message.reply_text('❌ اطلاعات یافت نشد. لطفاً نام و شماره دانشجویی را بررسی کنید.')

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    welcome_text = """
    سلام! 👋
    
    برای دریافت نمره، لطفاً اطلاعات خود را به صورت زیر ارسال کنید:
    
    **«نام خانوادگی، شماره دانشجویی»**
    
    مثال:
    `احمدی، 401123456`
    """
    await update.message.reply_text(welcome_text)

def main():
    """تابع اصلی اجرای ربات"""
    print("🚀 در حال راه‌اندازی سرویس...")
    
    # ==================== بخش ۳: راه‌اندازی همزمان ====================
    # ۱. شروع سرور وب در یک نخ جداگانه (برای Render)
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    print(f"🌐 سرور وب فعال شد (برای Render)")
    
    # ۲. ساخت و راه‌اندازی ربات تلگرام
    application = Application.builder().token(TOKEN).build()
    
    # ثبت دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 ربات تلگرام فعال شد!")
    print("✅ سرویس کاملاً آنلاین است!")
    
    # شروع ربات تلگرام (این تابع مسدود کننده است)
    application.run_polling(
        drop_pending_updates=True,
        close_loop_on_sigint=False
    )
# ==================== پایان تابع اصلی ====================

if __name__ == '__main__':
    main()
