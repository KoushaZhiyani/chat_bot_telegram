import os
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from g import UnitSelection  # جایگزین با نام فایل شما

# توکن بات تلگرام
TOKEN = '7805910107:AAGOnv7523WFwzTkphdr--BJB7U-QaqPIqM'

# مسیر فایل CSV
CSV_FILE_PATH = 'Book.csv'

ADMIN_USER_ID = 439165916  # شناسه کاربری تلگرام خود را اینجا قرار دهید


# ذخیره وضعیت کاربران
user_states = {}

# ارسال فایل CSV
async def send_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with open(CSV_FILE_PATH, 'rb') as file:
        await update.message.reply_document(document=file, filename=os.path.basename(CSV_FILE_PATH))


async def active_users_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("شما اجازه دسترسی به این کامند را ندارید.")
        return

    user_count = len(user_states)
    await update.message.reply_text(f"تعداد کاربران فعال: {user_count}")


async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    if document:
        new_file = await document.get_file()
        await new_file.download_to_drive('received_file.csv')
        await update.message.reply_text("فایل دریافت شد. در حال پردازش ...")
        await process_csv('received_file.csv', update)


# پردازش فایل CSV با استفاده از UnitSelection
async def process_csv(file_path: str, update: Update) -> None:
    try:
        # خواندن داده‌ها از فایل CSV
        df = pd.read_csv(file_path, encoding='windows-1256')
        user_id = update.message.from_user.id

        # بررسی و تنظیم مقدار پیش‌فرض برای کاربر در user_states
        if user_id not in user_states:
            user_states[user_id] = {
                "method": 1,  # متد پیش‌فرض
                "day_coff": 10,
                "gap_coff": 10,
                "pr_coff": 10
            }

        # دریافت مقادیر از user_states
        method = user_states[user_id]["method"]
        day_coff = user_states[user_id]["day_coff"]
        gap_coff = user_states[user_id]["gap_coff"]
        pr_coff = user_states[user_id]["pr_coff"]

        # ایجاد شیء UnitSelection
        unit_select_obj = UnitSelection(df, method=method, day_coff=day_coff, gap_coff=gap_coff, pr_coff=pr_coff)

        # پردازش داده‌ها و دریافت لیست برنامه‌ها
        sorted_list = unit_select_obj.evaluate_matrix()
        programs = unit_select_obj.print_matrix(sorted_list)

        # ذخیره برنامه‌ها و شیء UnitSelection برای کاربر
        user_states[user_id].update({
            "programs": programs,
            "current_index": 1,
            "unit_select_obj": unit_select_obj
        })

        # ارسال اولین برنامه به کاربر
        await update.message.reply_text(f"برنامه اول:\n{programs[0]}")
    except Exception as e:
        await update.message.reply_text(f"خطا در پردازش فایل: {e}")


async def send_next_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_states or "programs" not in user_states[user_id]:
        await update.message.reply_text("ابتدا فایل CSV خود را ارسال کنید تا برنامه‌ای ایجاد شود.")
        return

    state = user_states[user_id]
    programs = state["programs"]
    current_index = state["current_index"]

    if current_index < len(programs):
        # ارسال برنامه فعلی
        await update.message.reply_text(f"برنامه {current_index + 1}:\n{programs[current_index]}")
        # بروزرسانی شاخص
        user_states[user_id]["current_index"] += 1
    else:
        await update.message.reply_text("برنامه دیگری وجود ندارد!")


# فرمان start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'سلام! لطفاً در ابتدا با دستور /setmethod، متود موردنظر را انتخاب کرده و یا فایل CSV خود را مستقیما ارسال کنید.\n'
        'Ex: \n/setmethod 1  \n/setmethode 2 day_coff gap_coff pr_coff')


async def search_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username or f"user_{user_id}"

    # بررسی وجود اطلاعات برای کاربر
    if user_id not in user_states or "programs" not in user_states[user_id]:
        await update.message.reply_text("ابتدا فایل CSV خود را ارسال کنید تا برنامه‌ای ایجاد شود.")
        return

    state = user_states[user_id]
    programs = state["programs"]
    current_index = state["current_index"]

    # بررسی برنامه فعلی
    if current_index - 1 < 0 or current_index - 1 >= len(programs):
        await update.message.reply_text("برنامه معتبری برای جستجوی بیشتر یافت نشد.")
        return

    unit_select_obj = state["unit_select_obj"]
    courses = unit_select_obj.df_matrix_course[unit_select_obj.df_matrix_course['id'] == current_index]

    try:
        # تولید فایل جدید با استفاده از all_model
        results_file = unit_select_obj.all_model(courses, current_index)
        if isinstance(results_file, list):
            results_file = pd.DataFrame(results_file)

        # تنظیم نام فایل بر اساس نام کاربری
        file_name = f"@{username}-{current_index}-all-situations.csv"

        # ذخیره فایل
        file_path = f"./{file_name}"
        results_file.to_csv(file_path, index=False, encoding="utf-8")

        # ارسال فایل به کاربر
        await update.message.reply_document(document=open(file_path, 'rb'), filename=file_name)
        await update.message.reply_text(f"فایل {file_name} آپلود شد.")
    except Exception as e:
        await update.message.reply_text(f"خطا در جستجوی بیشتر: {e}")


async def set_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # بررسی وجود آرگومان‌ها
    if len(context.args) < 1:
        await update.message.reply_text(
            "لطفاً متد مورد نظر را با فرمت: /setmethod [1 یا 2] [day_coff] [gap_coff] [pr_coff] وارد کنید.")
        return

    try:
        # استخراج متد
        method = int(context.args[0])
        if method == 1:
            # متد 1 باید فقط یک آرگومان داشته باشد
            if len(context.args) != 1:
                raise ValueError("متد 1 فقط باید یک آرگومان داشته باشد.")

            day_coff = 10
            gap_coff = 10
            pr_coff = 10

            # ذخیره متد انتخابی
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id].update({
                "method": method,
                "day_coff": day_coff,
                "gap_coff": gap_coff,
                "pr_coff": pr_coff
            })
            await update.message.reply_text(f"متد 1 با موفقیت انتخاب شد. فایل csv خود را آپلود کنید")

        elif method == 2:
            # متد 2 باید دقیقاً چهار آرگومان داشته باشد
            if len(context.args) != 4:
                raise ValueError("متد 2 باید با چهار عدد تنظیم شود: /setmethod 2 [day_coff] [gap_coff] [pr_coff]")

            # استخراج مقادیر day_coff, gap_coff, pr_coff
            day_coff = int(context.args[1])
            gap_coff = int(context.args[2])
            pr_coff = int(context.args[3])

            # ذخیره متد و مقادیر در user_states
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id].update({
                "method": method,
                "day_coff": day_coff,
                "gap_coff": gap_coff,
                "pr_coff": pr_coff
            })
            await update.message.reply_text(
                f"متد 2 با مقادیر day_coff={day_coff}, gap_coff={gap_coff}, pr_coff={pr_coff} با موفقیت انتخاب شد. لطفا فایل csv خود را آپلود کنید.")

        else:
            raise ValueError("عدد وارد شده برای متد معتبر نیست. لطفاً عدد 1 یا 2 را وارد کنید.")

    except ValueError as e:
        # مدیریت خطاهای مقدار نامعتبر
        await update.message.reply_text(f"خطا: {e}")


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    if user_id in user_states:
        del user_states[user_id]  # حذف وضعیت کاربر از دیکشنری
        await update.message.reply_text("بات متوقف شد. برای شروع دوباره دستور /start را وارد کنید.")
    else:
        await update.message.reply_text("شما هیچ فعالیت فعالی با بات ندارید.")


# تابع main
def main():
    # ایجاد برنامه
    application = Application.builder().token(TOKEN).build()

    # افزودن هندلرها

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setmethod", set_method))
    application.add_handler(CommandHandler("getcsv", send_csv))
    application.add_handler(CommandHandler("next", send_next_program))
    application.add_handler(CommandHandler("search", search_more))
    application.add_handler(CommandHandler("end", end))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_csv))
    application.add_handler(CommandHandler("activeusers", active_users_count))

    application.run_polling()


if __name__ == '__main__':
    main()
