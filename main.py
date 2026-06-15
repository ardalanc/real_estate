import telebot
import mysql.connector
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from Texts import texts
from config import BOT_TOKEN, DATABASE_CONFIG, DB_NAME, ADMIN_IDS
from DLL import get_admin_level, get_all_admins, add_admin, deactivate_admin, get_stats

telebot.apihelper.API_URL="http://tapi.bale.ai/bot{0}/{1}"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- DATABASE ----------------

def get_connection():
    return mysql.connector.connect(database=DB_NAME,**DATABASE_CONFIG)

# -- visit request --

def update_user_name(telegram_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name = %s WHERE telegram_id = %s", (name, telegram_id))
    conn.commit()
    affected = cur.rowcount
    cur.close()
    conn.close()
    return affected > 0

def get_user_visit_requests(user_db_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
        SELECT vr.id, vr.status, vr.request_time, vr.scheduled_time, vr.admin_message,
               p.title, p.type, p.price, p.deposit, p.rent
        FROM visit_requests vr
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.user_id = %s
        ORDER BY vr.request_time DESC
    """
    cur.execute(query, (user_db_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_user_phone(telegram_id, phone):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()

    query = """
        UPDATE users
        SET phone = %s
        WHERE telegram_id = %s
    """
    cur.execute(query, (phone, telegram_id))
    conn.commit()

    affected = cur.rowcount

    cur.close()
    conn.close()

    return affected > 0

def create_visit_request(property_id, user_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()

    query = """
        INSERT INTO visit_requests (
            property_id,
            user_id,
            status,
            admin_id,
            scheduled_time,
            admin_message,
            is_successful_deal
        )
        VALUES (%s, %s, 'pending', NULL, NULL, NULL, FALSE)
    """
    cur.execute(query, (property_id, user_id))
    conn.commit()

    request_id = cur.lastrowid

    cur.close()
    conn.close()

    return request_id

def get_user_id_by_telegram_id(telegram_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor(dictionary=True)

    query = "SELECT id FROM users WHERE telegram_id = %s LIMIT 1"
    cur.execute(query, (telegram_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return user['id']
    return None

def get_user_by_telegram_id(telegram_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor(dictionary=True)

    query = "SELECT * FROM users WHERE telegram_id = %s LIMIT 1"
    cur.execute(query, (telegram_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return user

# ---------------- MENUE ----------------

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("خرید"),
        KeyboardButton("اجاره")
    )
    markup.add(KeyboardButton("بیشتر"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("افزودن فایل جدید"),
        KeyboardButton("مدیریت فایل ها")
    )
    markup.add(
        KeyboardButton("درخواست های بازدید"),
        KeyboardButton("ارسال پیام به همه کاربران")           
    )
    return markup

def superuser_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("افزودن فایل جدید"),
        KeyboardButton("مدیریت فایل ها")
    )
    markup.add(
        KeyboardButton("درخواست های بازدید"),
        KeyboardButton("ارسال پیام به همه کاربران")
    )
    # ردیف اختصاصی سوپر یوزر
    markup.add(
        KeyboardButton("مدیریت کاربران"),
        KeyboardButton("مدیریت ادمین ها")
    )
    markup.add(KeyboardButton("آمار و گزارش"))
    return markup

def more_menu_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👤 پروفایل من", callback_data="profile_show"),
    )
    return markup

def profile_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✏️ ویرایش شماره تلفن", callback_data="profile_edit_phone"),
        InlineKeyboardButton("📝 تغییر نام", callback_data="profile_edit_name"),
        InlineKeyboardButton("📋 درخواست‌های بازدید من", callback_data="profile_my_visits"),
    )
    return markup

def buy_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_all = InlineKeyboardButton("نمایش تمام فایل‌ها 🏠", callback_data="buy_show_all")
    btn_budget = InlineKeyboardButton("جست‌وجو بر اساس بودجه 💰", callback_data="buy_by_budget")
    markup.add(btn_all, btn_budget)
    return markup

def rent_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🏘 نمایش تمام فایل‌های اجاره", callback_data="rent_all"),
        InlineKeyboardButton("💰 جست‌وجو بر اساس ودیعه", callback_data="rent_by_deposit"),
        InlineKeyboardButton("💸 جست‌وجو بر اساس اجاره ماهانه", callback_data="rent_by_monthly"),
        InlineKeyboardButton("🎯 جست‌وجو ترکیبی", callback_data="rent_by_combo")
    )
    return markup

# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start_handler(message):
    cid = message.chat.id
    level = get_admin_level(cid)

    if level == 'superuser':
        bot.send_message(cid, "خوش امدید", reply_markup=superuser_menu())
        return

    if level == 'admin':
        bot.send_message(cid, "خوش امدید", reply_markup=admin_menu())
        return

    register_user(message)
    bot.send_message(cid, "خوش امدید", reply_markup=main_menu())

# ---------------- VERFECATION ----------------

def register_user(message):

    cid = message.chat.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE telegram_id=%s",(cid,))

    user = cur.fetchone()

    if not user:
        cur.execute("""
            INSERT INTO users
            (telegram_id, username, name)
            VALUES (%s,%s,%s)
        """, (
            cid,
            username,
            first_name,
        ))

        conn.commit()

    cur.close()
    conn.close()

def is_admin(cid):
    return get_admin_level(cid) is not None

def is_superuser(cid):
    return get_admin_level(cid) == 'superuser'

def normalize_phone_number(phone_text):
    # ۱. تبدیل اعداد فارسی به انگلیسی
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    clean = phone_text.translate(trans).strip()
    
    # ۲. حذف کاراکترهای غیر عددی و فضای خالی
    clean = re.sub(r'\D', '', clean)
    
    # ۳. هندل کردن پیش‌شماره‌ها
    if clean.startswith('98') and len(clean) == 12:
        clean = '0' + clean[2:]
    elif clean.startswith('0098') and len(clean) == 14:
        clean = '0' + clean[4:]
    elif len(clean) == 10 and clean.startswith('9'):
        clean = '0' + clean
    
    # ۴. اعتبارسنجی نهایی با regex
    if re.match(r'^09\d{9}$', clean):
        return clean
    return None

# ---------------- MESSAGE HANDLER ----------------
# -- more --
@bot.message_handler(func=lambda message: message.text == "بیشتر")
def more_handler(message):
    bot.send_message(message.chat.id, "یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=more_menu_markup())

# -- buy --
@bot.message_handler(func=lambda message: message.text == "خرید")
def buy_handler(message):
    cid = message.chat.id
    bot.send_message(cid, "لطفاً نحوه نمایش فایل‌های خرید را انتخاب کنید:", reply_markup=buy_options_markup())

# ---------------- CALLBACK HANDLER ----------------
# -- buy --

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "buy_show_all":
        show_properties(cid, mode='all')
    
    elif call.data == "buy_by_budget":
        msg = bot.send_message(cid, "لطفاً **حداقل** بودجه خود را به تومان وارد کنید:\n(مثال: 500000000)")
        bot.register_next_step_handler(msg, process_min_budget)

# -- rent --

@bot.message_handler(func=lambda message: message.text == "اجاره")
def rent_handler(message):
    bot.send_message(message.chat.id, "لطفاً روش جستجو را انتخاب کنید:", reply_markup=rent_options_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('rent_'))
def rent_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "rent_all":
        show_rent_properties(cid, mode='all')
    
    elif call.data == "rent_by_deposit":
        msg = bot.send_message(cid, "حداقل **ودیعه (رهن)** مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, "min")

    elif call.data == "rent_by_monthly":
        msg = bot.send_message(cid, "حداقل **اجاره ماهانه** مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, "min")

    elif call.data == "rent_by_combo":
        msg = bot.send_message(cid, "شروع جستجوی ترکیبی.\nحداقل **ودیعه** را وارد کنید:")
        bot.register_next_step_handler(msg, process_combo_step, {"step": 1})

# -- profile --

STATUS_FA = {
    'pending':  '🕐 در انتظار بررسی',
    'accepted': '✅ تأیید شده',
    'rejected': '❌ رد شده',
}

@bot.callback_query_handler(func=lambda call: call.data.startswith("profile_"))
def profile_callback_handler(call):
    cid = call.message.chat.id
    telegram_id = call.from_user.id

    if call.data == "profile_show":
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            bot.answer_callback_query(call.id, "خطا: کاربر یافت نشد.")
            return

        name     = user.get('name') or '—'
        username = f"@{user['username']}" if user.get('username') else '—'
        phone    = user.get('phone') or 'ثبت نشده'
        joined   = user['created_at'].strftime('%Y/%m/%d') if user.get('created_at') else '—'

        text = (
            f"👤 *پروفایل من*\n\n"
            f"📛 نام: {name}\n"
            f"🔗 یوزرنیم: {username}\n"
            f"📱 شماره موبایل: {phone}\n"
            f"📅 تاریخ عضویت: {joined}"
        )
        bot.send_message(cid, text, parse_mode='Markdown', reply_markup=profile_markup())

    elif call.data == "profile_edit_phone":
        msg = bot.send_message(cid, "📱 شماره موبایل جدید خود را وارد کنید (مثال: 09xxxxxxxxx):")
        bot.register_next_step_handler(msg, process_profile_phone_step)

    elif call.data == "profile_edit_name":
        msg = bot.send_message(cid, "📝 نام جدید خود را وارد کنید:")
        bot.register_next_step_handler(msg, process_profile_name_step)

    elif call.data == "profile_my_visits":
        user_db_id = get_user_id_by_telegram_id(telegram_id)
        if not user_db_id:
            bot.answer_callback_query(call.id, "خطا: کاربر یافت نشد.")
            return

        requests = get_user_visit_requests(user_db_id)

        if not requests:
            bot.send_message(cid, "📋 شما هنوز هیچ درخواست بازدیدی ثبت نکرده‌اید.")
            return

        bot.send_message(cid, f"📋 *درخواست‌های بازدید شما* ({len(requests)} مورد):", parse_mode='Markdown')

        for req in requests:
            status_fa = STATUS_FA.get(req['status'], req['status'])
            prop_type = 'خرید' if req['type'] == 'buy' else 'اجاره'

            if req['type'] == 'buy':
                price_line = f"💰 قیمت: {req['price']:,} تومان" if req.get('price') else ""
            else:
                price_line = (
                    f"💰 ودیعه: {req['deposit']:,} تومان\n"
                    f"💸 اجاره: {req['rent']:,} تومان"
                ) if req.get('deposit') else ""

            scheduled = ""
            if req.get('scheduled_time'):
                scheduled = f"\n🗓 زمان بازدید: {req['scheduled_time'].strftime('%Y/%m/%d %H:%M')}"

            admin_msg = ""
            if req.get('admin_message'):
                admin_msg = f"\n💬 پیام مشاور: {req['admin_message']}"

            text = (
                f"🏠 *{req['title']}* ({prop_type})\n"
                f"{price_line}\n"
                f"📌 وضعیت: {status_fa}\n"
                f"🕐 تاریخ درخواست: {req['request_time'].strftime('%Y/%m/%d')}"
                f"{scheduled}{admin_msg}"
            )
            bot.send_message(cid, text, parse_mode='Markdown')

# -- profile steps --

def process_profile_phone_step(message):
    cid = message.chat.id
    phone = normalize_phone_number(message.text)
    if not phone:
        msg = bot.send_message(cid, "❌ شماره نامعتبر است. لطفاً با فرمت 09xxxxxxxxx وارد کنید:")
        bot.register_next_step_handler(msg, process_profile_phone_step)
        return
    update_user_phone(message.from_user.id, phone)
    bot.send_message(cid, f"✅ شماره موبایل با موفقیت به {phone} تغییر یافت.")

def process_profile_name_step(message):
    cid = message.chat.id
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        msg = bot.send_message(cid, "❌ نام باید بین ۲ تا ۵۰ کاراکتر باشد. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, process_profile_name_step)
        return
    update_user_name(message.from_user.id, name)
    bot.send_message(cid, f"✅ نام شما با موفقیت به «{name}» تغییر یافت.")

# -- visit request --

@bot.callback_query_handler(func=lambda call: call.data.startswith("visit_"))
def handle_visit_request(call):
    cid = call.message.chat.id
    pid = call.data.split('_')[1] # Property ID
    
    # چک کردن شماره تلفن در دیتابیس
    user = get_user_by_telegram_id(call.from_user.id) # تابعی که قبلا گفتی داری
    
    if not user or not user.get('phone'):
        msg = bot.send_message(cid, "برای ثبت درخواست بازدید، لطفاً شماره موبایل خود را وارد کنید (مثال: 0912xxxxxxx):")
        bot.register_next_step_handler(msg, process_phone_step, pid)
    else:
        ask_for_confirmation(cid, pid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_visit_") or call.data == "cancel_visit")
def handle_visit_confirmation(call):
    cid = call.message.chat.id
    
    if call.data == "cancel_visit":
        bot.answer_callback_query(call.id, "درخواست لغو شد.")
        bot.delete_message(cid, call.message.message_id)
        return

    pid = int(call.data.split('_')[2])
    user_db_id = get_user_id_by_telegram_id(call.from_user.id)

    if not user_db_id:
        bot.answer_callback_query(call.id, "خطا: کاربر یافت نشد.")
        return

    # چک کردن اینکه آیا درخواست پندینگ قبلی وجود داره یا نه
    if is_visit_request_pending(user_db_id, pid):
        bot.answer_callback_query(call.id, "شما قبلاً برای این ملک درخواست داده‌اید.")
        bot.send_message(cid, "⚠️ درخواست شما قبلاً ثبت شده و در حال بررسی است.")
    else:
        # ثبت در دیتابیس (property_id اول، user_id دوم)
        create_visit_request(pid, user_db_id)
        bot.answer_callback_query(call.id, "موفقیت‌آمیز!")
        bot.edit_message_text("✅ درخواست شما با موفقیت ثبت شد. مشاور به‌زودی با شما تماس می‌گیرد.", cid, call.message.message_id)


# ---------------- FUNCTION ----------------
# -- buy --

def process_min_budget(message):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, "لطفاً فقط عدد وارد کنید. دوباره حداقل بودجه را ارسال کنید:")
        bot.register_next_step_handler(msg, process_min_budget)
        return
    
    min_price = int(message.text)
    msg = bot.send_message(cid, f"حداقل بودجه: {min_price:,} تومان\nحالا **حداکثر** بودجه را وارد کنید:")
    bot.register_next_step_handler(msg, process_max_budget, min_price)

def process_max_budget(message, min_price):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, "لطفاً فقط عدد وارد کنید. حداکثر بودجه را ارسال کنید:")
        bot.register_next_step_handler(msg, process_max_budget, min_price)
        return
    
    max_price = int(message.text)
    bot.send_message(cid, f"در حال جست‌وجو برای بازه {min_price:,} تا {max_price:,} تومان...")
    show_properties(cid, mode='budget', min_p=min_price, max_p=max_price)

def show_properties(cid, mode='all', min_p=0, max_p=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if mode == 'all':
        query = "SELECT * FROM properties WHERE type='buy' AND status='available' ORDER BY created_at DESC"
        params = ()
    else:
        query = "SELECT * FROM properties WHERE type='buy' AND status='available' AND price BETWEEN %s AND %s ORDER BY price ASC"
        params = (min_p, max_p)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(cid, "متأسفانه موردی یافت نشد. 😕")
    else:
        for row in rows:
            # قالب‌بندی متن مشابه عکسی که فرستادی
            caption = (
                f"🏠 عنوان: {row['title']}\n\n"
                f"💰 قیمت: {row['price']:,} تومان\n"
                f"📐 متراژ: {row['metraj']} متر\n"
                f"🛏 خواب: {row['rooms']}\n\n"
                f"📝 توضیحات:\n{row['description']}"
            )
            
            # پیدا کردن عکس‌های ملک از جدول property_images
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img_row = cursor.fetchone()
            
            # دکمه درخواست بازدید
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📅 درخواست بازدید", callback_data=f"visit_{row['id']}"))
            
            if img_row:
                bot.send_photo(cid, img_row['telegram_file_id'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(cid, caption, reply_markup=markup)
                
    cursor.close()
    conn.close()

# -- rent --

def process_deposit_step(message, type_mode, min_val=None):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "لطفاً عدد معتبری وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, f"حداقل ودیعه: {val:,}\nحالا **حداکثر ودیعه** را وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, "max", val)
    else:
        show_rent_properties(cid, mode='deposit', filters={'min_dep': min_val, 'max_dep': val})

def process_rent_step(message, type_mode, min_val=None):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "لطفاً عدد معتبری وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, f"حداقل اجاره: {val:,}\nحالا **حداکثر اجاره** را وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, "max", val)
    else:
        show_rent_properties(cid, mode='rent_val', filters={'min_rent': min_val, 'max_rent': val})

def process_combo_step(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "ورودی نامعتبر. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, process_combo_step, data)
        return

    step = data['step']
    if step == 1:
        data.update({'min_dep': val, 'step': 2})
        msg = bot.send_message(cid, "حداکثر **ودیعه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 2:
        data.update({'max_dep': val, 'step': 3})
        msg = bot.send_message(cid, "حداقل **اجاره ماهانه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 3:
        data.update({'min_rent': val, 'step': 4})
        msg = bot.send_message(cid, "حداکثر **اجاره ماهانه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 4:
        data['max_rent'] = val
        show_rent_properties(cid, mode='combo', filters=data)

def show_rent_properties(cid, mode='all', filters=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM properties WHERE type='rent' AND status='available' "
    params = []

    if mode == 'deposit':
        query += "AND deposit BETWEEN %s AND %s"
        params = [filters['min_dep'], filters['max_dep']]
    elif mode == 'rent_val':
        query += "AND rent BETWEEN %s AND %s"
        params = [filters['min_rent'], filters['max_rent']]
    elif mode == 'combo':
        query += "AND deposit BETWEEN %s AND %s AND rent BETWEEN %s AND %s"
        params = [filters['min_dep'], filters['max_dep'], filters['min_rent'], filters['max_rent']]

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(cid, "موردی با این مشخصات پیدا نشد. 📍")
    else:
        for row in rows:
            caption = (
                f"🏠 عنوان: {row['title']}\n\n"
                f"💰 ودیعه: {row['deposit']:,} تومان\n"
                f"💸 اجاره: {row['rent']:,} تومان\n"
                f"📐 متراژ: {row['metraj']} متر\n"
                f"🛏 خواب: {row['rooms']}\n\n"
                f"📝 توضیحات:\n{row['description']}"
            )
            
            # دریافت تصویر اول
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img = cursor.fetchone()
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📅 درخواست بازدید", callback_data=f"visit_{row['id']}"))

            if img:
                bot.send_photo(cid, img['telegram_file_id'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(cid, caption, reply_markup=markup)

    cursor.close()
    conn.close()

# -- visit request --

def process_phone_step(message, pid):
    cid = message.chat.id
    phone = normalize_phone_number(message.text)
    
    if not phone:
        msg = bot.send_message(cid, "❌ شماره نامعتبر است. لطفاً شماره موبایل را دقیقاً با فرمت 09xxxxxxxxx وارد کنید:")
        bot.register_next_step_handler(msg, process_phone_step, pid)
        return
    
    # ذخیره شماره در دیتابیس
    update_user_phone(message.from_user.id, phone)
    bot.send_message(cid, "✅ شماره شما با موفقیت ثبت شد.")
    ask_for_confirmation(cid, pid)

def ask_for_confirmation(cid, pid):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ بله، درخواست ثبت شود", callback_data=f"confirm_visit_{pid}"),
        InlineKeyboardButton("❌ انصراف", callback_data="cancel_visit")
    )
    bot.send_message(cid, "آیا از درخواست بازدید برای این ملک اطمینان دارید؟ مشاور با شما تماس خواهد گرفت.", reply_markup=markup)

# تابع کمکی برای چک کردن درخواست تکراری (در DLL.py اضافه کن)
def is_visit_request_pending(user_id, pid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM visit_requests WHERE user_id = %s AND property_id = %s AND status = 'pending' LIMIT 1",
        (user_id, pid)
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

# ---------------- HELPERS ----------------

def normalize_number(text):
    # تبدیل اعداد فارسی/عربی به انگلیسی
    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
    english_numbers = '0123456789'
    
    translation_table = str.maketrans(persian_numbers + arabic_numbers, english_numbers * 2)
    clean_text = text.translate(translation_table).replace(',', '').replace('،', '').strip()
    
    return int(clean_text) if clean_text.isdigit() else None


# ================ ADMIN PANEL ================

# -- درخواست های بازدید (ادمین) --

@bot.message_handler(func=lambda m: m.text == "درخواست های بازدید" and is_admin(m.chat.id))
def admin_visit_requests(message):
    cid = message.chat.id
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT vr.id, vr.status, vr.request_time,
               u.name AS user_name, u.phone AS user_phone, u.telegram_id AS user_tid,
               p.title AS prop_title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.status = 'pending'
        ORDER BY vr.request_time ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        bot.send_message(cid, "📋 هیچ درخواست در انتظاری وجود ندارد.")
        return

    bot.send_message(cid, f"📋 *درخواست‌های pending* ({len(rows)} مورد):", parse_mode='Markdown')
    for req in rows:
        text = (
            f"🏠 ملک: {req['prop_title']}\n"
            f"👤 کاربر: {req['user_name'] or '—'}\n"
            f"📱 تلفن: {req['user_phone'] or 'ثبت نشده'}\n"
            f"🕐 زمان درخواست: {req['request_time'].strftime('%Y/%m/%d %H:%M')}"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ تأیید", callback_data=f"vr_accept_{req['id']}"),
            InlineKeyboardButton("❌ رد",    callback_data=f"vr_reject_{req['id']}"),
        )
        bot.send_message(cid, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("vr_accept_") or c.data.startswith("vr_reject_"))
def admin_handle_visit(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts  = call.data.split("_")
    action = parts[1]
    vr_id  = int(parts[2])

    if action == "accept":
        msg = bot.send_message(cid, "📅 زمان بازدید را وارد کنید:")
        bot.register_next_step_handler(msg, admin_set_visit_time, vr_id)
    else:
        msg = bot.send_message(cid, "💬 دلیل رد درخواست را بنویسید (یا «—» برای بدون دلیل):")
        bot.register_next_step_handler(msg, admin_reject_visit, vr_id)
    bot.delete_message(cid, call.message.message_id)


def admin_set_visit_time(message, vr_id):
    cid = message.chat.id
    scheduled = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT u.telegram_id AS user_tid, p.title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.id = %s
    """, (vr_id,))
    row = cur.fetchone()
    cur.execute("""
        UPDATE visit_requests
        SET status = 'accepted', admin_message = %s,
            admin_id = (SELECT id FROM admins WHERE telegram_id = %s LIMIT 1)
        WHERE id = %s
    """, (f"زمان بازدید: {scheduled}", cid, vr_id))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(cid, f"✅ درخواست تأیید شد. زمان: {scheduled}")
    if row:
        bot.send_message(
            row['user_tid'],
            f"✅ درخواست بازدید شما برای *{row['title']}* تأیید شد!\n🗓 زمان: {scheduled}",
            parse_mode='Markdown'
        )


def admin_reject_visit(message, vr_id):
    cid = message.chat.id
    reason = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT u.telegram_id AS user_tid, p.title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.id = %s
    """, (vr_id,))
    row = cur.fetchone()
    cur.execute("""
        UPDATE visit_requests
        SET status = 'rejected', admin_message = %s,
            admin_id = (SELECT id FROM admins WHERE telegram_id = %s LIMIT 1)
        WHERE id = %s
    """, (reason if reason != '—' else None, cid, vr_id))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(cid, "❌ درخواست رد شد.")
    if row:
        user_text = f"❌ متأسفانه درخواست بازدید شما برای *{row['title']}* رد شد."
        if reason != '—':
            user_text += f"\n💬 دلیل: {reason}"
        bot.send_message(row['user_tid'], user_text, parse_mode='Markdown')


# -- ارسال پیام به همه کاربران --

@bot.message_handler(func=lambda m: m.text == "ارسال پیام به همه کاربران" and is_admin(m.chat.id))
def admin_broadcast_start(message):
    cid = message.chat.id
    msg = bot.send_message(cid, "✍️ متن پیام را بنویسید:")
    bot.register_next_step_handler(msg, admin_broadcast_send)


def admin_broadcast_send(message):
    cid = message.chat.id
    text = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT telegram_id FROM users WHERE is_blocked = FALSE")
    users = cur.fetchall()
    cur.close()
    conn.close()
    sent, failed = 0, 0
    for u in users:
        try:
            bot.send_message(u['telegram_id'], f"📢 *پیام از مشاور:*\n\n{text}", parse_mode='Markdown')
            sent += 1
        except Exception:
            failed += 1
    bot.send_message(cid, f"✅ ارسال تمام شد.\n📤 موفق: {sent} | ❌ ناموفق: {failed}")


# ================ SUPERUSER PANEL ================

# -- مدیریت کاربران --

@bot.message_handler(func=lambda m: m.text == "مدیریت کاربران" and is_superuser(m.chat.id))
def superuser_users(message):
    cid = message.chat.id
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, telegram_id, name, username, phone, is_blocked FROM users ORDER BY created_at DESC LIMIT 30")
    users = cur.fetchall()
    cur.close()
    conn.close()

    if not users:
        bot.send_message(cid, "هیچ کاربری ثبت نشده.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for u in users:
        blocked = "🔴" if u['is_blocked'] else "🟢"
        label   = u['name'] or u['username'] or str(u['telegram_id'])
        markup.add(InlineKeyboardButton(f"{blocked} {label}", callback_data=f"suuser_{u['id']}"))
    bot.send_message(cid, f"👥 *کاربران* ({len(users)} مورد):", parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("suuser_"))
def superuser_user_detail(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    user_id = int(call.data.split("_")[1])
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    u = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS cnt FROM visit_requests WHERE user_id = %s", (user_id,))
    visit_cnt = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    if not u:
        bot.answer_callback_query(call.id, "کاربر پیدا نشد.")
        return
    status = "🔴 بلاک" if u['is_blocked'] else "🟢 فعال"
    text = (
        f"👤 *{u['name'] or '—'}*\n"
        f"🔗 @{u['username'] or '—'}\n"
        f"📱 {u['phone'] or 'ثبت نشده'}\n"
        f"🆔 `{u['telegram_id']}`\n"
        f"📋 درخواست‌های بازدید: {visit_cnt}\n"
        f"📌 وضعیت: {status}"
    )
    action_btn = (
        InlineKeyboardButton("🔓 رفع بلاک", callback_data=f"unblock_{user_id}")
        if u['is_blocked'] else
        InlineKeyboardButton("🚫 بلاک", callback_data=f"block_{user_id}")
    )
    markup = InlineKeyboardMarkup()
    markup.add(action_btn)
    bot.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("block_") or c.data.startswith("unblock_"))
def superuser_toggle_block(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    action  = "block" if call.data.startswith("block_") else "unblock"
    user_id = int(call.data.split("_")[1])
    new_val = True if action == "block" else False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = %s WHERE id = %s", (new_val, user_id))
    conn.commit()
    cur.close()
    conn.close()
    label = "🚫 بلاک شد" if new_val else "🔓 رفع بلاک شد"
    bot.answer_callback_query(call.id, label)
    bot.delete_message(cid, call.message.message_id)


# -- مدیریت ادمین ها --

@bot.message_handler(func=lambda m: m.text == "مدیریت ادمین ها" and is_superuser(m.chat.id))
def superuser_admins(message):
    cid = message.chat.id
    admins = get_all_admins()
    markup = InlineKeyboardMarkup(row_width=1)
    for a in admins:
        crown  = "👑" if a['is_superuser'] else "🔧"
        active = "✅" if a['is_active']    else "🔴"
        markup.add(InlineKeyboardButton(
            f"{crown} {a['name'] or a['telegram_id']} {active}",
            callback_data=f"suadmin_{a['id']}"
        ))
    markup.add(InlineKeyboardButton("➕ افزودن ادمین جدید", callback_data="suadmin_add"))
    bot.send_message(cid, f"🛡️ *ادمین‌ها* ({len(admins)} نفر):", parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "suadmin_add")
def superuser_add_admin_start(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    msg = bot.send_message(cid, "🆔 آیدی عددی تلگرام ادمین جدید را وارد کنید:")
    bot.register_next_step_handler(msg, superuser_add_admin_step2)


def superuser_add_admin_step2(message):
    cid = message.chat.id
    if not message.text.strip().isdigit():
        bot.send_message(cid, "❌ آیدی باید فقط عدد باشد.")
        return
    tid = int(message.text.strip())
    msg = bot.send_message(cid, "📛 نام ادمین جدید را وارد کنید:")
    bot.register_next_step_handler(msg, superuser_add_admin_step3, tid)


def superuser_add_admin_step3(message, tid):
    cid = message.chat.id
    name = message.text.strip()
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👑 سوپر یوزر",    callback_data=f"addadmin_{tid}_{name}_super"),
        InlineKeyboardButton("🔧 ادمین معمولی", callback_data=f"addadmin_{tid}_{name}_normal"),
    )
    bot.send_message(cid, f"سطح دسترسی *{name}* را انتخاب کنید:", parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("addadmin_"))
def superuser_confirm_add_admin(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    # addadmin_{tid}_{name}_{super|normal}
    parts = call.data.split("_", 3)
    tid   = int(parts[1])
    name  = parts[2]
    level = parts[3]
    add_admin(tid, name, is_superuser_flag=(level == "super"))
    label = "👑 سوپر یوزر" if level == "super" else "🔧 ادمین معمولی"
    bot.answer_callback_query(call.id, "✅ ادمین اضافه شد.")
    bot.edit_message_text(f"✅ *{name}* به عنوان {label} اضافه شد.", cid, call.message.message_id, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda c: c.data.startswith("suadmin_") and c.data != "suadmin_add")
def superuser_admin_detail(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    admin_id = int(call.data.split("_")[1])
    admins = get_all_admins()
    a = next((x for x in admins if x['id'] == admin_id), None)
    if not a:
        bot.answer_callback_query(call.id, "ادمین پیدا نشد.")
        return
    crown  = "👑 سوپر یوزر" if a['is_superuser'] else "🔧 ادمین معمولی"
    active = "✅ فعال" if a['is_active'] else "🔴 غیرفعال"
    text = (
        f"*{a['name'] or '—'}*\n"
        f"🆔 `{a['telegram_id']}`\n"
        f"🏷 {crown}\n"
        f"📌 {active}"
    )
    markup = InlineKeyboardMarkup()
    if a['is_active']:
        markup.add(InlineKeyboardButton("🔴 غیرفعال‌سازی", callback_data=f"deactivateadmin_{a['telegram_id']}"))
    bot.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("deactivateadmin_"))
def superuser_deactivate_admin(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    tid = int(call.data.split("_")[1])
    deactivate_admin(tid)
    bot.answer_callback_query(call.id, "🔴 ادمین غیرفعال شد.")
    bot.delete_message(cid, call.message.message_id)


# -- آمار و گزارش --

@bot.message_handler(func=lambda m: m.text == "آمار و گزارش" and is_superuser(m.chat.id))
def superuser_stats(message):
    cid = message.chat.id
    s = get_stats()
    text = (
        "📊 *آمار کلی سیستم*\n\n"
        f"👥 کاربران:\n"
        f"  • کل: {s['total_users']}\n"
        f"  • بلاک‌شده: {s['blocked_users']}\n"
        f"  • عضو ۳۰ روز اخیر: {s['new_users_30d']}\n\n"
        f"🏠 ملک‌ها:\n"
        f"  • موجود: {s['available_props']}\n"
        f"  • فروخته‌شده: {s['sold_props']}\n\n"
        f"📋 درخواست‌های بازدید:\n"
        f"  • در انتظار: {s['pending_visits']}\n"
        f"  • معاملات موفق: {s['successful_deals']}"
    )
    bot.send_message(cid, text, parse_mode='Markdown')


# ---------------- LISTENER ----------------

def info_listener(messages):
    for message in messages:
        user_id = message.chat.id
        username = message.chat.username or "No Username"
        text = message.text or f"[{message.content_type}]"
        
        print(f"\n--- [New Message] ---")
        print(f"👤 User: {username} ({user_id})")
        print(f"💬 Content: {text}")
        print(f"----------------------\n")
bot.set_update_listener(info_listener)

# ---------------- RUN BOT ----------------

print("robot is runing")
bot.infinity_polling()