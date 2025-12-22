import csv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext
from telegram.ext import filters  # تغییر اصلی اینجاست

# 🔑 توکن ربات شما
TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def search_grade(name: str, student_id: str) -> str:
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
    text = update.message.text.strip()
    
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
    else:
        await update.message.reply_text('❌ اطلاعات یافت نشد')

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('سلام! برای دریافت نمره، نام ونام خانوادگی و شماره دانشجویی خود را به شکل زیر ارسال کنید:\n\n«نام و تام خانوادگی، شماره دانشجویی»\n\nمثال:\nبهنام احمدی، 401123456')

def main():
    # استفاده از Application به جای Updater[citation:8]
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # تغییر مهم: استفاده از filters.TEXT به جای Filters.text[citation:4]
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 ربات فعال شد! برای توقف Ctrl+C را بزنید.")
    app.run_polling()

if __name__ == '__main__':
    main()