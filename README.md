# ربات فروش PDF + گروه VIP (لینک یک‌بارمصرف)

## راه‌اندازی گروه VIP

1. گروه خصوصی بساز
2. ربات را اضافه و **ادمین** کن (دسترسی Invite Users)
3. شناسه گروه را بگیر (مثلاً `-100...`) و در `.env` بگذار: `VIP_GROUP_ID=`

## نصب

```powershell
cd telegram_bot
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env` را پر کن. در `assets/` بگذار: `full.pdf` (الزامی)، `sample.pdf`، `cover.jpg`

```powershell
python bot.py
```

## جریان

خرید → اطلاعات → کارت → رسید → تأیید ادمین → PDF + لینک VIP یک‌بارمصرف
