import os, logging, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database import init_db, list_products, get_product, create_order, set_stock, set_price
from products import PRODUCTS

logging.basicConfig(level=logging.INFO)
log=logging.getLogger("drinkshop")
BOT_TOKEN=os.environ["BOT_TOKEN"]
ADMIN_ID=int(os.environ.get("ADMIN_ID","0"))
CATEGORIES={"sparkling":"🥂 SPUMANT","wine":"🍷 VIN","drinks":"🥤 BĂUTURI"}
SUBCATS={
 "sparkling":{"Brut":"Brut","Demisec":"Demisec","Dulce":"Dulce"},
 "wine":{"Alb":"Alb","Roșu":"Roșu"}
}

def stock_label(qty):
    if qty <= 5: return "Stoc puțin"
    if qty <= 18: return "Stoc mediu"
    return "Stoc bun"

def main_menu():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("🥂 SPUMANT",callback_data="cat:sparkling")],
      [InlineKeyboardButton("🍷 VIN",callback_data="cat:wine")],
      [InlineKeyboardButton("🥤 BĂUTURI",callback_data="cat:drinks")],
      [InlineKeyboardButton("🛒 Coșul meu",callback_data="cart"),
       InlineKeyboardButton("📦 Plasează comanda",callback_data="checkout")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart",{})
    await update.message.reply_text(
      "Bun venit la DRINKSHOP! 🍷\n\nPentru a consulta catalogul și a comanda, confirmă că ai vârsta legală pentru achiziționarea băuturilor alcoolice.",
      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Am vârsta legală",callback_data="age:yes")],
                                         [InlineKeyboardButton("Nu",callback_data="age:no")]]))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    if data=="age:no":
        await q.edit_message_text("Accesul la produsele alcoolice nu este disponibil.")
        return
    if data=="age:yes":
        context.user_data["age_ok"]=True
        await q.edit_message_text("Bun venit la DRINKSHOP! Alege o categorie:",reply_markup=main_menu()); return
    if not context.user_data.get("age_ok"):
        await q.answer("Confirmă mai întâi vârsta.",show_alert=True); return
    if data.startswith("cat:"):
        cat=data.split(":")[1]
        if cat in SUBCATS:
            kb=[[InlineKeyboardButton(s,callback_data=f"sub:{cat}:{s}")] for s in SUBCATS[cat]]
            kb.append([InlineKeyboardButton("⬅️ Meniu",callback_data="home")])
            await q.edit_message_text(CATEGORIES[cat],reply_markup=InlineKeyboardMarkup(kb)); return
        await show_products(q,cat,None); return
    if data.startswith("sub:"):
        _,cat,sub=data.split(":",2)
        await show_products(q,cat,sub); return
    if data.startswith("prod:"):
        pid=int(data.split(":")[1]); p=await get_product(pid)
        if not p: await q.edit_message_text("Produs indisponibil."); return
        _,name,desc,price,qty,photo,award,cat,sub=p
        caption=f"<b>{name}</b>\n\n{award+'\\n\\n' if award else ''}{desc}\n\n<b>{price} Lei</b>\n{stock_label(qty)}"
        kb=[[InlineKeyboardButton("➕ Adaugă în coș",callback_data=f"add:{pid}")],
            [InlineKeyboardButton("⬅️ Înapoi la meniu",callback_data="home")]]
        if photo:
            try:
                await q.message.reply_photo(photo=photo,caption=caption,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(kb))
                await q.delete_message()
            except Exception:
                await q.edit_message_text(caption,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(kb))
        else: await q.edit_message_text(caption,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(kb))
        return
    if data.startswith("add:"):
        pid=int(data.split(":")[1]); p=await get_product(pid)
        if p and p[4]>0:
            cart=context.user_data.setdefault("cart",{}); cart[pid]=cart.get(pid,0)+1
            await q.answer("Adăugat în coș!",show_alert=True)
        else: await q.answer("Produs momentan indisponibil.",show_alert=True)
        return
    if data=="home":
        await q.edit_message_text("Alege o categorie:",reply_markup=main_menu()); return
    if data=="cart":
        await show_cart(q,context); return
    if data=="checkout":
        cart=context.user_data.get("cart",{})
        if not cart: await q.edit_message_text("Coșul este gol.",reply_markup=main_menu()); return
        context.user_data["awaiting_order_details"]=True
        await q.edit_message_text("Trimite într-un singur mesaj:\nNume și prenume\nTelefon\nAdresa/localitatea de livrare\n\nVom confirma comanda înainte de procesare.")
        return

async def show_products(q,cat,sub):
    products=await list_products(cat,sub)
    if not products:
        await q.edit_message_text("Nu sunt produse disponibile în această secțiune.",reply_markup=main_menu()); return
    kb=[]
    for p in products:
        pid,name,desc,price,qty,photo,award,c,s=p
        kb.append([InlineKeyboardButton(f"{name} — {price} Lei · {stock_label(qty)}",callback_data=f"prod:{pid}")])
    kb.append([InlineKeyboardButton("⬅️ Meniu",callback_data="home"),InlineKeyboardButton("🛒 Coș",callback_data="cart")])
    await q.edit_message_text("Alege produsul:",reply_markup=InlineKeyboardMarkup(kb))

async def show_cart(q,context):
    cart=context.user_data.get("cart",{})
    if not cart: await q.edit_message_text("Coșul este gol.",reply_markup=main_menu()); return
    lines=[]; total=0
    for pid,n in cart.items():
        p=await get_product(pid)
        if p:
            subtotal=p[3]*n; total+=subtotal; lines.append(f"• {p[1]} × {n} = {subtotal} Lei")
    await q.edit_message_text("🛒 COȘUL TĂU\n\n"+"\n".join(lines)+f"\n\n<b>Total: {total} Lei</b>",
      parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Plasează comanda",callback_data="checkout")],
      [InlineKeyboardButton("⬅️ Meniu",callback_data="home")]]))

async def text_message(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_order_details"):
        details=update.message.text
        cart=context.user_data.get("cart",{})
        lines=[]; total=0
        for pid,n in cart.items():
            p=await get_product(pid)
            if p:
                lines.append(f"{p[1]} x {n}"); total+=p[3]*n
        if not lines:
            await update.message.reply_text("Coșul este gol."); return
        order_id=await create_order(update.effective_user.id,update.effective_user.username or "",details,lines,total)
        if ADMIN_ID:
            await context.bot.send_message(ADMIN_ID,f"🆕 COMANDĂ #{order_id}\n\n"+"\n".join(lines)+f"\n\nTotal: {total} Lei\n\nDate client:\n{details}")
        context.user_data["cart"]={}
        context.user_data["awaiting_order_details"]=False
        await update.message.reply_text(f"Mulțumim! Comanda #{order_id} a fost transmisă. Administratorul te va contacta pentru confirmare.")
        return
    await update.message.reply_text("Folosește /start pentru meniul magazinului.")

async def admin(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("Comandă disponibilă doar administratorului."); return
    await update.message.reply_text("Administrare simplă:\n/stock ID CANTITATE\n/price ID PREȚ\n\nID-urile produselor le vom lista în etapa de configurare.")

async def stock_cmd(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or len(context.args)!=2: return
    try:
        await set_stock(int(context.args[0]),int(context.args[1]))
        await update.message.reply_text("Stoc actualizat.")
    except Exception: await update.message.reply_text("Format: /stock ID CANTITATE")

async def price_cmd(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or len(context.args)!=2: return
    try:
        await set_price(int(context.args[0]),float(context.args[1]))
        await update.message.reply_text("Preț actualizat.")
    except Exception: await update.message.reply_text("Format: /price ID PREȚ")

async def post_init(app):
    await init_db(PRODUCTS)

def main():
    app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CommandHandler("stock",stock_cmd))
    app.add_handler(CommandHandler("price",price_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_message))
    app.run_polling()

if __name__=="__main__": main()
