import base64
import json
import os
import secrets
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable সেট করা নেই")

HEADER_NAME = "ENCRYPTED BY KAWSAR"
TG_LINK = "https://t.me/TC_COMMIUNITY"
DEFAULT_TARGET_KB = 850
MIN_KB = 100
MAX_KB = 30000


def clamp_kb(value) -> int:
    try:
        num = int(str(value).strip())
    except (TypeError, ValueError):
        return DEFAULT_TARGET_KB
    return max(MIN_KB, min(MAX_KB, num))


def get_user_target_kb(context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data is None:
        return DEFAULT_TARGET_KB
    return clamp_kb(context.user_data.get("target_kb", DEFAULT_TARGET_KB))


def xb(data: bytes, key: bytes) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def rev_chunks(data: bytes, size: int = 64) -> bytes:
    out = bytearray(len(data))
    i = 0
    while i < len(data):
        end = min(i + size, len(data))
        chunk = data[i:end][::-1]
        out[i:end] = chunk
        i = end
    return bytes(out)


def junk_b64(bytes_needed: int) -> str:
    bytes_needed = max(0, int(bytes_needed))
    if bytes_needed == 0:
        return ""
    piece = 262144
    parts = []
    left = bytes_needed
    while left > 0:
        take = min(piece, left)
        raw_len = (take * 3 + 3) // 4
        b64_str = base64.b64encode(secrets.token_bytes(raw_len)).decode("ascii")
        parts.append(b64_str[:take])
        left -= take
    return "".join(parts)


def esc_comment(s: str) -> str:
    return str(s or "").replace("--", "—")


def build_heavy(
    source_html: str,
    header_name: str = HEADER_NAME,
    tg_link: str = TG_LINK,
    target_kb: int = DEFAULT_TARGET_KB,
) -> str:
    data = source_html.encode("utf-8")
    k1 = secrets.token_bytes(32)
    k2 = secrets.token_bytes(32)

    data = xb(data, k1)
    data = rev_chunks(data, 64)
    data = xb(data, k2)
    b64 = base64.b64encode(data).decode("ascii")

    seg_size = 120
    segs = [b64[i:i + seg_size] for i in range(0, len(b64), seg_size)]

    header = esc_comment(header_name)
    tg = esc_comment(tg_link)

    clamped_kb = clamp_kb(target_kb)
    target_bytes = clamped_kb * 1024
    approx = 2500 + len(json.dumps(segs)) + 200
    remain = max(0, target_bytes - approx)
    each = remain // 4

    j1 = junk_b64(each)
    j2 = junk_b64(each)
    j3 = junk_b64(each)
    j4 = junk_b64(max(0, remain - each * 3))

    segs_json = json.dumps(segs)
    k1_json = json.dumps(list(k1))
    k2_json = json.dumps(list(k2))

    return f"""<!--
╔══════════════════════════════════════════════════════════╗
║  🔒 {header}
║  Layers: XOR → ChunkRev → XOR → B64 → Segment Vault
║  Size-Lock: Heavy Junk Pad Enabled ({clamped_kb} KB)
║  TG: {tg}
║  Do not modify — integrity locked
╚══════════════════════════════════════════════════════════╝
-->
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KAWSAR</title>
<style>body{{margin:0;background:#000;color:#0ff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh}}.boot{{text-align:center;letter-spacing:1px}}</style>
</head>
<body>
<div class="boot" id="boot">🔒 {header} · DECRYPTING...</div>
<script>
(function(){{
"use strict";
var _J1="{j1}";
var _J2="{j2}";
var _J3="{j3}";
var _J4="{j4}";
var _S={segs_json};
var _K1={k1_json};
var _K2={k2_json};
function _xb(s,k){{var o=new Uint8Array(s.length);for(var i=0;i<s.length;i++)o[i]=s[i]^k[i%k.length];return o}}
function _b64(s){{var b=atob(s),u=new Uint8Array(b.length);for(var i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u}}
function _rev(u,c){{var out=new Uint8Array(u.length),i=0;while(i<u.length){{var e=Math.min(i+c,u.length),n=e-i;for(var j=0;j<n;j++)out[i+j]=u[e-1-j];i=e}}return out}}
try{{
  var b64=_S.join("");
  var u=_b64(b64);
  u=_xb(u,_K2);
  u=_rev(u,64);
  u=_xb(u,_K1);
  var html=new TextDecoder().decode(u);
  document.open();document.write(html);document.close();
}}catch(e){{
  var el=document.getElementById("boot");
  if(el) el.textContent="❌ DECRYPT FAIL";
}}
if(false){{console.log(_J1.length+_J2.length+_J3.length+_J4.length)}}
}})();
</script>
</body>
</html>"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_kb = get_user_target_kb(context)
    keyboard = [["🔒 ENCRYPT HTML", "📏 SET TARGET KB"], ["⚡ INFO"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"🔒 **HTML Heavy Encoder Bot**

"
        f"বর্তমান Target Size: **`{target_kb} KB`** (`{MIN_KB}`–`{MAX_KB}` KB)
"
        f"• `.html` ফাইল পাঠিয়ে সরাসরি এনক্রিপ্ট করুন
"
        f"• সাইজ বদলাতে `/setkb 5000` লিখুন",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def set_kb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_kb = get_user_target_kb(context)
    if not context.args:
        context.user_data["awaiting_kb"] = True
        await update.message.reply_text(
            f"📏 বর্তমান Target KB: **`{current_kb} KB`**

"
            f"নতুন Target KB লিখুন (`{MIN_KB}` থেকে `{MAX_KB}` এর মধ্যে, যেমন: `5000`):",
            parse_mode="Markdown",
        )
        return

    raw_val = context.args[0]
    try:
        num = int(raw_val)
    except ValueError:
        await update.message.reply_text("❌ দয়া করে একটি বৈধ সংখ্যা দিন (যেমন: `/setkb 5000`)।")
        return

    clamped = clamp_kb(num)
    context.user_data["target_kb"] = clamped
    context.user_data["awaiting_kb"] = False

    note = ""
    if num != clamped:
        note = f"
⚠️ সীমার বাইরে থাকায় `{MIN_KB}`–`{MAX_KB}` KB-এর মধ্যে **`{clamped} KB`** সেট করা হয়েছে।"

    await update.message.reply_text(f"✅ আপনার Target Size সেট হয়েছে: **`{clamped} KB`**{note}", parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    if context.user_data.get("awaiting_kb"):
        if txt.isdigit():
            clamped = clamp_kb(int(txt))
            context.user_data["target_kb"] = clamped
            context.user_data["awaiting_kb"] = False
            await update.message.reply_text(
                f"✅ Target Size সেট হয়েছে: **`{clamped} KB`**
এখন `.html` ফাইল পাঠান।",
                parse_mode="Markdown",
            )
            return
        else:
            context.user_data["awaiting_kb"] = False

    if txt == "🔒 ENCRYPT HTML":
        kb = get_user_target_kb(context)
        await update.message.reply_text(
            f"আপনার `.html` ফাইলটি Document হিসেবে আপলোড করুন।
বর্তমান Target Size: **`{kb} KB`**",
            parse_mode="Markdown",
        )
    elif txt == "📏 SET TARGET KB":
        await set_kb_command(update, context)
    elif txt == "⚡ INFO":
        kb = get_user_target_kb(context)
        await update.message.reply_text(
            f"Header: {HEADER_NAME}
Your Target Size: {kb} KB
Allowed Range: {MIN_KB}–{MAX_KB} KB
Channel: {TG_LINK}"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not (doc.file_name or "").lower().endswith((".html", ".htm")):
        await update.message.reply_text("❌ দয়া করে একটি বৈধ `.html` বা `.htm` ফাইল আপলোড করুন।")
        return

    target_kb = get_user_target_kb(context)
    status_msg = await update.message.reply_text(f"⏳ `{target_kb} KB` টার্গেটে ফাইল এনক্রিপ্ট হচ্ছে...", parse_mode="Markdown")
    in_path = f"in_{doc.file_unique_id}.html"
    out_name = f"Encrypted_{doc.file_name}"
    out_path = f"out_{doc.file_unique_id}.html"

    try:
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(in_path)

        with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
            source_html = f.read()

        packed = build_heavy(source_html, target_kb=target_kb)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(packed)

        size_kb = os.path.getsize(out_path) / 1024
        await status_msg.delete()
        with open(out_path, "rb") as out_f:
            await update.message.reply_document(
                document=out_f,
                filename=out_name,
                caption=(
                    f"👑 ━━━━━━━━━━━━━━━
"
                    f"🛡️ **{HEADER_NAME}**
"
                    f"👑 ━━━━━━━━━━━━━━━

"
                    f"📄 **ফাইল নাম:** `{out_name}`
"
                    f"📦 **সাইজ:** `{size_kb:.1f} KB` (Target: `{target_kb} KB`)
"
                    f"🔐 **লেয়ার:** `XOR → ChunkRev → XOR → B64 → Vault`"
                ),
                parse_mode="Markdown",
            )
    except Exception as e:
        await status_msg.edit_text(f"❌ এরর হয়েছে: `{e}`", parse_mode="Markdown")
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.remove(p)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setkb", set_kb_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
