import csv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from flask import Flask  # <-- خط جدید: وارد کردن Flask
from threading import Thread  # <-- خط جدید: وارد کردن Thread

# 🔑 توکن ربات شما (همین‌طور باقی می‌ماند)
TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"

# --- بخش جدید: ایجاد یک سرور وب ساده با Flask ---
app = Flask('')

@app.route('/')
def home():
    return "ربات تلگرام نمره فعال است! 🤖"

def run_web_server():
    """تابع برای اجرای وب سرور Flask در یک نخ جداگانه"""
    # مهم: پورت را باید به 10000 تغییر دهید زیرا Render در پلن رایگان فقط این پورت را می‌پذیرد
    app.run(host='0.0.0.0', port=10000)

# --- انتهای بخش جدید ---

# بقیه کدهای قبلی شما (بدون تغییر)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def search_grade(name: str, student_id: str) -> str:
    # ... (همان تابع قبلی شما، بدون تغییر) ...
    try:
        with open('grades.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['name'].strip() == name.strip() and row['student_id'].strip() == student_id.strip():
                    return row['grade']
    except Exception as e:
        logger.error(f"خطا در خواندن فایل: {e}")
    return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    # ... (همان تابع قبلی شما، بدون تغییر) ...
    text = update.message.text.strip()
    if '،' in text:
        parts = text.split('،')
    else:
        parts = text.split(',')
    if len(parts) != 2:
        await update.message.reply_text('⚠️ فرمت صحیح: «نام و نام خانوادگی،شماره دانشجویی»')
        return
    name, student_id = parts[0].strip(), parts[1].strip()
    grade = search_grade(name, student_id)
    if grade:
        await update.message.reply_text(f'✅ نمره شما: {grade}')
    else:
        await update.message.reply_text('❌ اطلاعات یافت نشد')

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('سلام! برای دریافت نمره، نام و نام خانوادگی و شماره دانشجویی خود را به شکل زیر ارسال کنید:\n\nنام و نام خانوادگی، شماره دانشجویی\n\nمثال:\nبهنام احمدی،401123450')

def main():
    # --- بخش اصلاح شده: راه‌اندازی همزمان وب سرور و ربات تلگرام ---
    print("🚀 در حال راه‌اندازی سرویس...")
    
    # 1. راه‌اندازی وب سرور Flask در یک نخ (Thread) جداگانه
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True  # این نخ با بسته شدن برنامه اصلی، بسته می‌شود.
    server_thread.start()
    print("🌐 وب سرور ساده فعال شد (پورت 10000).")
    
    # 2. راه‌اندازی ربات تلگرام (همان بخش اصلی)
    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 ربات تلگرام فعال شد!")
    telegram_app.run_polling()

if __name__ == '__main__':
    main()






