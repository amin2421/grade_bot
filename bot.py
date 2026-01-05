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
CHANNEL_ID = -1003457817555  # آیدی عددی واقعی کانال شما
CHANNEL_USERNAME = "@With_u_until_end"
CHANNEL_LINK = "https://t.me/+uRCMurkr0KA5ODNk"

print("=" * 50)
print(f"شروع اجرا در: {time.ctime()}")
print("=" * 50)
print(f"📢 کانال: {CHANNEL_USERNAME} (آیدی: {CHANNEL_ID})")

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
    """بررسی عضویت کاربر در کانال با آیدی عددی"""
    try:
        logger.info(f"🔍 بررسی عضویت کاربر {user_id} در کانال {CHANNEL_ID}")
        
        # با آیدی عددی بررسی می‌کنیم
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        
        # وضعیت‌های مجاز
        allowed_statuses = ['member', 'administrator', 'creator']
        is_member = member.status in allowed_statuses
        
        logger.info(f"📊 کاربر {user_id} - وضعیت: {member.status} - عضو است: {is_member}")
        
        # برای دیباگ بیشتر
        if not is_member:
            logger.info(f"⚠️ وضعیت غیرمجاز: {member.status}")
        
        return is_member
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ خطا در بررسی عضویت کاربر {user_id}: {error_msg}")
        
        # تشخیص دقیق خطا
        if "Chat not found" in error_msg:
            logger.error(f"⚠️ کانال با آیدی {CHANNEL_ID} پیدا نشد!")
        elif "User not found" in error_msg:
            logger.error(f"⚠️ کاربر {user_id} در کانال پیدا نشد")
        elif "Not enough rights" in error_msg:
            logger.error("⚠️ ربات دسترسی کافی ندارد!")
        elif "Forbidden" in error_msg:
            logger.error("⚠️ ربات اخراج شده یا ادمین نیست")
        elif "user is deactivated" in error_msg:
            logger.error("⚠️ کاربر غیرفعال است")
            
        return False

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """بررسی عضویت کاربر با دکمه"""
    query = update.callback_query
    await query.answer("در حال بررسی...")
    
    user_id = query.from_user.id
    username = query.from_user.username or f"کاربر{user_id}"
    
    logger.info(f"🔄 بررسی عضویت برای {username} ({user_id})")
    
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        user_status[user_id] = {
            "verified": True,
            "timestamp": time.time(),
            "username": username,
            "checked_at": time.ctime()
        }
        
        logger.info(f"🎉 تأیید عضویت برای {username}")
        
        await query.edit_message_text(
            f"✅ عضویت شما تأیید شد!\n\n"
            f"👋 سلام {username}!\n\n"
            f"📝 حالا اطلاعات خود را به این فرمت ارسال کنید:\n\n"
            f"نام و نام خانوادگی،شماره دانشجویی\n\n"
            f"مثال:\n"
            f"بهنام احمدی،14044121000\n\n"
            f"✨ می‌توانید چندین بار نمره خود را چک کنید!"
        )
    else:
        # حذف وضعیت قبلی
        if user_id in user_status:
            del user_status[user_id]
        
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.warning(f"⚠️ عضویت {username} تأیید نشد")
        
        await query.edit_message_text(
            f"❌ عضویت شما تأیید نشد!\n\n"
            f"لطفاً بررسی کنید:\n\n"
            f"1. آیا در کانال عضو شده‌اید؟\n"
            f"2. آیا از همان اکانتی استفاده می‌کنید که در کانال عضو شده‌اید؟\n"
            f"3. پس از عضویت، کمی صبر کنید (۱۰ ثانیه)\n\n"
            f"📢 کانال: {CHANNEL_USERNAME}\n"
            f"🔗 لینک: {CHANNEL_LINK}\n\n"
            f"پس از اطمینان از عضویت، دوباره بررسی کنید.",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        username = update.effective_user.username or f"user_{user_id}"
        
        logger.info(f"📩 پیام از {username}: {text}")
        
        # بررسی وضعیت تأیید کاربر
        if user_id not in user_status or not user_status[user_id].get("verified", False):
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"👋 سلام {username}!\n\n"
                f"برای دریافت نمره ابتدا باید در کانل ما عضو شوید:\n\n"
                f"📢 کانال: {CHANNEL_USERNAME}\n"
                f"🔗 لینک: {CHANNEL_LINK}\n\n"
                f"مراحل:\n"
                f"1️⃣ روی 'عضویت در کانال' کلیک کنید\n"
                f"2️⃣ پس از عضویت، روی 'بررسی عضویت من' کلیک کنید\n\n"
                f"⚡ سریع و آسان!",
                reply_markup=reply_markup
            )
            return
        
        # اگر کاربر تأیید شده، پردازش نمره
        if '،' in text:
            parts = text.split('،')
        else:
            parts = text.split(',')
        
        if len(parts) != 2:
            await update.message.reply_text(
                '⚠️ فرمت صحیح:\n\n'
                '«نام و نام خانوادگی، شماره دانشجویی»\n\n'
                'مثال:\n'
                'بهنام احمدی،14044121000'
            )
            return
        
        name, student_id = parts[0].strip(), parts[1].strip()
        grade = search_grade(name, student_id)
        
        if grade:
            await update.message.reply_text(
                f'✅ نمره شما: {grade}\n\n'
                f'👤 نام: {name}\n'
                f'🆔 شماره دانشجویی: {student_id}\n\n'
                f'🎉 موفق باشید!'
            )
            logger.info(f"نمره یافت شد: {name} -> {grade}")
        else:
            await update.message.reply_text(
                '❌ اطلاعات یافت نشد!\n\n'
                'لطفاً بررسی کنید:\n'
                '1. نام و نام خانوادگی را صحیح وارد کنید\n'
                '2. شماره دانشجویی را دقیق وارد کنید\n'
                '3. از کاما (,) یا ویرگول (،) استفاده کنید'
            )
            logger.info(f"نمره یافت نشد: {name}, {student_id}")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")
        await update.message.reply_text("⚠️ خطای داخلی رخ داد. لطفاً دوباره تلاش کنید.")

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    username = user.username or user.first_name or "کاربر"
    
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    👋 سلام {username}!
    
    به ربات نمره‌یاب خوش آمدید! 🎓
    
    📢 کانال ما: {CHANNEL_USERNAME}
    
    📌 برای دریافت نمره:
    
    1️⃣ عضویت در کانال:
       روی دکمه 'عضویت در کانال' کلیک کنید
    
    2️⃣ تأیید عضویت:
       پس از عضویت، روی 'بررسی عضویت من' کلیک کنید
    
    3️⃣ دریافت نمره:
       اطلاعات خود را به این فرمت ارسال کنید:
    
       نام و نام خانوادگی،شماره دانشجویی
    
    📝 مثال:
    بهنام احمدی،14044121000
    
    ⚡ سریع و آسان!
    """
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=reply_markup
    )

async def stats(update: Update, context: CallbackContext) -> None:
    """آمار ربات"""
    user_id = update.effective_user.id
    
    stats_text = f"""
    📊 آمار ربات:
    
    👥 کاربران تأیید شده: {len(user_status)}
    🆔 آیدی کانال: {CHANNEL_ID}
    📢 کانال: {CHANNEL_USERNAME}
    
    📅 آخرین کاربران تأیید شده:
    """
    
    # نمایش ۵ کاربر آخر
    count = 0
    for uid, data in list(user_status.items())[-5:]:
        if data.get("verified"):
            count += 1
            username = data.get("username", "بدون نام")
            time_str = data.get("checked_at", "نامشخص")
            stats_text += f"\n{count}. {username} ({uid}) - {time_str}"
    
    if count == 0:
        stats_text += "\nهنوز کاربری تأیید نشده است."
    
    await update.message.reply_text(stats_text)

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
        application.add_handler(CommandHandler("stats", stats))
        
        # ثبت هندلر برای دکمه‌ها
        application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
        
        # ثبت هندلر برای پیام‌های متنی
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ ربات تلگرام آماده است!")
        print(f"📢 کانال: {CHANNEL_USERNAME}")
        print(f"🆔 آیدی عددی: {CHANNEL_ID}")
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
