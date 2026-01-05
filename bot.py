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
CHANNEL_LINK = "https://t.me/grade_amin"  # لینک عمومی کانال

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

# ذخیره وضعیت کاربران
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
        logger.info(f"🔍 بررسی عضویت کاربر {user_id} در کانال {CHANNEL_ID}")
        
        # ابتدا بررسی می‌کنیم آیا بات در کانال است
        try:
            bot_member = await context.bot.get_chat_member(
                chat_id=CHANNEL_ID, 
                user_id=context.bot.id
            )
            logger.info(f"🤖 وضعیت ربات در کانال: {bot_member.status}")
            
            # اگر ربات ادمین نیست، نمی‌تواند وضعیت کاربران را بررسی کند
            if bot_member.status != 'administrator':
                logger.error("❌ ربات ادمین کانال نیست!")
                return False
                
        except Exception as bot_err:
            logger.error(f"❌ ربات در کانال نیست یا ادمین نیست: {bot_err}")
            return False
        
        # حالا وضعیت کاربر را بررسی می‌کنیم
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        logger.info(f"👤 وضعیت کاربر {user_id}: {member.status}")
        
        # وضعیت‌های مجاز
        allowed_statuses = ['member', 'administrator', 'creator']
        is_member = member.status in allowed_statuses
        
        logger.info(f"✅ نتیجه بررسی: کاربر عضو است = {is_member}")
        return is_member
        
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ خطا در بررسی عضویت: {error_msg}")
        
        if "chat not found" in error_msg:
            logger.error("⚠️ کانال پیدا نشد - آیدی را بررسی کنید")
        elif "user not found" in error_msg:
            logger.error("⚠️ کاربر در کانال پیدا نشد")
        elif "not enough rights" in error_msg:
            logger.error("⚠️ ربات دسترسی کافی ندارد")
        elif "forbidden" in error_msg:
            logger.error("⚠️ ربات اخراج شده یا ادمین نیست")
            
        return False

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """بررسی عضویت کاربر با دکمه"""
    query = update.callback_query
    await query.answer("در حال بررسی...")
    
    user_id = query.from_user.id
    logger.info(f"🔄 درخواست بررسی عضویت از کاربر {user_id}")
    
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        user_status[user_id] = {
            "verified": True,
            "timestamp": time.time(),
            "username": query.from_user.username or f"user_{user_id}"
        }
        
        logger.info(f"🎉 عضویت کاربر {user_id} تأیید شد")
        
        await query.edit_message_text(
            "✅ عضویت شما تأیید شد!\n\n"
            "📝 حالا اطلاعات خود را به این فرمت ارسال کنید:\n\n"
            "**نام و نام خانوادگی،شماره دانشجویی**\n\n"
            "مثال:\n"
            "`بهنام احمدی،14044121000`",
            parse_mode='Markdown'
        )
    else:
        # حذف وضعیت قبلی
        if user_id in user_status:
            del user_status[user_id]
        
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")],
            [InlineKeyboardButton("⚙️ تنظیمات دسترسی ربات", callback_data="access_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.warning(f"⚠️ عضویت کاربر {user_id} تأیید نشد")
        
        await query.edit_message_text(
            "❌ عضویت شما تأیید نشد!\n\n"
            "🔍 **دلایل احتمالی:**\n"
            "1. هنوز عضو کانال نشده‌اید\n"
            "2. ربات ادمین کانال نیست\n"
            "3. ربات دسترسی کافی ندارد\n\n"
            "🛠️ **لطفاً:**\n"
            "1. مطمئن شوید عضو کانال شده‌اید\n"
            "2. ربات را با تنظیمات درست ادمین کنید\n"
            "3. روی 'تنظیمات دسترسی ربات' کلیک کنید",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def access_settings(update: Update, context: CallbackContext) -> None:
    """تنظیمات دسترسی صحیح برای ربات"""
    query = update.callback_query
    await query.answer()
    
    settings_text = """
    ⚙️ **تنظیمات صحیح دسترسی ربات:**
    
    **ربات را ادمین کنید با این تنظیمات:**
    
    ✅ **Post messages** (ارسال پیام)
    ✅ **Edit messages** (ویرایش پیام)
    ✅ **Delete messages** (حذف پیام)
    ✅ **Invite users via link** (دعوت کاربر با لینک)
    ✅ **Restrict users** (محدود کردن کاربران)
    ✅ **Pin messages** (سنجاق کردن پیام)
    
    ❌ **توجه: این دسترسی‌ها را ندهید:**
    ❌ Change channel info (تغییر اطلاعات کانال)
    ❌ Manage video chats (مدیریت چت ویدیویی)
    ❌ Add new admins (اضافه کردن ادمین جدید)
    ❌ Anonymous (ناشناس)
    
    **مراحل:**
    1. به تنظیمات کانال بروید
    2. Administrators → Add Admin
    3. ربات را انتخاب کنید
    4. فقط دسترسی‌های ✅ بالا را فعال کنید
    5. تغییرات را ذخیره کنید
    
    پس از تنظیم، دوباره بررسی کنید.
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")],
        [InlineKeyboardButton("📢 بازگشت به عضویت", url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        logger.info(f"📩 پیام از کاربر {user_id}: {text}")
        
        # بررسی وضعیت تأیید کاربر
        if user_id not in user_status or not user_status[user_id].get("verified", False):
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")],
                [InlineKeyboardButton("⚙️ تنظیمات دسترسی", callback_data="access_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👋 برای دریافت نمره ابتدا در کانال عضو شوید:\n\n"
                "**مراحل:**\n"
                "1. روی 'عضویت در کانال' کلیک کنید\n"
                "2. پس از عضویت، روی 'بررسی عضویت من' کلیک کنید\n"
                "3. اگر مشکل دارید، تنظیمات دسترسی را چک کنید\n\n"
                f"🔗 کانال: {CHANNEL_LINK}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # اگر کاربر تأیید شده، پردازش نمره
        if '،' in text:
            parts = text.split('،')
        else:
            parts = text.split(',')
        
        if len(parts) != 2:
            await update.message.reply_text(
                '⚠️ فرمت صحیح: **«نام و نام خانوادگی، شماره دانشجویی»**\n\n'
                'مثال:\n'
                '`بهنام احمدی،14044121000`',
                parse_mode='Markdown'
            )
            return
        
        name, student_id = parts[0].strip(), parts[1].strip()
        grade = search_grade(name, student_id)
        
        if grade:
            await update.message.reply_text(f'✅ **نمره شما:** {grade}', parse_mode='Markdown')
            logger.info(f"نمره یافت شد: {name} -> {grade}")
        else:
            await update.message.reply_text('❌ اطلاعات یافت نشد. لطفاً بررسی کنید.')
            logger.info(f"نمره یافت نشد: {name}, {student_id}")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")],
        [InlineKeyboardButton("⚙️ تنظیمات دسترسی", callback_data="access_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    سلام! 👋
    
    برای دریافت نمره ابتدا در کانال ما عضو شوید:
    
    🔗 **کانال:** {CHANNEL_LINK}
    
    📌 **مراحل:**
    1️⃣ روی 'عضویت در کانال' کلیک کنید
    2️⃣ پس از عضویت، روی 'بررسی عضویت من' کلیک کنید
    3️⃣ اگر مشکل دارید، تنظیمات دسترسی را چک کنید
    
    ⚠️ **توجه:** ربات باید ادمین کانال باشد با دسترسی‌های محدود
    
    📝 **بعد از تأیید عضویت، اطلاعات خود را ارسال کنید:**
    
    **نام و نام خانوادگی،شماره دانشجویی**
    
    **مثال:**
    `بهنام احمدی،14044121000`
    """
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def bot_info(update: Update, context: CallbackContext) -> None:
    """اطلاعات وضعیت ربات"""
    try:
        # بررسی وضعیت ربات در کانال
        try:
            bot_member = await context.bot.get_chat_member(
                chat_id=CHANNEL_ID, 
                user_id=context.bot.id
            )
            
            info_text = f"🤖 **وضعیت ربات:**\n"
            info_text += f"• در کانال: `{'✅' if bot_member.status in ['administrator', 'creator'] else '❌'}`\n"
            info_text += f"• وضعیت: `{bot_member.status}`\n"
            
            if bot_member.status == 'administrator':
                info_text += "• ✅ ربات ادمین است\n"
            else:
                info_text += "• ❌ ربات ادمین نیست!\n"
                
        except Exception as e:
            info_text = f"❌ **خطا در بررسی وضعیت ربات:**\n`{str(e)[:100]}`\n"
        
        info_text += f"\n📊 **آمار کاربران تأیید شده:** {len(user_status)}\n"
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)[:100]}")

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
        application.add_handler(CommandHandler("info", bot_info))
        
        # ثبت هندلر برای دکمه‌ها
        application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
        application.add_handler(CallbackQueryHandler(access_settings, pattern="^access_settings$"))
        
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
