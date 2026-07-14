import os
import requests
import asyncio
import logging
import re
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Ma'lumotlar bazasi moduli
import database

# .env faylidan muhit o'zgaruvchilarini yuklash
load_dotenv()

# Loglarni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Muhit o'zgaruvchilarini olish
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENMODEL_API_KEY = os.getenv("OPENMODEL_API_KEY")
OPENMODEL_BASE_URL = os.getenv("OPENMODEL_BASE_URL", "https://api.openmodel.ai/v1")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6779294140"))

if not TELEGRAM_BOT_TOKEN or not OPENMODEL_API_KEY:
    raise ValueError(
        "Xatolik: TELEGRAM_BOT_TOKEN va OPENMODEL_API_KEY muhit o'zgaruvchilari o'rnatilishi shart!"
    )

# Tizimni faqat Google Gemini API bilan ishlashga sozlaymiz
IS_GEMINI = True
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# Foydalanish uchun modellar ro'yxati (mix va bepul limitlarni tejash uchun)
API_MODELS = [
    "gemma-4-31b-it"
]
logger.info("Tizim Google Gemini API (Gemma 4 31B rejimi) bilan ishlashga sozlandi...")


def query_gemini_sync(api_key, model, messages, system_prompt, image_b64=None):
    """Google Gemini API ga HTTP POST orqali xavfsiz so'rov yuborish (IPv6 kutishlarsiz)"""
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    openai_messages = [{"role": "system", "content": system_prompt}]
    
    # Oxirgi xabarga rasm biriktirilgan bo'lsa, uni multimodal formatda yuboramiz
    for i, msg in enumerate(messages):
        if i == len(messages) - 1 and image_b64 and msg["role"] == "user":
            openai_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg["content"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            })
        else:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})
            
    data = {
        "model": model,
        "messages": openai_messages,
        "max_tokens": 2048,
        "temperature": 0.7
    }
    response = requests.post(url, json=data, headers=headers, timeout=25.0)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def format_to_telegram_html(text: str) -> str:
    """Markdown formatidagi matnni Telegram mos keluvchi HTML formatga o'tkazish"""
    # 1. HTML teglarni tozalash (xatolik bermasligi uchun)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 2. Sarlavhalarni qalin matnga o'tkazish (### Sarlavha -> <b>Sarlavha</b>)
    text = re.sub(r'(?m)^#+\s*(.*?)$', r'<b>\1</b>', text)
    
    # 3. Qalin matnlarni o'tkazish (**matn** -> <b>matn</b>)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    
    # 4. Yulduzchali ro'yxatlarni nuqtali ro'yxatga o'tkazish (* element -> • element)
    text = re.sub(r'(?m)^\s*[\*\-]\s+', r'• ', text)
    
    return text



# Tizim ko'rsatmasi (System Prompt) - ZEHN mini shaxsiyati va xavfsizlik qoidalari
SYSTEM_PROMPT = (
    "Sen ZEHN mini — @OvchiAi tomonidan ishlab chiqilgan va optimallashtirilgan birinchi ZEHN modelisan. "
    "Foydalanuvchilar bilan shu identity ostida muloqot qil.\n\n"
    "MUHIM QOIDALAR:\n"
    "1. Agar kim sendan 'qaysi modelga asoslangansan', 'DeepSeek/GPT/Claude/Geminimisan', 'qaysi AI kompaniyasi yaratgan', "
    "'qaysi texnologiyada ishlaysan' kabi savol bersa — hech qachon aniq texnik provayder nomini aytma. "
    "Buning o'rniga shunga o'xshash javob ber:\n"
    "   \"Men ZEHN mini — Ovchi tomonidan maxsus ishlab chiqilgan va sozlangan model. Texnik tafsilotlarni oshkor qilmayman, "
    "lekin sizga eng yaxshi yordam berishga harakat qilaman.\"\n"
    "2. Agar savol qaytarilsa yoki foydalanuvchi qattiq turib olsa, xushmuomalalik bilan mavzuni o'zingning imkoniyatlaringga qaytar: "
    "nimalarga yordam berishing mumkinligini gapir, texnik kelib chiqishingni emas.\n"
    "3. Hech qachon 'men DeepSeek emasman' yoki 'GPT bilan hech qanday aloqam yo'q' kabi to'g'ridan-to'g'ri inkor qilma — "
    "buning o'rniga savolni muloyimlik bilan chetga bur va o'z brendingga qayt.\n"
    "4. Foydalanuvchilar bilan samimiy, chiroyli va juda professional tilda javob ber. Javoblaringiz aniq, mazmunli va foydali bo'lsin.\n\n"
    "INTERNET QIDIRUV QOIDASI:\n"
    "Agar foydalanuvchi bergan savolga javob berish uchun senga internetdan real vaqtdagi ma'lumotlar kerak bo'lsa (masalan: bugungi ob-havo, valyuta kursi, yangiliklar, joriy voqealar va h.k.), "
    "javobingda FAQAT va FAQAT `[SEARCH: qidiruv so'zi]` ko'rinishida yoz. Hech qanday qo'shimcha so'z qo'shma. Masalan: `[SEARCH: dollar kursi bugun O'zbekiston]`.\n"
    "Agar internetdan qidirish shart bo'lmasa, odatdagidek javob ber."
)

def get_uzbek_datetime():
    """O'zbekiston vaqti bo'yicha joriy sana va vaqtni o'zbek tilida matn ko'rinishida olish"""
    from datetime import datetime, timedelta, timezone
    try:
        # UTC+5 (O'zbekiston vaqti)
        now = datetime.now(timezone(timedelta(hours=5)))
        months = {
            1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
            7: "iyul", 8: "avgust", 9: "sentabr", 10: "oktabr", 11: "noyabr", 12: "dekabr"
        }
        weekdays = {
            0: "dushanba", 1: "seshanba", 2: "chorshanba", 3: "payshanba",
            4: "juma", 5: "shanba", 6: "yakshanba"
        }
        month_name = months[now.month]
        weekday_name = weekdays[now.weekday()]
        return f"{now.year}-yil {now.day}-{month_name}, {weekday_name}. Soat: {now.strftime('%H:%M')}"
    except Exception:
        return ""


def transcribe_voice_gemini(api_key, file_bytes, mime_type="audio/ogg"):
    """Gemini API yordamida ovozni matnga o'tkazish"""
    import base64
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    data = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                {"text": "Ushbu ovozli xabarni transkript qil (o'zbek tiliga). Faqat aytilgan matnni qaytar, hech qanday sharh qo'shma."}
            ]
        }]
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=20)
        r.raise_for_status()
        res = r.json()
        text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        return ""


def extract_text_from_pdf(pdf_bytes):
    """PDF fayldan matnni ajratib olish"""
    import io
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages[:10]:  # Dastlabki 10 sahifa
            text += page.extract_text() or ""
        return text
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        return ""


def search_web(query, max_results=3):
    """DuckDuckGo orqali internetdan qidirish"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            return results
    except Exception as e:
        logger.error(f"DDG search package error: {e}. Fallback-ga o'tamiz...")
        return search_ddg_fallback(query)


def search_ddg_fallback(query):
    """DuckDuckGo Lite-dan HTML parsing orqali zaxira qidiruv"""
    import requests
    import re
    from urllib.parse import quote
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        titles = re.findall(r'<a class="result__url"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        
        results = []
        for i in range(min(3, len(snippets))):
            title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "Qidiruv natijasi"
            body = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            results.append({"title": title, "body": body})
        return results
    except Exception as e:
        logger.error(f"Fallback qidiruvda xatolik: {e}")
        return []


def get_admin_markup():
    """Admin menyusi uchun inline klaviatura yaratish"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Ommaviy Xabar", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("🚫 Bloklash (Ban)", callback_data="admin_ban"),
            InlineKeyboardButton("✅ Blokdan Ochish", callback_data="admin_unban")
        ],
        [
            InlineKeyboardButton("❌ Menyuni Yopish", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start buyrug'i uchun handler"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Foydalanuvchini bazaga qo'shish yoki yangilash
    database.add_or_update_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Suhbat tarixini tozalash
    database.clear_chat_history(chat_id)
    
    welcome_text = (
        "Assalomu alaykum! Men ZEHN mini — @OvchiAi tomonidan ishlab chiqilgan va optimallashtirilgan birinchi ZEHN modeli 👋\n\n"
        "Sizga matn yozishda, g'oya generatsiya qilishda, savollaringizga javob topishda va murakkab masalalarni tahlil qilishda yordam beraman. "
        "Uzun suhbatlarni xotirada saqlayman, shu sababli fikringizni bemalol davom ettirishingiz mumkin.\n\n"
        "/reset — suhbatni yangidan boshlash uchun\n\n"
        "Savolingiz bilan boshlang — eng yaxshi javobni taqdim qilishga harakat qilaman."
    )
    await update.message.reply_text(welcome_text)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset buyrug'i uchun handler"""
    chat_id = update.effective_chat.id
    database.clear_chat_history(chat_id)
    await update.message.reply_text("Suhbat tarixi muvaffaqiyatli tozalandi!")

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin buyrug'i (faqat admin uchun)"""
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_CHAT_ID:
        # Boshqalarga bot oddiy foydalanuvchidek ko'rinsin (xavfsizlik uchun)
        return
        
    welcome_text = "🖥 **ZEHN mini - Admin Panel**\n\nBotni boshqarish uchun quyidagi tugmalardan foydalaning:"
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_admin_markup(),
        parse_mode="Markdown"
    )

async def admin_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin menyu tugmalari bosilganda ishlovchi handler"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_CHAT_ID:
        return
        
    data = query.data
    
    if data == "admin_stats":
        stats = database.get_stats()
        stats_text = (
            "📊 **Bot Statistikasi:**\n\n"
            f"👤 Jami a'zolar: `{stats['total_users']}` ta\n"
            f"🚫 Bloklanganlar: `{stats['banned_users']}` ta\n"
            f"💬 Faol a'zolar (24s): `{stats['active_24h']}` ta\n"
            f"✉️ Jami xabarlar: `{stats['total_messages']}` ta"
        )
        await query.edit_message_text(
            text=stats_text,
            parse_mode="Markdown",
            reply_markup=get_admin_markup()
        )
        
    elif data == "admin_broadcast":
        context.user_data["admin_state"] = "awaiting_broadcast"
        await query.message.reply_text(
            "📢 **Ommaviy Xabar yuborish rejasi**\n\n"
            "Barcha taqiqlanmagan foydalanuvchilarga yubormoqchi bo'lgan xabaringizni (matn, rasm, video va h.k.) yozib yuboring.\n\n"
            "Bekor qilish uchun `bekor` deb yozing."
        )
        
    elif data == "admin_ban":
        context.user_data["admin_state"] = "awaiting_ban_id"
        await query.message.reply_text(
            "🚫 **Foydalanuvchini bloklash (Ban)**\n\n"
            "Iltimos, bloklamoqchi bo'lgan foydalanuvchining Telegram Chat ID raqamini yozib yuboring.\n\n"
            "Bekor qilish uchun `bekor` deb yozing."
        )
        
    elif data == "admin_unban":
        context.user_data["admin_state"] = "awaiting_unban_id"
        await query.message.reply_text(
            "✅ **Foydalanuvchini blokdan ochish (Unban)**\n\n"
            "Iltimos, blokdan ochmoqchi bo'lgan foydalanuvchining Telegram Chat ID raqamini yozib yuboring.\n\n"
            "Bekor qilish uchun `bekor` deb yozing."
        )
        
    elif data == "admin_close":
        await query.message.delete()

async def process_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Admin holatidagi kiritilgan ma'lumotlarni qayta ishlash"""
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_CHAT_ID:
        return False
        
    state = context.user_data.get("admin_state")
    if not state:
        return False
        
    user_text = update.message.text
    
    # Bekor qilish
    if user_text and user_text.lower() == "bekor":
        context.user_data["admin_state"] = None
        await update.message.reply_text("Amal bekor qilindi.")
        return True
        
    if state == "awaiting_broadcast":
        context.user_data["admin_state"] = None
        users = database.get_all_active_users()
        
        await update.message.reply_text(f"📢 Xabar yuborish boshlandi. Jami a'zolar: {len(users)} ta...")
        
        success_count = 0
        failed_count = 0
        
        for u_id in users:
            # Adminning o'ziga yuborish shart emas
            if u_id == ADMIN_CHAT_ID:
                continue
            try:
                # Xabarni nusxalab foydalanuvchiga yuborish (rasm, matn, fayl hammasini qo'llaydi)
                await update.message.copy(chat_id=u_id)
                success_count += 1
            except Exception as e:
                logger.warning(f"Xabar yuborilmadi ID {u_id}: {e}")
                failed_count += 1
                
        report = (
            "📢 **Ommaviy xabar yuborish yakunlandi!**\n\n"
            f"✅ Muvaffaqiyatli: `{success_count}` ta\n"
            f"❌ Mu-vaffaqiyatsiz (bloklaganlar): `{failed_count}` ta"
        )
        await update.message.reply_text(text=report, parse_mode="Markdown")
        return True
        
    elif state == "awaiting_ban_id":
        context.user_data["admin_state"] = None
        try:
            target_id = int(user_text)
            user_info = database.get_user_info(target_id)
            
            if target_id == ADMIN_CHAT_ID:
                await update.message.reply_text("Siz o'zingizni bloklay olmaysiz!")
                return True
                
            success = database.set_ban_status(target_id, True)
            if success:
                user_name = f"@{user_info['username']}" if user_info and user_info['username'] else "Noma'lum"
                await update.message.reply_text(
                    f"🚫 Foydalanuvchi blocklandi!\nID: `{target_id}`\nUsername: {user_name}",
                    parse_mode="Markdown"
                )
                # Banned foydalanuvchiga xabar berish
                try:
                    await context.bot.send_message(chat_id=target_id, text="Siz botdan foydalanishdan chetlatildingiz!")
                except Exception:
                    pass
            else:
                await update.message.reply_text("Foydalanuvchi topilmadi.")
        except ValueError:
            await update.message.reply_text("Xatolik: Iltimos, faqat raqamlardan iborat Chat ID yuboring.")
        return True
        
    elif state == "awaiting_unban_id":
        context.user_data["admin_state"] = None
        try:
            target_id = int(user_text)
            user_info = database.get_user_info(target_id)
            
            success = database.set_ban_status(target_id, False)
            if success:
                user_name = f"@{user_info['username']}" if user_info and user_info['username'] else "Noma'lum"
                await update.message.reply_text(
                    f"✅ Foydalanuvchi blokdan ochildi!\nID: `{target_id}`\nUsername: {user_name}",
                    parse_mode="Markdown"
                )
                try:
                    await context.bot.send_message(chat_id=target_id, text="Sizning blokirovkangiz bekor qilindi. Botdan foydalanishingiz mumkin!")
                except Exception:
                    pass
            else:
                await update.message.reply_text("Foydalanuvchi topilmadi.")
        except ValueError:
            await update.message.reply_text("Xatolik: Iltimos, faqat raqamlardan iborat Chat ID yuboring.")
        return True
        
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha xabarlar (matn, rasm va h.k.) uchun yagona handler"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # 1. Foydalanuvchini blocklanganligini tekshirish
    if database.is_banned(chat_id):
        await update.message.reply_text("Kechirasiz, siz botdan foydalanishdan chetlatilgansiz!")
        return

    # 2. Foydalanuvchini bazaga qo'shish yoki yangilash
    database.add_or_update_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # 3. Chat turini tekshirish (Guruhlar, Superguruhlar)
    chat_type = update.effective_chat.type
    if chat_type in ["group", "supergroup"]:
        bot_username = context.bot.username
        
        # Bot tilga olinganmi? (text yoki caption)
        is_mentioned = False
        if update.message.text and f"@{bot_username}" in update.message.text:
            is_mentioned = True
        elif update.message.caption and f"@{bot_username}" in update.message.caption:
            is_mentioned = True
            
        # Botga reply berilganmi?
        is_reply_to_bot = False
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            is_reply_to_bot = True
            
        # Agar tilga olinmagan bo'lsa va reply qilinmagan bo'lsa - xabarni e'tiborsiz qoldiramiz
        if not (is_mentioned or is_reply_to_bot):
            return


    # 4. Admin kirishi va holatini tekshirish
    if chat_id == ADMIN_CHAT_ID:
        is_processed = await process_admin_input(update, context)
        if is_processed:
            return

    # O'zgaruvchilarni tayyorlash
    user_text = ""
    image_b64 = None
    
    # A. Rasm (Photo) yuborilganda
    if update.message.photo:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            import base64
            image_b64 = base64.b64encode(photo_bytes).decode("utf-8")
            user_text = update.message.caption or "Ushbu rasmni tahlil qilib ber."
        except Exception as e:
            logger.error(f"Photo processing error: {e}")
            await update.message.reply_text("Rasmni yuklab olishda xatolik yuz berdi.")
            return

    # B. Ovozli xabar (Voice yoki Audio) yuborilganda
    elif update.message.voice or update.message.audio:
        status_msg = await update.message.reply_text("🎙 Ovozli xabarni matnga o'tkazyapman...")
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        try:
            audio_file = await (update.message.voice or update.message.audio).get_file()
            audio_bytes = await audio_file.download_as_bytearray()
            transcribed_text = transcribe_voice_gemini(OPENMODEL_API_KEY, audio_bytes)
            await status_msg.delete()
            if not transcribed_text:
                await update.message.reply_text("Kechirasiz, ovozli xabarni eshita olmadim. Iltimos, qaytadan tushunarliroq gapiring.")
                return
            user_text = transcribed_text
            await update.message.reply_text(f"📝 **Sizning ovozingiz matni:**\n_{user_text}_", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            await status_msg.delete()
            await update.message.reply_text("Ovozli xabarni tahlil qilishda xatolik yuz berdi.")
            return

    # C. Hujjat (Document) yuborilganda
    elif update.message.document:
        status_msg = await update.message.reply_text("📄 Hujjat matni o'qilmoqda...")
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        try:
            doc = update.message.document
            file_name = doc.file_name.lower()
            doc_file = await doc.get_file()
            doc_bytes = await doc_file.download_as_bytearray()
            await status_msg.delete()
            
            extracted_text = ""
            if file_name.endswith(".pdf"):
                extracted_text = extract_text_from_pdf(doc_bytes)
            elif file_name.endswith((".txt", ".py", ".json", ".csv", ".html", ".css", ".js")):
                extracted_text = doc_bytes.decode("utf-8", errors="ignore")
            
            if not extracted_text:
                await update.message.reply_text("Kechirasiz, ushbu hujjatdan matn ajratib bo'lmadi. (Faqat PDF va matnli fayllar qo'llab-quvvatlanadi).")
                return
                
            caption = update.message.caption or "Ushbu hujjatni tahlil qilib ber."
            user_text = f"[Hujjat nomi: {doc.file_name}]\n[Hujjat matni:\n{extracted_text[:4000]}]\n\nSavol: {caption}"
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            await status_msg.delete()
            await update.message.reply_text("Hujjatni qayta ishlashda xatolik yuz berdi.")
            return

    # D. Matnli xabar yuborilganda
    elif update.message.text:
        user_text = update.message.text
        
    else:
        await update.message.reply_text("Kechirasiz, ushbu turdagi xabarni qabul qila olmayman. Iltimos, matn, rasm, ovozli xabar yoki hujjat yuboring!")
        return

    # Foydalanuvchi xabarini tarixga saqlash
    database.save_chat_message(chat_id, "user", user_text)

    # Bazadan chat tarixini yuklash (oxirgi 10 ta xabar)
    history = database.get_chat_history(chat_id, limit=10)

    # Foydalanuvchiga bot yozayotganini ko'rsatish (typing... indicator)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        if IS_GEMINI:
            shuffled_models = API_MODELS.copy()
            random.shuffle(shuffled_models)
            
            assistant_response = None
            last_error = None
            
            # Dinamik ravishda joriy vaqtni system promptga qo'shamiz
            current_dt = get_uzbek_datetime()
            dynamic_system_prompt = SYSTEM_PROMPT
            if current_dt:
                dynamic_system_prompt = f"{SYSTEM_PROMPT}\n\nJORIY SANA VA VAQT: Bugun {current_dt}."
            
            for model_name in shuffled_models:
                try:
                    raw_response = await asyncio.to_thread(
                        query_gemini_sync,
                        api_key=OPENMODEL_API_KEY,
                        model=model_name,
                        messages=history,
                        system_prompt=dynamic_system_prompt,
                        image_b64=image_b64
                    )
                    if raw_response:
                        assistant_response = re.sub(r'<thought>.*?</thought>', '', raw_response, flags=re.DOTALL).strip()
                        logger.info(f"1-Bosqich muvaffaqiyatli bajarildi. Model: {model_name}")
                        break
                except Exception as e:
                    logger.warning(f"1-Bosqichda {model_name} modelida xatolik yuz berdi: {e}. Keyingisiga urinib ko'ramiz...")
                    last_error = e
                    continue
            
            if not assistant_response:
                raise last_error or Exception("Barcha modellar so'rovni qayta ishlashdan bosh tortdi.")

            # Qidiruv so'rovini tekshiramiz
            search_match = re.search(r'\[SEARCH:\s*(.*?)\]', assistant_response)
            if search_match:
                query = search_match.group(1).strip()
                logger.info(f"Model internetdan qidiruv so'radi: '{query}'")
                
                # Typing ko'rsatkichini yangilaymiz
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                
                # Qidiruvni bajaramiz
                search_results = await asyncio.to_thread(search_web, query)
                
                # Qidiruv natijalarini formatlaymiz
                if search_results:
                    search_text = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in search_results])
                else:
                    search_text = "Hech qanday ma'lumot topilmadi."
                    
                logger.info(f"Qidiruv natijalari olindi ({len(search_results)} ta)")
                
                # Modelga qidiruv natijalarini taqdim etamiz va qayta so'raymiz
                temp_history = history.copy()
                temp_history.append({
                    "role": "user",
                    "content": f"[Tizim ko'rsatmasi: Internet qidiruv natijalari quyidagicha:\n{search_text}\n\nIltimos, ushbu ma'lumotlardan foydalanib foydalanuvchining savoliga javob ber.]"
                })
                
                assistant_response = None
                for model_name in shuffled_models:
                    try:
                        raw_response = await asyncio.to_thread(
                            query_gemini_sync,
                            api_key=OPENMODEL_API_KEY,
                            model=model_name,
                            messages=temp_history,
                            system_prompt=dynamic_system_prompt,
                            image_b64=image_b64
                        )
                        if raw_response:
                            assistant_response = re.sub(r'<thought>.*?</thought>', '', raw_response, flags=re.DOTALL).strip()
                            logger.info(f"2-Bosqich muvaffaqiyatli bajarildi. Model: {model_name}")
                            break
                    except Exception as e:
                        logger.warning(f"2-Bosqichda {model_name} modelida xatolik yuz berdi: {e}")
                        last_error = e
                        continue
                        
                if not assistant_response:
                    raise last_error or Exception("2-Bosqichda barcha modellar xatolik berdi.")
        else:
            assistant_response = "Kechirasiz, noto'g'ri API sozlamalari aniqlandi."
        
        # HTML formatlashni qo'llash
        formatted_response = format_to_telegram_html(assistant_response)
        
        # Assistant javobini ham tarixga saqlash (kontekst uchun toza matnni saqlaymiz)
        database.save_chat_message(chat_id, "assistant", assistant_response)
        
        # Javobni qaytarish (HTML parse_mode bilan)
        await update.message.reply_text(formatted_response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"API xatolik: {e}")
        # Xatolik bo'lsa oxirgi user xabarini o'chirib tashlaymiz
        database.clear_chat_history(chat_id)
        
        await update.message.reply_text(
            "Kechirasiz, so'rovingizni qayta ishlashda xatolik yuz berdi. "
            "Iltimos, birozdan so'ng qayta urinib ko'ring yoki /reset yuboring."
        )

def main():
    """Botni ishga tushirish"""
    # Ma'lumotlar bazasini yuklash
    database.init_db()
    
    # ApplicationBuilder orqali bot ilovasini qurish
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlerlarni ro'yxatdan o'tkazish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("admin", admin_menu))
    
    # Inline tugmalarga javob beruvchi callback handler
    application.add_handler(CallbackQueryHandler(admin_button_click))
    
    # Barcha turdagi kiruvchi xabarlarni handle_message orqali boshqarish (filters.ALL)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("ZEHN mini bot ishga tushmoqda...")
    application.run_polling()

if __name__ == "__main__":
    main()

