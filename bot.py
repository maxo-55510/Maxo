import os
import json
import asyncio
import logging
import traceback
import time

from rubka import Robot
from rubka.keypad import ChatKeypadBuilder


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")

DATA_FILE = "data.json"

WELCOME_TEXT = (
    "╔════════════════════════════╗\n"
    "        ✦ MAXO PANEL ✦\n"
    "╚════════════════════════════╝\n\n"
    "به ربات خوش اومدی.\n"
    "فایل موردنظرت رو از منوی زیر انتخاب کن."
)

ADMIN_TEXT = (
    "╔════════════════════════════╗\n"
    "       ⚙️ MAXO PANEL\n"
    "       پنل مدیریت\n"
    "╚════════════════════════════╝\n\n"
    "یکی از گزینه‌های زیر را انتخاب کن."
)


# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("MAXO")


# =========================================================
# DATABASE
# =========================================================

DEFAULT_DATA = {
    "buttons": {},
    "users": [],
    "states": {}
}


def load_db():

    try:

        if not os.path.exists(DATA_FILE):

            save_db(DEFAULT_DATA)

            return {
                "buttons": {},
                "users": [],
                "states": {}
            }

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, dict):

            data = {
                "buttons": {},
                "users": [],
                "states": {}
            }

        data.setdefault("buttons", {})
        data.setdefault("users", [])
        data.setdefault("states", {})

        return data

    except Exception:

        log.exception("DATABASE LOAD ERROR")

        return {
            "buttons": {},
            "users": [],
            "states": {}
        }


def save_db(data):

    tmp_file = DATA_FILE + ".tmp"

    with open(
        tmp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        tmp_file,
        DATA_FILE
    )


# =========================================================
# BOT
# =========================================================

if not BOT_TOKEN:

    raise RuntimeError(
        "BOT_TOKEN is not set"
    )

if not ADMIN_ID:

    raise RuntimeError(
        "ADMIN_ID is not set"
    )


bot = Robot(
    token=BOT_TOKEN
)


# =========================================================
# BASIC HELPERS
# =========================================================

def normalize_id(value):

    if value is None:
        return None

    return str(value)


def is_admin(chat_id):

    return normalize_id(chat_id) == normalize_id(
        ADMIN_ID
    )


def add_user(chat_id):

    chat_id = normalize_id(chat_id)

    db = load_db()

    if chat_id not in db["users"]:

        db["users"].append(chat_id)

        save_db(db)


def set_state(
    chat_id,
    name,
    data=None
):

    db = load_db()

    db["states"][
        normalize_id(chat_id)
    ] = {
        "name": name,
        "data": data or {}
    }

    save_db(db)


def get_state(chat_id):

    db = load_db()

    return db["states"].get(
        normalize_id(chat_id)
    )


def clear_state(chat_id):

    db = load_db()

    db["states"].pop(
        normalize_id(chat_id),
        None
    )

    save_db(db)


# =========================================================
# KEYBOARD
# =========================================================

def make_keyboard(rows):

    builder = ChatKeypadBuilder()

    for row in rows:

        buttons = []

        for button_id, text in row:

            buttons.append(
                ChatKeypadBuilder().button(
                    id=str(button_id),
                    text=str(text)
                )
            )

        if buttons:

            builder.row(
                *buttons
            )

    return builder.build()


# =========================================================
# USER KEYBOARD
# =========================================================

def user_keyboard(chat_id):

    db = load_db()

    rows = []
    current_row = []

    for button_id, item in db["buttons"].items():

        title = item.get(
            "title",
            "فایل"
        )

        current_row.append(
            (
                "file_" + str(button_id),
                title
            )
        )

        if len(current_row) >= 2:

            rows.append(
                current_row
            )

            current_row = []

    if current_row:

        rows.append(
            current_row
        )

    if not rows:

        rows.append([
            (
                "empty",
                "📂 هنوز فایلی اضافه نشده"
            )
        ])

    if is_admin(chat_id):

        rows.append([
            (
                "admin",
                "⚙️ مدیریت"
            )
        ])

    return make_keyboard(rows)


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():

    return make_keyboard([

        [
            (
                "add",
                "➕ افزودن فایل"
            ),
            (
                "edit",
                "✏️ ویرایش فایل"
            )
        ],

        [
            (
                "list",
                "📋 لیست فایل‌ها"
            ),
            (
                "delete",
                "🗑 حذف فایل"
            )
        ],

        [
            (
                "users",
                "👥 کاربران"
            )
        ],

        [
            (
                "back",
                "↩️ بازگشت"
            )
        ]

    ])


# =========================================================
# MESSAGE HELPERS
# =========================================================

def get_chat_id(message):

    value = getattr(
        message,
        "chat_id",
        None
    )

    if value is not None:
        return normalize_id(value)

    raw = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw, dict):

        for key in (
            "chat_id",
            "chatId"
        ):

            if raw.get(key) is not None:

                return normalize_id(
                    raw.get(key)
                )

    return None


def get_message_id(message):

    value = getattr(
        message,
        "message_id",
        None
    )

    if value is not None:
        return normalize_id(value)

    value = getattr(
        message,
        "id",
        None
    )

    if value is not None:
        return normalize_id(value)

    raw = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw, dict):

        for key in (
            "message_id",
            "messageId",
            "id"
        ):

            if raw.get(key) is not None:

                return normalize_id(
                    raw.get(key)
                )

    return None


def get_text(message):

    value = getattr(
        message,
        "text",
        None
    )

    if value is not None:
        return str(value)

    raw = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw, dict):

        for key in (
            "text",
            "caption"
        ):

            if isinstance(
                raw.get(key),
                str
            ):

                return raw.get(key)

    return None


# =========================================================
# RAW MESSAGE
# =========================================================

def get_raw(message):

    raw = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw, dict):
        return raw

    return {}


def looks_like_file(message):

    raw = get_raw(message)

    if raw:

        raw_string = json.dumps(
            raw,
            ensure_ascii=False
        ).lower()

        keys = (
            "file_id",
            "fileid",
            "document",
            "file",
            "attachment",
            "media"
        )

        for key in keys:

            if key in raw_string:
                return True

    for attr in (
        "file",
        "document",
        "file_id",
        "media"
    ):

        if getattr(
            message,
            attr,
            None
        ) is not None:

            return True

    return False


# =========================================================
# ERROR REPORT
# =========================================================

async def report_error(error):

    text = (
        "❌ MAXO PANEL ERROR\n\n"
        f"{type(error).__name__}: {error}\n\n"
        f"{traceback.format_exc()}"
    )

    log.error(text)

    try:

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text[-7000:]
        )

    except Exception:

        log.exception(
            "ERROR REPORT FAILED"
        )


# =========================================================
# HOME
# =========================================================

async def show_home(chat_id):

    await bot.send_message(
        chat_id=chat_id,
        text=WELCOME_TEXT,
        chat_keypad=user_keyboard(chat_id),
        chat_keypad_type="New"
    )


async def show_admin(chat_id):

    await bot.send_message(
        chat_id=chat_id,
        text=ADMIN_TEXT,
        chat_keypad=admin_keyboard(),
        chat_keypad_type="New"
    )


# =========================================================
# END PART 1
# =========================================================
# =========================================================
# PART 2/3
# =========================================================

# =========================================================
# SAVE FORWARDED MESSAGE
# =========================================================

async def save_forwarded_message(
    chat_id,
    message
):
    """
    پیام اصلی را ذخیره می‌کند.
    فایل دانلود یا آپلود نمی‌شود.
    فقط chat_id و message_id ذخیره می‌شوند.
    """

    try:

        message_id = get_message_id(message)

        if not message_id:

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ نتونستم شناسه پیام رو پیدا کنم.\n\n"
                    "فایل رو دوباره به ربات Forward کن."
                )
            )

            return

        source_chat_id = get_chat_id(message)

        if not source_chat_id:

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ شناسه چت پیام پیدا نشد.\n\n"
                    "پیام رو دوباره Forward کن."
                )
            )

            return

        state = get_state(chat_id)

        if not state:

            return

        if state["name"] != "waiting_file":

            return

        title = state["data"].get(
            "title",
            "فایل"
        )

        button_id = str(
            int(time.time() * 1000)
        )

        db = load_db()

        db["buttons"][button_id] = {

            "title": title,

            # منبع اصلی پیام
            "source_chat_id": str(
                source_chat_id
            ),

            # ID همان پیام Forward شده
            "message_id": str(
                message_id
            ),

            # نوع ذخیره‌سازی
            "type": "forward"

        }

        save_db(db)

        clear_state(chat_id)

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "╔════════════════════════════╗\n"
                "        ✅ فایل اضافه شد\n"
                "╚════════════════════════════╝\n\n"
                f"📌 نام دکمه: {title}\n\n"
                "پیام اصلی ذخیره شد.\n"
                "از این به بعد ربات همان پیام را "
                "Forward می‌کند.\n\n"
                "بنابراین کپشن و قالب‌بندی خود "
                "پیام هم حفظ می‌شود."
            ),
            chat_keypad=admin_keyboard(),
            chat_keypad_type="New"
        )

    except Exception as e:

        await report_error(e)

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ ذخیره فایل انجام نشد.\n"
                "خطا برای ادمین ارسال شد."
            )
        )


# =========================================================
# FORWARD FILE TO USER
# =========================================================

async def send_saved_file(
    chat_id,
    button_id
):

    try:

        db = load_db()

        item = db["buttons"].get(
            str(button_id)
        )

        if not item:

            await bot.send_message(
                chat_id=chat_id,
                text="❌ این فایل دیگر وجود ندارد."
            )

            return

        source_chat_id = item.get(
            "source_chat_id"
        )

        message_id = item.get(
            "message_id"
        )

        if not source_chat_id or not message_id:

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ اطلاعات پیام اصلی ناقص است.\n"
                    "این فایل را دوباره اضافه کنید."
                )
            )

            return

        # =================================================
        # مهم:
        # اینجا اصلاً send_document نداریم.
        # فایل هم دانلود نمی‌شود.
        # فقط Forward واقعی انجام می‌شود.
        # =================================================

        await bot.forward_message(
            from_chat_id=str(
                source_chat_id
            ),

            message_id=str(
                message_id
            ),

            to_chat_id=str(
                chat_id
            ),

            disable_notification=False
        )

    except Exception as e:

        await report_error(e)

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ ارسال فایل ناموفق بود.\n\n"
                "ممکن است پیام اصلی حذف شده باشد "
                "یا دیگر قابل Forward نباشد."
            )
        )


# =========================================================
# BUTTON LIST
# =========================================================

async def show_file_list(chat_id):

    try:

        db = load_db()

        if not db["buttons"]:

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "          📂 فایل‌ها\n"
                    "╚════════════════════════════╝\n\n"
                    "هنوز هیچ فایلی اضافه نشده."
                ),
                chat_keypad=admin_keyboard(),
                chat_keypad_type="New"
            )

            return

        text = (
            "╔════════════════════════════╗\n"
            "          📂 فایل‌ها\n"
            "╚════════════════════════════╝\n\n"
        )

        number = 1

        for button_id, item in db["buttons"].items():

            title = item.get(
                "title",
                "بدون نام"
            )

            text += (
                f"▫️ {number}. {title}\n"
                f"   ID: {button_id}\n\n"
            )

            number += 1

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            chat_keypad=admin_keyboard(),
            chat_keypad_type="New"
        )

    except Exception as e:

        await report_error(e)


# =========================================================
# DELETE MENU
# =========================================================

async def show_delete_menu(chat_id):

    try:

        db = load_db()

        rows = []

        for button_id, item in db["buttons"].items():

            title = item.get(
                "title",
                "بدون نام"
            )

            rows.append([
                (
                    "delete_" + str(button_id),
                    "🗑 " + title
                )
            ])

        if not rows:

            rows.append([
                (
                    "empty",
                    "📂 لیست خالی است"
                )
            ])

        rows.append([
            (
                "back",
                "↩️ بازگشت"
            )
        ])

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🗑 حذف فایل\n\n"
                "فایلی که می‌خواهی حذف شود "
                "را انتخاب کن:"
            ),
            chat_keypad=make_keyboard(rows),
            chat_keypad_type="New"
        )

    except Exception as e:

        await report_error(e)


# =========================================================
# EDIT MENU
# =========================================================

async def show_edit_menu(chat_id):

    try:

        db = load_db()

        rows = []

        for button_id, item in db["buttons"].items():

            title = item.get(
                "title",
                "بدون نام"
            )

            rows.append([
                (
                    "choose_edit_" + str(button_id),
                    "✏️ " + title
                )
            ])

        if not rows:

            rows.append([
                (
                    "empty",
                    "📂 لیست خالی است"
                )
            ])

        rows.append([
            (
                "back",
                "↩️ بازگشت"
            )
        ])

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "╔════════════════════════════╗\n"
                "          ✏️ ویرایش فایل\n"
                "╚════════════════════════════╝\n\n"
                "فایل موردنظر را انتخاب کن:"
            ),
            chat_keypad=make_keyboard(rows),
            chat_keypad_type="New"
        )

    except Exception as e:

        await report_error(e)


# =========================================================
# EDIT OPTIONS
# =========================================================

async def show_edit_options(
    chat_id,
    button_id
):

    db = load_db()

    item = db["buttons"].get(
        str(button_id)
    )

    if not item:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ فایل پیدا نشد."
        )

        return

    title = item.get(
        "title",
        "بدون نام"
    )

    await bot.send_message(

        chat_id=chat_id,

        text=(
            "╔════════════════════════════╗\n"
            "          ✏️ ویرایش\n"
            "╚════════════════════════════╝\n\n"
            f"فایل: {title}\n\n"
            "چه چیزی را می‌خواهی تغییر بدهی؟"
        ),

        chat_keypad=make_keyboard([

            [
                (
                    "rename_" + str(button_id),
                    "📝 تغییر نام دکمه"
                )
            ],

            [
                (
                    "replace_" + str(button_id),
                    "🔄 جایگزینی پیام"
                )
            ],

            [
                (
                    "back_edit",
                    "↩️ بازگشت"
                )
            ]

        ]),

        chat_keypad_type="New"
    )


# =========================================================
# CALLBACK
# =========================================================

@bot.on_callback()
async def callback(
    bot_instance,
    message
):

    try:

        chat_id = get_chat_id(
            message
        )

        if not chat_id:

            return

        add_user(chat_id)

        # -------------------------------------------------
        # callback id
        # -------------------------------------------------

        callback_id = None

        aux_data = getattr(
            message,
            "aux_data",
            None
        )

        if isinstance(
            aux_data,
            dict
        ):

            callback_id = (
                aux_data.get("button_id")
                or aux_data.get("id")
                or aux_data.get("data")
            )

        if callback_id is None:

            callback_id = getattr(
                aux_data,
                "button_id",
                None
            )

        if callback_id is None:

            callback_id = getattr(
                message,
                "button_id",
                None
            )

        if callback_id is None:

            return

        callback_id = str(
            callback_id
        )

        # =================================================
        # EMPTY
        # =================================================

        if callback_id == "empty":

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📂 هنوز هیچ فایلی اضافه نشده."
                )
            )

            return

        # =================================================
        # ADMIN
        # =================================================

        if callback_id == "admin":

            if is_admin(chat_id):

                clear_state(chat_id)

                await show_admin(
                    chat_id
                )

            return

        # =================================================
        # BACK
        # =================================================

        if callback_id == "back":

            clear_state(chat_id)

            await show_home(
                chat_id
            )

            return

        if callback_id == "back_edit":

            clear_state(chat_id)

            await show_edit_menu(
                chat_id
            )

            return

        # =================================================
        # ADD
        # =================================================

        if callback_id == "add":

            if not is_admin(chat_id):

                return

            clear_state(chat_id)

            set_state(
                chat_id,
                "waiting_title"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "          ➕ افزودن فایل\n"
                    "╚════════════════════════════╝\n\n"
                    "اول نام دکمه را بفرست.\n\n"
                    "مثال:\n"
                    "📦 فایل VIP\n"
                    "🔥 کانفیگ شماره ۱"
                )
            )

            return

        # =================================================
        # LIST
        # =================================================

        if callback_id == "list":

            if not is_admin(chat_id):

                return

            await show_file_list(
                chat_id
            )

            return

        # =================================================
        # DELETE
        # =================================================

        if callback_id == "delete":

            if not is_admin(chat_id):

                return

            await show_delete_menu(
                chat_id
            )

            return

        # =================================================
        # EDIT
        # =================================================

        if callback_id == "edit":

            if not is_admin(chat_id):

                return

            await show_edit_menu(
                chat_id
            )

            return

        # =================================================
        # DELETE ITEM
        # =================================================

        if callback_id.startswith(
            "delete_"
        ):

            if not is_admin(chat_id):

                return

            button_id = callback_id[
                len("delete_"):
            ]

            db = load_db()

            if button_id in db["buttons"]:

                title = db["buttons"][
                    button_id
                ].get(
                    "title",
                    "فایل"
                )

                del db["buttons"][
                    button_id
                ]

                save_db(db)

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ فایل حذف شد.\n\n"
                        f"📁 {title}"
                    ),
                    chat_keypad=admin_keyboard(),
                    chat_keypad_type="New"
                )

            else:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ فایل پیدا نشد."
                )

            return

        # =================================================
        # CHOOSE EDIT
        # =================================================

        if callback_id.startswith(
            "choose_edit_"
        ):

            if not is_admin(chat_id):

                return

            button_id = callback_id[
                len("choose_edit_"):
            ]

            await show_edit_options(
                chat_id,
                button_id
            )

            return

        # =================================================
        # RENAME
        # =================================================

        if callback_id.startswith(
            "rename_"
        ):

            if not is_admin(chat_id):

                return

            button_id = callback_id[
                len("rename_"):
            ]

            db = load_db()

            if button_id not in db["buttons"]:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ فایل پیدا نشد."
                )

                return

            set_state(
                chat_id,
                "rename",
                {
                    "id": button_id
                }
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📝 نام جدید دکمه را بفرست."
                )
            )

            return

        # =================================================
        # REPLACE MESSAGE
        # =================================================

        if callback_id.startswith(
            "replace_"
        ):

            if not is_admin(chat_id):

                return

            button_id = callback_id[
                len("replace_"):
            ]

            db = load_db()

            if button_id not in db["buttons"]:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ فایل پیدا نشد."
                )

                return

            set_state(
                chat_id,
                "replace",
                {
                    "id": button_id
                }
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔄 پیام جدید را Forward کن.\n\n"
                    "می‌توانی فایل را همراه با "
                    "کپشن و قالب‌بندی دلخواهت "
                    "از Saved Messages بفرستی."
                )
            )

            return

        # =================================================
        # SEND FILE
        # =================================================

        if callback_id.startswith(
            "file_"
        ):

            button_id = callback_id[
                len("file_"):
            ]

            await send_saved_file(
                chat_id,
                button_id
            )

            return

    except Exception as e:

        await report_error(e)


# =========================================================
# END PART 2
# =========================================================
# =========================================================
# PART 3/3
# =========================================================


# =========================================================
# START
# =========================================================

@bot.on_message(commands=["start"])
async def start(
    bot_instance,
    message
):

    try:

        chat_id = get_chat_id(
            message
        )

        if not chat_id:
            return

        add_user(chat_id)

        clear_state(chat_id)

        await show_home(
            chat_id
        )

    except Exception as e:

        await report_error(e)


# =========================================================
# NORMAL MESSAGES
# =========================================================

@bot.on_message()
async def messages(
    bot_instance,
    message
):

    try:

        chat_id = get_chat_id(
            message
        )

        if not chat_id:
            return

        add_user(chat_id)

        current_state = get_state(
            chat_id
        )

        if not current_state:
            return

        state_name = current_state.get(
            "name"
        )

        state_data = current_state.get(
            "data",
            {}
        )

        # =================================================
        # WAITING FOR BUTTON TITLE
        # =================================================

        if (
            state_name == "waiting_title"
            and is_admin(chat_id)
        ):

            text = get_text(
                message
            )

            if not text:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ نام معتبر نیست.\n"
                        "لطفاً یک نام برای دکمه بفرست."
                    )
                )

                return

            title = text.strip()

            if not title:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ نام نمی‌تواند خالی باشد."
                    )
                )

                return

            if len(title) > 80:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ نام خیلی طولانی است.\n"
                        "حداکثر ۸۰ کاراکتر."
                    )
                )

                return

            set_state(
                chat_id,
                "waiting_file",
                {
                    "title": title
                }
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "          📤 مرحله دوم\n"
                    "╚════════════════════════════╝\n\n"
                    f"نام دکمه:\n"
                    f"「 {title} 」\n\n"
                    "حالا پیام فایل را Forward کن.\n\n"
                    "نکته مهم:\n"
                    "فایل را می‌توانی در Saved Messages "
                    "با کپشن دلخواه، نقل‌قول، بولد و "
                    "قالب‌بندی خودت آماده کنی و همان "
                    "پیام را Forward کنی.\n\n"
                    "ربات فایل را دانلود نمی‌کند؛ "
                    "خود پیام را ذخیره می‌کند."
                )
            )

            return


        # =================================================
        # WAITING FOR FORWARDED FILE
        # =================================================

        if (
            state_name == "waiting_file"
            and is_admin(chat_id)
        ):

            message_id = get_message_id(
                message
            )

            source_chat_id = get_chat_id(
                message
            )

            if not message_id:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ این پیام شناسه معتبری ندارد.\n\n"
                        "لطفاً پیام فایل را دوباره "
                        "Forward کن."
                    )
                )

                return

            if not source_chat_id:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ منبع پیام پیدا نشد.\n\n"
                        "لطفاً فایل را دوباره Forward کن."
                    )
                )

                return

            title = state_data.get(
                "title",
                "فایل"
            )

            button_id = str(
                int(time.time() * 1000)
            )

            db = load_db()

            db["buttons"][button_id] = {

                "title": title,

                "source_chat_id": str(
                    source_chat_id
                ),

                "message_id": str(
                    message_id
                ),

                "type": "forward"

            }

            save_db(db)

            clear_state(
                chat_id
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "        ✅ فایل ثبت شد\n"
                    "╚════════════════════════════╝\n\n"
                    f"📌 دکمه:\n"
                    f"「 {title} 」\n\n"
                    "پیام اصلی ذخیره شد.\n"
                    "ربات از این به بعد همان پیام "
                    "را Forward می‌کند.\n\n"
                    "پس کپشن و قالب‌بندی پیام اصلی "
                    "دستکاری نمی‌شود."
                ),
                chat_keypad=admin_keyboard(),
                chat_keypad_type="New"
            )

            return


        # =================================================
        # RENAME
        # =================================================

        if (
            state_name == "rename"
            and is_admin(chat_id)
        ):

            text = get_text(
                message
            )

            if not text:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ نام جدید را ارسال کن."
                    )
                )

                return

            new_title = text.strip()

            button_id = state_data.get(
                "id"
            )

            db = load_db()

            if button_id not in db["buttons"]:

                clear_state(
                    chat_id
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ فایل پیدا نشد."
                )

                return

            db["buttons"][
                button_id
            ]["title"] = new_title

            save_db(db)

            clear_state(
                chat_id
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "          ✅ انجام شد\n"
                    "╚════════════════════════════╝\n\n"
                    f"نام جدید:\n"
                    f"「 {new_title} 」"
                ),
                chat_keypad=admin_keyboard(),
                chat_keypad_type="New"
            )

            return


        # =================================================
        # REPLACE FORWARDED MESSAGE
        # =================================================

        if (
            state_name == "replace"
            and is_admin(chat_id)
        ):

            message_id = get_message_id(
                message
            )

            source_chat_id = get_chat_id(
                message
            )

            button_id = state_data.get(
                "id"
            )

            if not message_id or not source_chat_id:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ پیام معتبر نیست.\n\n"
                        "پیام جدید را دوباره Forward کن."
                    )
                )

                return

            db = load_db()

            if button_id not in db["buttons"]:

                clear_state(
                    chat_id
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ فایل پیدا نشد."
                )

                return

            db["buttons"][
                button_id
            ]["source_chat_id"] = str(
                source_chat_id
            )

            db["buttons"][
                button_id
            ]["message_id"] = str(
                message_id
            )

            db["buttons"][
                button_id
            ]["type"] = "forward"

            save_db(db)

            clear_state(
                chat_id
            )

            title = db["buttons"][
                button_id
            ].get(
                "title",
                "فایل"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔════════════════════════════╗\n"
                    "        🔄 پیام جایگزین شد\n"
                    "╚════════════════════════════╝\n\n"
                    f"📌 {title}\n\n"
                    "از این به بعد پیام جدید "
                    "Forward خواهد شد."
                ),
                chat_keypad=admin_keyboard(),
                chat_keypad_type="New"
            )

            return


    except Exception as e:

        await report_error(
            e
        )

        try:

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ خطایی رخ داد.\n"
                    "جزئیات برای ادمین ارسال شد."
                )
            )

        except Exception:

            pass


# =========================================================
# RUN
# =========================================================

async def main():

    log.info(
        "╔════════════════════════════╗"
    )

    log.info(
        "       MAXO PANEL ONLINE"
    )

    log.info(
        "╚════════════════════════════╝"
    )

    await bot.run()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        log.info(
            "MAXO PANEL stopped."
        )

    except Exception as e:

        log.exception(
            "BOT CRASHED"
        )

        raise


# =========================================================
# END OF BOT.PY
# =========================================================