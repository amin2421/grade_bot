import os
import csv
import time
import requests
import threading
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ==================== تنظیمات ساده ====================
print("🚀 در حال راه‌اندازی ربات...")

# دریافت توکن
TOKEN = os.environ.get('BOT_TOKEN', '8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE')
print(f"✅ توکن دریافت شد: {TOKEN[:15]}...")

# ==================== Keep-Alive ساده ====================
def ping_server():
    """هر ۵ دقیقه سرور را پینگ می‌کند"""
    while True:
        try:
            # آدرس درست ربات شما (با خط تیره)
            requests.get("https://amin-greadebot.onrender.com", timeout=5)
            print(f"✅ {time.ctime()} - پینگ موفق")
        except:
            print(f"⚠️ {time.ctime()} - پینگ ناموفق")
        
        time.sleep(300)  # هر ۵ دقیقه

# شروع keep-alive
thread = threading.Thread(target=ping_server, daemon=True)
thread.start()
print("🔄 سیستم Keep-Alive فعال شد")

# ==================== منطق ربات ====================
def find_grade(name: str, student_id: str) -> str:
    """جستجوی نمره در فایل CSV"""
    try:
        with open('grades.csv', 'r', encoding='utf-8') as f:
            # پیدا کردن ردیف با نام و شماره دانشجویی
            for line in f:
                if ',' in line:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        file_name, file_id, grade = parts[0], parts[1], parts[2]
                        if (file_name.strip().lower() == name.strip().lower() and 
                            file_id.strip() == student_id.strip()):
                            return grade
    except Exception as e:
        print(f"خطا در خواندن فایل: {e}")
    return None

async def handle_message(update, context):
    """پردازش پیام کاربر"""
    try:
        text = update.message.text.strip()
        print(f"📥 دریافت پیام: {text}")
        
        # جدا کردن نام و شماره دانشجویی
        if '،' in text:
            name, student_id = text.split('،', 1)
        elif ',' in text:
            name, student_id = text.split(',', 1)
        else:
            await update.message.reply_text(
                '⚠️ لطفاً اینگونه ارسال کنید:\n'
                'نام و نام خانوادگی،شماره دانشجویی\n\n'
                'مثال: بهنام احمدی،401123450'
            )
            return
        
        name = name.strip()
        student_id = student_id.strip()
        
        # جستجوی نمره
        grade = find_grade(name, student_id)
        
        if grade:
            response = f'✅ نمره شما: {grade}'
            print(f"📤 پاسخ: {name} → {grade}")
        else:
            response = '❌ اطلاعات یافت نشد'
            print(f"⚠️ یافت نشد: {name}, {student_id}")
        
        await update.message.reply_text(response)
        
    except Exception as e:
        print(f"💥 خطا: {e}")
        await update.message.reply_text('❌ خطا در پردازش')

async def start_command(update, context):
    """دستور /start"""
    await update.message.reply_text(
        '👋 سلام!\n\n'
        'برای دریافت نمره، نام و شماره دانشجویی خود را ارسال کنید:\n\n'
        '📝 فرمت:\n'
        'نام و نام خانوادگی،شماره دانشجویی\n\n'
        'مثال:\n'
        'بهنام احمدی،401123450\n'
        'فاطمه محمدی،401123451'
    )

# ==================== اجرای اصلی ====================
def run_bot():
    """تابع اصلی اجرای ربات"""
    try:
        # ایجاد برنامه
        app = Application.builder().token(TOKEN).build()
        
        # اضافه کردن دستورات
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🤖 ربات فعال و آماده است...")
        print("📍 آدرس: https://amin-greadebot.onrender.com")
        print("⏰ Keep-Alive: هر ۵ دقیقه")
        
        # اجرای ربات
        app.run_polling(
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=30
        )
        
    except Exception as e:
        print(f"💥 خطای شدید: {e}")
        return False
    
    return True

if __name__ == '__main__':
    # اجرا با restart اتوماتیک
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        attempts += 1
        print(f"\n🔄 تلاش شماره {attempts}")
        
        if run_bot():
            print("ربات به صورت طبیعی متوقف شد")
            break
        else:
            if attempts < max_attempts:
                print(f"⏳ ۱۰ ثانیه صبر برای تلاش مجدد...")
                time.sleep(10)
            else:
                print("❌ بیش از حد تلاش ناموفق")
