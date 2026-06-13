import telebot
import mysql.connector
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from Texts import texts
from config import BOT_TOKEN, DATABASE_CONFIG, DB_NAME, PAGE_SIZE, ADMIN_IDS, ITEMS_PER_PAGE, VISIT_ITEMS_PER_PAGE

telebot.apihelper.API_URL="http://tapi.bale.ai/bot{0}/{1}"

bot = telebot.TeleBot(BOT_TOKEN)

user_state = {}
user_data = {}
user_results = {}
admin_states = {}
admin_data = {}


# ---------------- DATABASE ----------------

def get_connection():
    return mysql.connector.connect(
        database=DB_NAME,
        **DATABASE_CONFIG
    )


def get_buy_properties_by_price(price):

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT * FROM properties
    WHERE type='buy'
    AND status='available'
    AND price <= %s
    ORDER BY price ASC
    """

    cur.execute(query, (price,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def get_all_buy_properties():

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT * FROM properties
    WHERE type='buy'
    AND status='available'
    ORDER BY created_at DESC
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def get_property_images(property_id):

    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT telegram_file_id
    FROM property_images
    WHERE property_id=%s
    """

    cur.execute(query, (property_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [r[0] for r in rows]


# ---------------- DATABASE HELPER ----------------


def get_rent_properties_by_price(price):

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT * FROM properties
    WHERE type='rent'
    AND status='available'
    AND price <= %s
    ORDER BY price ASC
    """

    cur.execute(query, (price,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def get_all_rent_properties():

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    query = """
    SELECT * FROM properties
    WHERE type='rent'
    AND status='available'
    ORDER BY created_at DESC
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ---------------- MENUS ----------------


def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton(texts["BUY"]),
        KeyboardButton(texts["RENT"])
    )
    kb.add(KeyboardButton(texts["MORE"]))
    return kb


def budget_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton(texts["BUDGET_ENTER"]),
        KeyboardButton(texts["SHOW_ALL"])
    )
    kb.add(KeyboardButton(texts["BACK"]))
    return kb


# ----------------------------------------------------


def save_visit_request(cid, property_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE telegram_id=%s",
        (cid,)
    )
    row = cur.fetchone()

    if not row:
        bot.send_message(cid, "❌ خطا: کاربر یافت نشد")
        return

    user_id = row[0]

    cur.execute("""
        INSERT INTO visit_requests (property_id, user_id)
        VALUES (%s, %s)
    """, (property_id, user_id))

    conn.commit()
    cur.close()
    conn.close()

    bot.send_message(
        cid,
        "درخواست بازدید ثبت شد ✔️\nکارشناسان ما به‌زودی با شما تماس می‌گیرند."
    )



def get_all_users():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users")

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [r[0] for r in rows]


def send_visit_page(chat_id, page):

    total = count_visit_requests()

    if total == 0:
        bot.send_message(chat_id, texts["NO_VISIT_REQUESTS"])
        return

    offset = (page - 1) * VISIT_ITEMS_PER_PAGE

    visits = get_visit_requests_paginated(
        VISIT_ITEMS_PER_PAGE,
        offset
    )

    total_pages = (total + VISIT_ITEMS_PER_PAGE - 1) // VISIT_ITEMS_PER_PAGE

    text = texts["VISIT_LIST_HEADER"] + "\n\n"

    kb = InlineKeyboardMarkup()

    for v in visits:

        text += f"""
🆔 {v['id']}
🏠 ملک: {v['property_title']}
👤 {v['first_name']} (@{v['username']})
📞 {v['phone']}
📊 وضعیت: {v['status']}
⏰ {v['created_at']}
--------------------
"""

        kb.row(
            InlineKeyboardButton(
                texts["VISIT_APPROVE"],
                callback_data=f"vapprove_{v['id']}_{page}"
            ),
            InlineKeyboardButton(
                texts["VISIT_REJECT"],
                callback_data=f"vreject_{v['id']}_{page}"
            )
        )

        kb.row(
            InlineKeyboardButton(
                texts["VISIT_CONTACTED"],
                callback_data=f"vcontact_{v['id']}_{page}"
            ),
            InlineKeyboardButton(
                texts["VISIT_DELETE"],
                callback_data=f"vdelete_{v['id']}_{page}"
            )
        )

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton("⬅", callback_data=f"vpage_{page-1}")
        )

    if page < total_pages:
        nav.append(
            InlineKeyboardButton("➡", callback_data=f"vpage_{page+1}")
        )

    if nav:
        kb.row(*nav)

    bot.send_message(chat_id, text, reply_markup=kb)


def count_visit_requests():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM visit_requests")

    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return total

def get_visit_requests_paginated(limit, offset):

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT vr.id,
               vr.phone,
               vr.status,
               vr.created_at,
               u.first_name,
               u.username,
               p.title AS property_title
        FROM visit_requests vr
        LEFT JOIN users u ON vr.user_id = u.user_id
        LEFT JOIN properties p ON vr.property_id = p.id
        ORDER BY vr.id DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def update_visit_status(visit_id, status):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE visit_requests SET status=%s WHERE id=%s",
        (status, visit_id)
    )

    conn.commit()

    cur.close()
    conn.close()

def delete_visit_request(visit_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM visit_requests WHERE id=%s",
        (visit_id,)
    )

    conn.commit()

    cur.close()
    conn.close()


def is_admin(user_id):
    return user_id in ADMIN_IDS



def get_all_properties():

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM properties ORDER BY id DESC")

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def delete_property_db(pid):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM properties WHERE id=%s", (pid,))

    conn.commit()

    cur.close()
    conn.close()


def save_property(title, price, type, description, metraj, rooms, photo):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO properties
        (title, price, type, description, metraj, rooms, photo, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'available')
    """, (
        title,
        price,
        type,
        description,
        metraj,
        rooms,
        photo
    ))

    conn.commit()

    cur.close()
    conn.close()

def admin_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton(texts["ADMIN_ADD_PROPERTY"]),
        KeyboardButton(texts["ADMIN_LIST_PROPERTIES"])
    )
    kb.add(
        KeyboardButton(texts["ADMIN_VISIT_REQUESTS"]),
        KeyboardButton(texts["ADMIN_BROADCAST"])
    )

    return kb


def get_properties_paginated(limit, offset):

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM properties
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def count_properties():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM properties")

    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return total



def send_properties_page(chat_id, page):

    total = count_properties()

    if total == 0:
        bot.send_message(chat_id, texts["NO_PROPERTIES"])
        return

    offset = (page - 1) * ITEMS_PER_PAGE

    properties = get_properties_paginated(
        ITEMS_PER_PAGE,
        offset
    )

    text = texts["PROPERTIES_LIST_HEADER"] + "\n\n"

    for p in properties:
        text += f"""
🆔 {p['id']}
🏠 {p['title']}
💰 {p['price']}
📐 {p['metraj']} متر
🛏 {p['rooms']} خواب
📊 {p['status']}
--------------------
"""

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    kb = InlineKeyboardMarkup()

    if page > 1:
        kb.add(
            InlineKeyboardButton(
                "⬅ قبلی",
                callback_data=f"upage_{page-1}"
            )
        )

    if page < total_pages:
        kb.add(
            InlineKeyboardButton(
                "بعدی ➡",
                callback_data=f"upage_{page+1}"
            )
        )

    bot.send_message(
        chat_id,
        text,
        reply_markup=kb
    )




# ----------------------------------------------------
# ---------------- HELPERS ----------------

def show_property(cid, prop):

    images = get_property_images(prop["id"])

    caption = f"""
🏠 {prop["title"]}

💰 قیمت: {prop["price"]:,} تومان
📐 متراژ: {prop["metr"]} متر
🛏 خواب: {prop["rooms"]}

📝 توضیحات:
{prop["description"]}
"""

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "📅 درخواست بازدید",
            callback_data=f"visit_{prop['id']}"
        )
    )

    if images:
        bot.send_photo(
            cid,
            images[0],
            caption=caption,
            reply_markup=kb
        )

        for img in images[1:]:
            bot.send_photo(cid, img)

    else:
        bot.send_message(
            cid,
            caption,
            reply_markup=kb
        )


def show_properties_list(cid, properties):

    if not properties:
        bot.send_message(cid, "❌ فایلی پیدا نشد")
        return

    for prop in properties:
        show_property(cid, prop)


def ask_for_phone(cid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("📱 ارسال شماره", request_contact=True)
    )
    kb.add(texts["BACK"])

    bot.send_message(
        cid,
        "لطفاً شماره خود را ارسال کنید:",
        reply_markup=kb
    )
# ---------------- REGISTER USER ----------------


def register_user(message):

    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE telegram_id=%s",(telegram_id,))

    user = cur.fetchone()

    if not user:
        cur.execute("""
            INSERT INTO users
            (telegram_id, username, first_name)
            VALUES (%s,%s,%s)
        """, (
            telegram_id,
            username,
            first_name,
        ))

        conn.commit()

    cur.close()
    conn.close()

# ---------------- SHOW PAGE ----------------


def show_properties_page(chat_id, properties, page=0):

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    page_items = properties[start:end]

    for prop in page_items:
        show_property(chat_id, prop)

    keyboard = InlineKeyboardMarkup()

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                texts["PREVIOUS_PAGE"],
                callback_data=f"upage_{page-1}"
            )
        )

    if end < len(properties):
        buttons.append(
            InlineKeyboardButton(
                texts["NEXT_PAGE"],
                callback_data=f"upage_{page+1}"
            )
        )

    if buttons:
        keyboard.row(*buttons)

        bot.send_message(
            chat_id,
            texts["PAGE_NAVIGATION"],
            reply_markup=keyboard
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("upage_"))
def page_handler(call):

    cid = call.message.chat.id

    page = int(call.data.split("_")[1])

    properties = user_results.get(cid, [])

    if not properties:
        return

    bot.delete_message(cid, call.message.message_id)

    show_properties_page(cid, properties, page)


# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start_handler(message):

    cid = message.chat.id
    user_state[cid] = "none"
    
    register_user(message)   

    bot.send_message(
        cid,
        texts["WELCOME"],
        reply_markup=main_menu()
    )

# ---------------- BUY MENU ----------------

@bot.message_handler(func=lambda m: m.text == texts["BUY"])
def buy_handler(message):

    cid = message.chat.id
    user_state[cid] = "buy_menu"

    bot.send_message(
        cid,
        texts["ASK_BUDGET"],
        reply_markup=budget_menu()
    )

# ---------------- SHOW ALL BUY ----------------

@bot.message_handler(func=lambda m: m.text == texts["SHOW_ALL"])
def show_all_buy(message):

    cid = message.chat.id

    if user_state.get(cid) != "buy_menu":
        return

    properties = get_all_buy_properties()
    show_properties_list(cid, properties)

# ---------------- ENTER PRICE ----------------

@bot.message_handler(func=lambda m: m.text == texts["BUDGET_ENTER"])
def enter_budget(message):

    cid = message.chat.id

    if user_state.get(cid) != "buy_menu":
        return

    user_state[cid] = "buy_price"

    bot.send_message(
        cid,
        texts["ASK_PRICE"]
    )

# ---------------- GET PRICE ----------------

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "buy_price")
def get_price(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_PRICE"])
        return

    price = int(message.text)

    properties = get_buy_properties_by_price(price)

    bot.send_message(
        cid,
        texts["SEARCH_BUY"].format(price=price)
    )

    show_properties_list(cid, properties)

    user_state[cid] = "buy_menu"


# ---------------- GET NUMBER ----------------

@bot.message_handler(content_types=['contact'])
def phone_handler(message):

    cid = message.chat.id
    phone = message.contact.phone_number

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET phone=%s WHERE telegram_id=%s",
        (phone, cid)
    )
    conn.commit()

    cur.close()
    conn.close()

    bot.send_message(cid, "شماره شما ثبت شد ✔️")

    if user_state.get(cid) and user_state[cid].startswith("visit_"):
        property_id = int(user_state[cid].split("_")[1])
        save_visit_request(cid, property_id)

# ---------------- VISIT REQUEST ----------------


@bot.callback_query_handler(func=lambda c: c.data.startswith("visit_"))
def visit_request_start(call):

    cid = call.message.chat.id
    property_id = int(call.data.split("_")[1])

    user_state[cid] = f"visit_{property_id}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT phone FROM users WHERE telegram_id=%s",
        (cid,)
    )
    phone = cur.fetchone()
    cur.close()
    conn.close()

    if not phone or not phone[0]:
        ask_for_phone(cid)
        bot.answer_callback_query(call.id, "شماره لازم است")
        return

    save_visit_request(cid, property_id)
    bot.answer_callback_query(call.id)

# ---------------- RENT ----------------

@bot.message_handler(func=lambda m: m.text == texts["RENT"])
def rent_handler(message):

    cid = message.chat.id
    user_state[cid] = "rent_menu"

    bot.send_message(
        cid,
        texts["ASK_RENT_BUDGET"],
        reply_markup=budget_menu()
    )


@bot.message_handler(func=lambda m: m.text == texts["SHOW_ALL"])
def show_all_rent(message):

    cid = message.chat.id

    if user_state.get(cid) != "rent_menu":
        return

    properties = get_all_rent_properties()

    show_properties_list(cid, properties)


@bot.message_handler(func=lambda m: m.text == texts["BUDGET_ENTER"])
def enter_rent_budget(message):

    cid = message.chat.id

    if user_state.get(cid) != "rent_menu":
        return

    user_state[cid] = "rent_price"

    bot.send_message(
        cid,
        texts["ASK_RENT_PRICE"]
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "rent_price")
def get_rent_price(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_PRICE"])
        return

    price = int(message.text)

    properties = get_rent_properties_by_price(price)

    bot.send_message(
        cid,
        texts["SEARCH_RENT"].format(price=price)
    )

    show_properties_list(cid, properties)

    user_state[cid] = "rent_menu"


# ---------------- BACK ----------------

@bot.message_handler(func=lambda m: m.text == texts["BACK"])
def back_handler(message):

    cid = message.chat.id

    user_state[cid] = "none"

    bot.send_message(
        cid,
        texts["WELCOME"],
        reply_markup=main_menu()
    )


# ---------------- ADMIN MENUE ----------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):

    uid = message.from_user.id

    if not is_admin(uid):
        bot.send_message(message.chat.id, texts["ACCESS_DENIED"])
        return

    bot.send_message(
        message.chat.id,
        texts["ADMIN_WELCOME"],
        reply_markup=admin_main_menu()
    )

@bot.message_handler(func=lambda m: m.text == texts["ADMIN_ADD_PROPERTY"])
def admin_add_property(message):

    uid = message.from_user.id
    if not is_admin(uid):
        return

    cid = message.chat.id

    admin_states[cid] = "admin_add_title"
    admin_data[cid] = {}

    bot.send_message(cid, texts["ASK_PROPERTY_TITLE"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_title")
def get_title(message):

    cid = message.chat.id

    admin_data[cid]["title"] = message.text
    admin_states[cid] = "admin_add_price"

    bot.send_message(cid, texts["ASK_PROPERTY_PRICE"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_price")
def admin_get_price(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_PRICE"])
        return

    admin_data[cid]["price"] = int(message.text)

    admin_states[cid] = "admin_add_type"

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(texts["TYPE_BUY"]), KeyboardButton(texts["TYPE_RENT"]))

    bot.send_message(cid, texts["ASK_PROPERTY_TYPE"], reply_markup=kb)

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_type")
def get_type(message):

    cid = message.chat.id

    if message.text == texts["TYPE_BUY"]:
        admin_data[cid]["type"] = "buy"
    elif message.text == texts["TYPE_RENT"]:
        admin_data[cid]["type"] = "rent"
    else:
        bot.send_message(cid, texts["INVALID_TYPE"])
        return

    admin_states[cid] = "admin_add_desc"
    bot.send_message(cid, texts["ASK_PROPERTY_DESC"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_desc")
def get_desc(message):

    cid = message.chat.id

    admin_data[cid]["description"] = message.text

    admin_states[cid] = "admin_add_metraj"
    bot.send_message(cid, texts["ASK_PROPERTY_METRAJ"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_metraj")
def get_metraj(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_METRAJ"])
        return

    admin_data[cid]["metraj"] = int(message.text)

    admin_states[cid] = "admin_add_rooms"
    bot.send_message(cid, texts["ASK_PROPERTY_ROOMS"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_add_rooms")
def get_rooms(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_ROOMS"])
        return

    admin_data[cid]["rooms"] = int(message.text)

    admin_states[cid] = "admin_add_photo"
    bot.send_message(cid, texts["ASK_PROPERTY_PHOTO"])



@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_property(call):

    if not is_admin(call.from_user.id):
        return

    pid = call.data.split("_")[1]

    delete_property_db(pid)

    bot.answer_callback_query(call.id, texts["PROPERTY_DELETED"])

    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("disable_"))
def disable_property(call):

    pid = call.data.split("_")[1]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE properties SET status='disabled' WHERE id=%s",
        (pid,)
    )

    conn.commit()

    cur.close()
    conn.close()

    bot.answer_callback_query(call.id, texts["PROPERTY_DISABLED"])

@bot.callback_query_handler(func=lambda call: call.data.startswith("sold_"))
def sold_property(call):

    pid = call.data.split("_")[1]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE properties SET status='sold' WHERE id=%s",
        (pid,)
    )

    conn.commit()

    cur.close()
    conn.close()

    bot.answer_callback_query(call.id, texts["PROPERTY_SOLD"])

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_property(call):

    pid = call.data.split("_")[1]

    admin_states[call.message.chat.id] = "admin_edit_title"
    admin_data[call.message.chat.id] = {"id": pid}

    bot.send_message(
        call.message.chat.id,
        texts["ASK_EDIT_TITLE"]
    )

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_edit_title")
def edit_title(message):

    cid = message.chat.id

    admin_data[cid]["title"] = message.text

    admin_states[cid] = "admin_edit_price"

    bot.send_message(cid, texts["ASK_EDIT_PRICE"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_edit_price")
def edit_price(message):

    cid = message.chat.id

    if not message.text.isdigit():
        bot.send_message(cid, texts["INVALID_PRICE"])
        return

    admin_data[cid]["price"] = int(message.text)

    admin_states[cid] = "admin_edit_desc"

    bot.send_message(cid, texts["ASK_EDIT_DESC"])

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_edit_desc")
def edit_desc(message):

    cid = message.chat.id

    data = admin_data[cid]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE properties
        SET title=%s, price=%s, description=%s
        WHERE id=%s
    """, (
        data["title"],
        data["price"],
        message.text,
        data["id"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    bot.send_message(cid, texts["PROPERTY_UPDATED"])

    admin_states[cid] = "admin_none"


@bot.message_handler(content_types=['photo'])
def get_photo(message):

    cid = message.chat.id

    if admin_states.get(cid) != "admin_add_photo":
        return

    photo_id = message.photo[-1].file_id

    data = admin_data[cid]

    save_property(
        title=data["title"],
        price=data["price"],
        type=data["type"],
        description=data["description"],
        metraj=data["metraj"],
        rooms=data["rooms"],
        photo=photo_id
    )

    bot.send_message(cid, texts["PROPERTY_ADDED"], reply_markup=admin_main_menu())

    admin_states[cid] = "admin_none"
    admin_data.pop(cid)

@bot.message_handler(func=lambda m: m.text == texts["ADMIN_MANAGE_PROPERTIES"])
def admin_manage_properties(message):

    if not is_admin(message.from_user.id):
        return

    send_properties_page(message.chat.id, page=1)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def change_page(call):

    page = int(call.data.split("_")[1])

    total = count_properties()
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if page < 1 or page > total_pages:
        return

    offset = (page - 1) * ITEMS_PER_PAGE
    properties = get_properties_paginated(
        ITEMS_PER_PAGE,
        offset
    )

    text = texts["PROPERTIES_LIST_HEADER"] + "\n\n"

    for p in properties:
        text += f"""
🆔 {p['id']}
🏠 {p['title']}
💰 {p['price']}
📐 {p['metraj']} متر
🛏 {p['rooms']} خواب
📊 {p['status']}
--------------------
"""

    kb = InlineKeyboardMarkup()

    if page > 1:
        kb.add(
            InlineKeyboardButton(
                "⬅ قبلی",
                callback_data=f"upage_{page-1}"
            )
        )

    if page < total_pages:
        kb.add(
            InlineKeyboardButton(
                "بعدی ➡",
                callback_data=f"upage_{page+1}"
            )
        )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == texts["ADMIN_VISIT_REQUESTS"])
def admin_visit_requests(message):

    if not is_admin(message.from_user.id):
        return

    send_visit_page(message.chat.id, page=1)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vpage_"))
def change_visit_page(call):

    page = int(call.data.split("_")[1])

    bot.delete_message(call.message.chat.id, call.message.message_id)

    send_visit_page(call.message.chat.id, page)

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("vapprove_", "vreject_", "vcontact_")))
def update_visit(call):

    parts = call.data.split("_")
    action = parts[0]
    visit_id = parts[1]
    page = int(parts[2])

    if action == "vapprove":
        status = "approved"
    elif action == "vreject":
        status = "rejected"
    else:
        status = "contacted"

    update_visit_status(visit_id, status)

    bot.answer_callback_query(call.id, texts["VISIT_UPDATED"])

    bot.delete_message(call.message.chat.id, call.message.message_id)

    send_visit_page(call.message.chat.id, page)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vdelete_"))
def delete_visit(call):

    parts = call.data.split("_")
    visit_id = parts[1]
    page = int(parts[2])

    delete_visit_request(visit_id)

    bot.answer_callback_query(call.id, texts["VISIT_DELETED"])

    bot.delete_message(call.message.chat.id, call.message.message_id)

    send_visit_page(call.message.chat.id, page)

@bot.message_handler(func=lambda m: m.text == texts["BROADCAST"])
def admin_broadcast(message):

    if not is_admin(message.from_user.id):
        return

    admin_states[message.chat.id] = "admin_broadcast"

    bot.send_message(
        message.chat.id,
        texts["ASK_BROADCAST"]
    )

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id) == "admin_broadcast", content_types=['text','photo'])
def send_broadcast(message):

    users = get_all_users()

    success = 0
    failed = 0

    bot.send_message(
        message.chat.id,
        texts["BROADCAST_STARTED"]
    )

    for user_id in users:

        try:

            if message.content_type == "text":

                bot.send_message(
                    user_id,
                    message.text
                )

            elif message.content_type == "photo":

                bot.send_photo(
                    user_id,
                    message.photo[-1].file_id,
                    caption=message.caption
                )

            success += 1

        except:
            failed += 1

    bot.send_message(
        message.chat.id,
        texts["BROADCAST_DONE"]
    )

    bot.send_message(
        message.chat.id,
        texts["BROADCAST_STATS"].format(
            success=success,
            failed=failed
        )
    )

    admin_states[message.chat.id] = "admin_none"

# ---------------- RUN BOT ----------------
print("robot is runing")
bot.infinity_polling()