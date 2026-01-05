import csv
import logging
import os
import sys
from threading import Thread
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, CallbackQueryHandler
from flask import Flask

TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"
CHANNEL_ID = "@With_u_until_end"  # آیدی کانال شما

print("=" * 50)
print(f"شروع اجرا در: {time.ctime()}")
print("=" * 50)

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
    try:
        port = int(os.environ.get('PORT', 10000))
        print(f"🌐 سرور وب روی پورت {port} راه‌اندازی می‌شود...")
        web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطای سرور وب: {e}")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره وضعیت کاربران (به صورت موقت در حافظه)
user_status = {}

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

async def check_channel_membership(user_id: int, context: CallbackContext) -> bool:
    """بررسی عضویت کاربر در کانال"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت کانال: {e}")
        return False

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """بررسی عضویت کاربر با دکمه"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        user_status[user_id] = "verified"
        await query.edit_message_text(
            "✅ عضویت شما تأیید شد!\n\n"
            "حالا می‌توانید اطلاعات خود را به این فرمت ارسال کنید:\n"
            "نام و نام خانوادگی،شماره دانشجویی\n\n"
            "مثال:\n"
            "بهنام احمدی،14044121000"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/+29MDo7noLR0xMzZk")],
            [InlineKeyboardButton("✅ بررسی مجدد عضویت", callback_data="verify_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ هنوز در کانال عضو نیستید!\n\n"
            "1. روی دکمه 'عضویت در کانال' کلیک کنید\n"
            "2. پس از عضویت، روی 'بررسی مجدد عضویت' کلیک کنید",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        logger.info(f"پیام دریافتی از {user_id}: {text}")
        
        # بررسی وضعیت تأیید کاربر
        if user_id not in user_status or user_status[user_id] != "verified":
            # اگر کاربر تأیید نشده، پیام عضویت نشان داده شود
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/+29MDo7noLR0xMzZk")],
                [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👋 برای استفاده از ربات، ابتدا باید در کانال ما عضو شوید:\n\n"
                "1. روی دکمه 'عضویت در کانال' کلیک کنید\n"
                "2. پس از عضویت، روی 'بررسی عضویت من' کلیک کنید\n\n"
                "🔗 کانال: https://t.me/+29MDo7noLR0xMzZk",
                reply_markup=reply_markup
            )
            return
        
        # اگر کاربر تأیید شده، پردازش نمره
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
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/+29MDo7noLR0xMzZk")],
        [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
    سلام! 👋
    
    برای دریافت نمره ابتدا باید در کانال ما عضو شوید:
    
    1️⃣ روی دکمه 'عضویت در کانال' کلیک کنید
    2️⃣ پس از عضویت، روی 'بررسی عضویت من' کلیک کنید
    
    سپس اطلاعات خود را به این شکل ارسال کنید:
    
    نام و نام خانوادگی،شماره دانشجویی
    
    مثال:
    بهنام احمدی،14044121000
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def check_command(update: Update, context: CallbackContext) -> None:
    """دستور /check برای بررسی دستی عضویت"""
    user_id = update.effective_user.id
    
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        user_status[user_id] = "verified"
        await update.message.reply_text(
            "✅ شما عضو کانال هستید!\n\n"
            "حالا می‌توانید اطلاعات خود را ارسال کنید."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/+29MDo7noLR0xMzZk")],
            [InlineKeyboardButton("✅ بررسی مجدد عضویت", callback_data="verify_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ هنوز در کانال عضو نیستید!\n\n"
            "لطفاً ابتدا در کانال عضو شوید.",
            reply_markup=reply_markup
        )

def main():
    print("🚀 در حال راه‌اندازی سرویس...")
    
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    print("🌐 سرور وب فعال شد")
    time.sleep(1)
    
    try:
        print("🤖 در حال راه‌اندازی ربات تلگرام...")
        application = Application.builder().token(TOKEN).build()
        
        # ثبت دستورات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("check", check_command))
        
        # ثبت هندلر برای دکمه‌ها
        application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
        
        # ثبت هندلر برای پیام‌های متنی
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ ربات تلگرام آماده است!")
        print("=" * 50)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
        
    except Exception as e:
        print(f"❌ خطای اصلی: {e}")
        logger.error(f"خطای اصلی: {e}")

if __name__ == '__main__':
    main()
