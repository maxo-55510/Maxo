# MAXO Railway SOCKS Panel

پنل مدیریت SOCKS5 با نام کاربر، حجم، تاریخ انقضا، فعال/غیرفعال و آمار مصرف.

## Railway Variables

ADMIN_USER=admin
ADMIN_PASSWORD=یک-رمز-قوی
SESSION_SECRET=یک-رشته-طولانی-تصادفی
PORT=3000
SOCKS_PORT=1080

## Deploy

Repository را در GitHub قرار بده و همان Repository را در Railway Deploy کن.

برای ماندگاری SQLite یک Railway Volume روی `/app/data` قرار بده.

## نکته IP تمیز

فیلد IP تمیز نباید IP دلخواه را جعل کند. IP خروجی SOCKS، IP واقعی سرویس/Upstream است. اگر IP تمیز اختصاصی داری، باید به‌عنوان upstream استفاده شود؛ صرفاً وارد کردن یک IP در پنل، IP خروجی را تغییر نمی‌دهد.
