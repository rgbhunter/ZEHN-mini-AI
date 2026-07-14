# OpenModel Telegram Bot (`deepseek-v4-flash`)

Ushbu Telegram bot OpenModel API (base_url: `https://api.openmodel.ai`) orqali `deepseek-v4-flash` modeli bilan interaktiv muloqot qiladi va suhbat tarixini eslab qoladi.

## Bosqichma-bosqich sozlash yo'riqnomasi

### 1. Telegram Bot Tokenini olish (@BotFather)
1. Telegram ilovasida rasmiy [@BotFather](https://t.me/BotFather) botini qidiring.
2. Botga `/newbot` buyrug'ini yuboring.
3. Bot uchun nom (masalan: `Mening Yordamchi Botim`) va foydalanuvchi nomini (username, masalan: `my_openmodel_helper_bot`, oxiri `bot` bilan tugashi shart) tanlang.
4. BotFather sizga **HTTP API tokenini** beradi (masalan: `8772775469:AAGZlXgSsauSX...`). Uni nusxalab oling.

### 2. Loyihani o'rnatish
Ushbu katalogni ishchi soha (workspace) sifatida oching:
`C:\Users\sayyo\.gemini\antigravity\scratch\openmodel_telegram_bot`

Tizimda Python 3.8+ o'rnatilgan bo'lishi kerak. Kerakli paketlarni o'rnating:
```bash
pip install -r requirements.txt
```

### 3. Sozlamalar (.env)
Loyihada `.env` fayli yaratilgan bo'lishi kerak (namuna `.env.example` faylida ko'rsatilgan). 
Quyidagi parametrlarni kiriting:
```env
TELEGRAM_BOT_TOKEN=Sizning_Telegram_Bot_Tokeningiz
OPENMODEL_API_KEY=Sizning_OpenModel_API_Kalitingiz
OPENMODEL_BASE_URL=https://api.openmodel.ai/v1
```

*(Hozirda foydalanuvchi bergan to'g'ri kalitlar bilan `.env` fayli loyihada tayyor holda yaratilgan).*

### 4. Ishga tushirish
Botni polling rejimida ishga tushirish uchun quyidagi buyruqni bering:
```bash
python main.py
```

### 5. Bot buyruqlari
*   `/start` - Botni boshlash va kutib olish xabari.
*   `/reset` - Suhbat tarixini tozalash va xotirani o'chirish.
*   Istalgan matn yozilsa, bot `typing...` holatini ko'rsatib, OpenModel API orqali javob qaytaradi.
