import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import datetime
import asyncio
from flask import Flask
from threading import Thread

TOKEN = "MTQwMDEyNjEwOTYwOTIzNDUwNQ.GLCU4h.8EWVc5t-6plvOT1tYyteRljjmeNba2PFgptHzQ"
OWNER_ROLE_ID = 1399535532773609482
ADMIN_ROLE_ID = 1400127284039516241
BLACKLIST_ROLE_ID = 1399870275931340892
LOG_CHANNEL_ID = 1399872619267883078
EMBED_CHANNEL_ID = 1388816778162999296
CATEGORY_ID = 1387074680711680030
FEEDBACK_CHANNEL_ID = 1399543182366347416
CREDIT_RECEIVER_ID = 1269270515005128715
STOCK_CHANNELS = [1400126843335741481, 1399875039859576982]
PROBOT_ID = 282859044593598464
PREFIX = "-"

# قائمة المنتجات ذات الكمية اللانهائية
INFINITE_PRODUCTS = ["نسخ سيرفرات", "كويستات"]

PRODUCTS = {
    "nitro": 1,
    "account": 1,
    "نسخ سيرفرات": 1,
    "كويستات": 1
}

DB_FILE = "database.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"products": {}}, f)

with open(DB_FILE, "r") as f:
    db = json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📘 أوامر البوت", color=discord.Color.blue())
    embed.add_field(name="-add [اسم] [المنتج]", value="إضافة منتج للستوك", inline=False)
    embed.add_field(name="-addstock [اسم] [السعر] [المنتج]", value="إضافة منتج مع السعر", inline=False)
    embed.add_field(name="-stock", value="عرض الستوك الحالي", inline=False)
    embed.add_field(name="-buy [اسم]", value="شراء منتج من أي روم", inline=False)
    
    # إضافة أوامر الإدارة
    if is_owner_or_admin(ctx):
        embed.add_field(name="🔧 **أوامر الإدارة**", value="━━━━━━━━━━━━━━━━━━━━", inline=False)
        embed.add_field(name="-prix [اسم المنتج] [السعر الجديد]", value="تغيير سعر منتج موجود", inline=False)
        embed.add_field(name="-kmi [اسم المنتج] [الكمية الجديدة]", value="تغيير كمية منتج (استخدم ♾️ للكمية اللانهائية)", inline=False)
        embed.add_field(name="-delete [اسم المنتج]", value="حذف منتج من النظام", inline=False)
    
    embed.set_footer(text="كل الحقوق محفوظا لي GTR ")
    await ctx.send(embed=embed)

def is_owner_or_admin(ctx):
    return any(role.id in [OWNER_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles)

class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="📨 افتح تذكرة شراء", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if discord.utils.get(member.roles, id=BLACKLIST_ROLE_ID):
            return await interaction.response.send_message("🚫 ما بتقدر تفتح تذكرة لأنك بلاك ليست.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"طلب-{member.name}",
            overwrites=overwrites,
            category=guild.get_channel(CATEGORY_ID)
        )

        await interaction.response.send_message(f"📩 تم فتح تذكرتك هون: {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(title="📦 المنتجات المتوفرة", color=discord.Color.blurple())
        for name, price in PRODUCTS.items():
            quantity = len(db["products"].get(name, []))
            quantity_str = "♾️" if name in INFINITE_PRODUCTS else str(quantity)
            embed.add_field(
                name=name,
                value=f"💰 السعر: `{price}` كريدت\n📦 الكمية: `{quantity_str}`\n🛒 اكتب `-buy {name}` لطلبه.",
                inline=False
            )

        await ticket_channel.send(content=f"{member.mention} هاي التفاصيل 👇", embed=embed)

class ProductMenu(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())

@bot.command()
async def stock(ctx):
    if ctx.channel.id not in STOCK_CHANNELS:
        return await ctx.send("❌ هذا الأمر فقط في روم الستوك أو التحكم.")
    embed = discord.Embed(title="📦 المنتجات المتوفرة", color=discord.Color.blurple())
    for name, price in PRODUCTS.items():
        quantity = len(db["products"].get(name, []))
        quantity_str = "♾️" if name in INFINITE_PRODUCTS else str(quantity)
        embed.add_field(
            name=name,
            value=f"💰 السعر: `{price}` كريدت\n📦 الكمية: `{quantity_str}`\n🛒 استخدم: `-buy {name}`",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def add(ctx, product: str, *, data: str):
    if not is_owner_or_admin(ctx): return
    if product not in db["products"]:
        db["products"][product] = []
    db["products"][product].append(data)
    save_db()
    await ctx.send(f"✅ تمت إضافة `{product}` إلى الستوك.")

@bot.command()
async def addstock(ctx, *, args: str):
    if not is_owner_or_admin(ctx): return await ctx.send("🚫 ما عندك صلاحية.")
    try:
        name, price, data = args.split(" ", 2)
        price = int(price)
        PRODUCTS[name] = price
        if name not in db["products"]:
            db["products"][name] = []
        db["products"][name].append(data)
        save_db()
        await ctx.send(f"✅ أضفنا `{name}` بسعر `{price}`.")
    except:
        await ctx.send("❌ الصيغة: -addstock [اسم] [سعر] [المنتج]")

@bot.command()
async def prix(ctx, product_name: str, new_price: int):
    """أمر تغيير سعر المنتج - للمالكين والمسؤولين فقط"""
    if not is_owner_or_admin(ctx):
        return await ctx.send("🚫 ما عندك صلاحية لاستخدام هذا الأمر.")
    
    # البحث عن المنتج
    matched = None
    for key in PRODUCTS:
        if product_name.lower() in key.lower() or key.lower() in product_name.lower():
            matched = key
            break
    
    if not matched:
        return await ctx.send(f"❌ المنتج `{product_name}` غير موجود في النظام.")
    
    # حفظ السعر القديم
    old_price = PRODUCTS[matched]
    
    # تحديث السعر
    PRODUCTS[matched] = new_price
    
    # إرسال رسالة التأكيد
    embed = discord.Embed(
        title="💰 تم تحديث السعر",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="📦 المنتج", value=f"`{matched}`", inline=True)
    embed.add_field(name="💸 السعر القديم", value=f"`{old_price}` كريدت", inline=True)
    embed.add_field(name="💵 السعر الجديد", value=f"`{new_price}` كريدت", inline=True)
    embed.set_footer(text=f"تم التحديث بواسطة {ctx.author}")
    
    await ctx.send(embed=embed)
    
    # تسجيل العملية في قناة اللوغ
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(
            title="📊 تحديث سعر منتج",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.add_field(name="👤 المسؤول", value=ctx.author.mention, inline=True)
        log_embed.add_field(name="📦 المنتج", value=f"`{matched}`", inline=True)
        log_embed.add_field(name="💰 التغيير", value=f"`{old_price}` ← `{new_price}`", inline=True)
        await log_channel.send(embed=log_embed)

@bot.command()
async def kmi(ctx, product_name: str, *, quantity: str):
    """أمر تغيير كمية المنتج - للمالكين والمسؤولين فقط"""
    if not is_owner_or_admin(ctx):
        return await ctx.send("🚫 ما عندك صلاحية لاستخدام هذا الأمر.")
    
    # البحث عن المنتج
    matched = None
    for key in PRODUCTS:
        if product_name.lower() in key.lower() or key.lower() in product_name.lower():
            matched = key
            break
    
    if not matched:
        return await ctx.send(f"❌ المنتج `{product_name}` غير موجود في النظام.")
    
    # حفظ الكمية القديمة
    old_quantity = len(db["products"].get(matched, []))
    old_quantity_str = "♾️" if matched in INFINITE_PRODUCTS else str(old_quantity)
    
    # معالجة الكمية الجديدة
    if quantity == "♾️" or quantity.lower() == "infinity":
        # تحويل المنتج إلى كمية لانهائية
        if matched not in INFINITE_PRODUCTS:
            INFINITE_PRODUCTS.append(matched)
        new_quantity_str = "♾️"
    else:
        try:
            new_quantity_num = int(quantity)
            if new_quantity_num < 0:
                return await ctx.send("❌ الكمية يجب أن تكون رقم موجب أو ♾️.")
            
            # إزالة المنتج من قائمة المنتجات اللانهائية إذا كان فيها
            if matched in INFINITE_PRODUCTS:
                INFINITE_PRODUCTS.remove(matched)
            
            # تحديث الكمية
            if matched not in db["products"]:
                db["products"][matched] = []
            
            current_items = db["products"][matched]
            current_count = len(current_items)
            
            if new_quantity_num > current_count:
                # إضافة عناصر فارغة للوصول للكمية المطلوبة
                for i in range(new_quantity_num - current_count):
                    db["products"][matched].append(f"عنصر مؤقت #{current_count + i + 1} - يرجى تحديثه")
            elif new_quantity_num < current_count:
                # تقليل الكمية
                db["products"][matched] = current_items[:new_quantity_num]
            
            new_quantity_str = str(new_quantity_num)
            save_db()
            
        except ValueError:
            return await ctx.send("❌ الكمية يجب أن تكون رقم صحيح أو ♾️.")
    
    # إرسال رسالة التأكيد
    embed = discord.Embed(
        title="📊 تم تحديث الكمية",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="📦 المنتج", value=f"`{matched}`", inline=True)
    embed.add_field(name="📈 الكمية القديمة", value=f"`{old_quantity_str}`", inline=True)
    embed.add_field(name="📊 الكمية الجديدة", value=f"`{new_quantity_str}`", inline=True)
    embed.set_footer(text=f"تم التحديث بواسطة {ctx.author}")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['del'])
async def delete(ctx, *, product_name: str):
    """أمر حذف المنتج - للمالكين والمسؤولين فقط"""
    if not is_owner_or_admin(ctx):
        return await ctx.send("🚫 ما عندك صلاحية لاستخدام هذا الأمر.")
    
    # البحث عن المنتج
    matched = None
    for key in PRODUCTS:
        if product_name.lower() in key.lower() or key.lower() in product_name.lower():
            matched = key
            break
    
    if not matched:
        return await ctx.send(f"❌ المنتج `{product_name}` غير موجود في النظام.")
    
    # حفظ معلومات المنتج قبل الحذف
    deleted_price = PRODUCTS[matched]
    deleted_items = len(db["products"].get(matched, []))
    
    # حذف المنتج من القائمة والستوك
    del PRODUCTS[matched]
    if matched in db["products"]:
        del db["products"][matched]
    
    # حفظ التغييرات
    save_db()
    
    # إرسال رسالة التأكيد
    embed = discord.Embed(
        title="🗑️ تم حذف المنتج",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="📦 المنتج المحذوف", value=f"`{matched}`", inline=True)
    embed.add_field(name="💰 السعر", value=f"`{deleted_price}` كريدت", inline=True)
    embed.add_field(name="📊 الكمية المحذوفة", value=f"`{deleted_items}` عنصر", inline=True)
    embed.set_footer(text=f"تم الحذف بواسطة {ctx.author}")
    
    await ctx.send(embed=embed)
    
    # تسجيل العملية في قناة اللوغ
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(
            title="🗑️ حذف منتج",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.add_field(name="👤 المسؤول", value=ctx.author.mention, inline=True)
        log_embed.add_field(name="📦 المنتج", value=f"`{matched}`", inline=True)
        log_embed.add_field(name="📊 البيانات", value=f"السعر: `{deleted_price}`\nالكمية: `{deleted_items}`", inline=True)
        await log_channel.send(embed=log_embed)

@bot.command()
async def buy(ctx, *, product_name: str):
    if discord.utils.get(ctx.author.roles, id=BLACKLIST_ROLE_ID):
        return await ctx.send("🚫 ما بتقدر تشتري لأنك بلاك ليست.")

    matched = next((key for key in PRODUCTS if product_name.lower() in key.lower().split("/")), None)
    if not matched:
        return await ctx.send("❌ المنتج غير متوفر حالياً.")

    product_list = db["products"].get(matched, [])
    if matched not in INFINITE_PRODUCTS and not product_list:
        return await ctx.send("❌ المنتج غير متوفر في الستوك حالياً.")

    price = PRODUCTS.get(matched)
    await ctx.send(
        f"🔔 {ctx.author.mention} لشراء **{matched}**، حول `{price}` كريدت لـ <@{CREDIT_RECEIVER_ID}>.\n"
        f"📌 مثال: `c <@{CREDIT_RECEIVER_ID}> {price}`\n"
        f"⌛ بنتظر تحويلك 60 ثانية..."
    )

    def check(m):
        return (
            m.channel == ctx.channel and
            m.author.id == PROBOT_ID and
            ":moneybag:" in m.content and
            ctx.author.name in m.content and
            str(CREDIT_RECEIVER_ID) in m.content and
            f"${price}" in m.content
        )

    try:
        await bot.wait_for("message", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        return await ctx.send("⌛ ما وصل تحويل. جرب مرة ثانية.")

    item = "سيتم التواصل معك من قبل الإدارة لاحقاً" if matched in INFINITE_PRODUCTS else db["products"][matched].pop(0)
    if matched not in INFINITE_PRODUCTS:
        save_db()

    try:
        if matched in ["nitro", "account"]:
            await ctx.author.send(
                f"✅ شكراً لشرائك **{matched}**!\n"
                f"🔐 منتجك:\n"
                f"||{item}||\n"
                f"💬 قيمنا <#{FEEDBACK_CHANNEL_ID}> ❤️"
            )
            await ctx.send("✅ تم إرسال المنتج عالخاص!")
        else:
            await ctx.author.send(
                f"✅ شكراً لشرائك **{matched}**!\n"
                f"📦 طلبك قيد المراجعة من المسؤولين. راح يتم التواصل معك قريباً."
            )
            await ctx.send("⏳ تم تسجيل طلبك، راح يتم التواصل معك قريباً.")
            log = bot.get_channel(LOG_CHANNEL_ID)
            if log:
                mention_roles = f"<@&{OWNER_ROLE_ID}> <@&{ADMIN_ROLE_ID}>"
                await log.send(f"🔔 {mention_roles} في طلب جديد:\n👤 {ctx.author.mention} (`{ctx.author.id}`)\n📦 `{matched}`")
    except:
        if matched not in INFINITE_PRODUCTS:
            db["products"][matched].insert(0, item)
            save_db()
        await ctx.send("❌ افتح الخاص عشان نرسل لك المنتج.")

@bot.event
async def on_ready():
    print(f"✅ البوت جاهز كـ {bot.user}")
    channel = bot.get_channel(EMBED_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📦 GTR SHOP",
            description="اضغط الزر لتفتح تذكرة وتشتري 👇",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text="كل الحقوق محفوظة لـ GTR ")
        await channel.send(embed=embed, view=ProductMenu())

# ====== FLASK KEEP-ALIVE ======
app = Flask('')

@app.route('/')
def home():
    return "✅ ALG Effects Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

# ====== RUN BOT ======
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
