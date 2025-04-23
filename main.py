from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
import json
import os

TOKEN = '7709445317:AAEoLX-x4R8l3MGQIIR3Y9virP0b9NOFms0'  # Reemplaza con tu token real

profesores_validos = {
    "juanperez": "1234",
    "anagarcia": "abcd"
}

usuarios_logueados = set()
LOGIN_USUARIO, LOGIN_CLAVE, ESPERAR_ESTUDIANTES, ESPERAR_NOMBRE_ELIMINAR, ESPERAR_ASIGNAR = range(5)
ESTUDIANTES_FILE = "estudiantes.json"
OPTATIVAS_FILE = "optativas.json"

def cargar_estudiantes():
    if not os.path.exists(ESTUDIANTES_FILE):
        return []
    with open(ESTUDIANTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def cargar_optativas():
    if not os.path.exists(OPTATIVAS_FILE):
        return []
    with open(OPTATIVAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_estudiantes(estudiantes):
    with open(ESTUDIANTES_FILE, "w", encoding="utf-8") as f:
        json.dump(estudiantes, f, indent=4, ensure_ascii=False)

# ---------- BOTÓN CANCELAR INLINE ----------
cancelar_inline = InlineKeyboardMarkup([
    [InlineKeyboardButton("❎ Cancelar", callback_data="cancelar")]
])

# ---------- COMANDOS PRINCIPALES ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    optativos = cargar_optativas()  # Cargar las optativas desde el archivo
    texto = "📚 *Cursos optativos disponibles:*\n\n"
    for curso in optativos:
        plazas = curso.get('plazas', 'No disponible')  # Usar valor por defecto si no existe 'plazas'
        texto += f"• *{curso['nombre']}* (Prof: {curso['profesor']}, Plazas: {plazas})\n"
    texto += "\nSi eres profesor, usa /login"
    await update.message.reply_markdown(texto)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 Usuario:")
    return LOGIN_USUARIO

async def recibir_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["usuario"] = update.message.text
    await update.message.reply_text("🔑 Contraseña:")
    return LOGIN_CLAVE

async def recibir_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data["usuario"]
    clave = update.message.text
    if user in profesores_validos and profesores_validos[user] == clave:
        usuarios_logueados.add(update.effective_user.id)
        teclado = [[
            KeyboardButton("👥 Ver estudiantes"),
            KeyboardButton("➕ Agregar estudiantes"),
        ], [
            KeyboardButton("❌ Eliminar estudiante"),
            KeyboardButton("🧹 Vaciar lista"),
        ], [
            KeyboardButton("📌 Asignar optativa"),
            KeyboardButton("🔓 Cerrar sesión")
        ]]
        await update.message.reply_text(
            "✅ Login exitoso.",
            reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True)
        )
    else:
        await update.message.reply_text("❌ Usuario o contraseña incorrectos.")
    return ConversationHandler.END

# ---------- CANCELAR OPERACIÓN ----------

async def cancelar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in usuarios_logueados:
        await query.edit_message_text("❌ No tienes una sesión activa.")
        return ConversationHandler.END

    # Borrar el mensaje anterior con el botón
    await query.message.delete()

    teclado = [[
        KeyboardButton("👥 Ver estudiantes"),
        KeyboardButton("➕ Agregar estudiantes"),
    ], [
        KeyboardButton("❌ Eliminar estudiante"),
        KeyboardButton("🧹 Vaciar lista"),
    ], [
        KeyboardButton("📌 Asignar optativa"),
        KeyboardButton("🔓 Cerrar sesión")
    ]]
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="✅ Acción cancelada.\n📋 Menú principal:",
        reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True)
    )
    return ConversationHandler.END

# ---------- MENÚ DE PROFESOR ----------

async def manejar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in usuarios_logueados:
        return ConversationHandler.END  # No responder si no está logueado

    texto = update.message.text

    if texto == "👥 Ver estudiantes":
        estudiantes = cargar_estudiantes()
        if not estudiantes:
            await update.message.reply_text("📂 Lista vacía.")
            return

        grupos = {}
        for est in estudiantes:
            grupo = est["grupo"]
            grupos.setdefault(grupo, []).append(est)

        respuesta = "👥 *Estudiantes por grupo:*\n\n"
        for grupo in sorted(grupos.keys()):
            respuesta += f"*Grupo {grupo}:*\n"
            for est in grupos[grupo]:
                opt = est["optativa"] if est["optativa"] else "Ninguna"
                respuesta += f"• {est['nombre']} - Optativa: {opt}\n"
            respuesta += "\n"
        await update.message.reply_markdown(respuesta)

    elif texto == "➕ Agregar estudiantes":
        await update.message.reply_text(
            "📨 Envía los estudiantes en el formato:\n\n`Nombre Apellido1 Apellido2 Grupo`\nUno por línea.",
            parse_mode="Markdown",
            reply_markup=cancelar_inline
        )
        return ESPERAR_ESTUDIANTES

    elif texto == "❌ Eliminar estudiante":
        await update.message.reply_text(
            "✂️ Escribe los estudiantes a eliminar en el formato:\n\n`Nombre Apellido1 Apellido2 Grupo`\nUno por línea.:",
            reply_markup=cancelar_inline
        )
        return ESPERAR_NOMBRE_ELIMINAR

    elif texto == "🧹 Vaciar lista":
        guardar_estudiantes([])
        await update.message.reply_text("🗑️ Lista vaciada.")

    elif texto == "📌 Asignar optativa":
        await update.message.reply_text(
            "📥 Envía los estudiantes a asignar en el formato:\n\n`Nombre Apellido1 Apellido2 Grupo\nNombre2 Apellido3 Apellido4 Grupo2\nOptativa`\n",
            parse_mode="Markdown",
            reply_markup=cancelar_inline
        )

        return ESPERAR_ASIGNAR

    elif texto == "🔓 Cerrar sesión":
        usuarios_logueados.discard(user_id)
        await update.message.reply_text("👋 Sesión cerrada.", reply_markup=ReplyKeyboardRemove())

# ---------- FUNCIONES DE PROFESOR ----------

async def recibir_estudiantes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    lineas = texto.strip().split("\n")
    estudiantes = cargar_estudiantes()
    nuevos = 0
    duplicados = []

    for linea in lineas:
        partes = linea.strip().split()
        if len(partes) < 4:
            continue
        nombre = " ".join(partes[:-1])
        grupo = partes[-1]

        ya_existe = any(e["nombre"] == nombre and e["grupo"] == grupo for e in estudiantes)
        if ya_existe:
            duplicados.append(f"{nombre} ({grupo})")
            continue

        estudiantes.append({"nombre": nombre, "grupo": grupo, "optativa": ""})
        nuevos += 1

    guardar_estudiantes(estudiantes)

    respuesta = f"✅ {nuevos} estudiante(s) agregado(s).\n"
    if duplicados:
        respuesta += "\n⚠️ *No se agregaron por estar duplicados:*\n"
        respuesta += "\n".join(duplicados)
    await update.message.reply_markdown(respuesta)
    return ConversationHandler.END


async def recibir_nombre_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    lineas = texto.split("\n")

    estudiantes = cargar_estudiantes()
    no_encontrados = []
    eliminados = 0

    for linea in lineas:
        partes = linea.strip().split()
        if len(partes) < 4:
            no_encontrados.append(linea)
            continue
        nombre = " ".join(partes[:-1])
        grupo = partes[-1]

        original_len = len(estudiantes)
        estudiantes = [e for e in estudiantes if not (e["nombre"] == nombre and e["grupo"] == grupo)]

        if len(estudiantes) == original_len:
            no_encontrados.append(linea)
        else:
            eliminados += 1

    guardar_estudiantes(estudiantes)

    respuesta = f"✅ {eliminados} estudiante(s) eliminado(s).\n"
    if no_encontrados:
        respuesta += "\n⚠️ *Estudiantes no eliminados por error de escritura:*\n"
        respuesta += "\n".join(no_encontrados)
    await update.message.reply_markdown(respuesta)
    return ConversationHandler.END

async def recibir_asignar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    lineas = texto.split("\n")

    estudiantes = cargar_estudiantes()
    asignados = 0
    errores = []

    # Cargar las optativas desde el archivo
    optativos = cargar_optativas()

    bloque_actual = []
    for linea in lineas + [""]:  # Añadimos línea vacía para procesar el último bloque
        if linea.strip() == "":
            continue
        partes = linea.strip().split()
        # Si la línea tiene solo una o dos palabras, asumimos que es una optativa
        if len(partes) <= 3:
            nombre_optativa = " ".join(partes)
            optativa = next((o for o in optativos if o["nombre"].lower() == nombre_optativa.lower()), None)

            if not optativa:
                errores.append(f"❌ Optativa no encontrada: {nombre_optativa}")
                bloque_actual = []
                continue

            ya_asignados = [e for e in estudiantes if e["optativa"] == optativa["nombre"]]
            plazas_disponibles = optativa["plazas"] - len(ya_asignados)

            for est_linea in bloque_actual:
                est_partes = est_linea.strip().split()
                if len(est_partes) < 4:
                    errores.append(f"❌ Formato inválido: {est_linea}")
                    continue
                nombre = " ".join(est_partes[:-1])
                grupo = est_partes[-1]

                if plazas_disponibles <= 0:
                    errores.append(f"🚫 Sin plazas: {nombre} → {optativa['nombre']}")
                    continue

                encontrado = False
                for e in estudiantes:
                    if e["nombre"] == nombre and e["grupo"] == grupo:
                        e["optativa"] = optativa["nombre"]
                        asignados += 1
                        plazas_disponibles -= 1
                        encontrado = True
                        break

                if not encontrado:
                    errores.append(f"❌ Estudiante no encontrado: {nombre} ({grupo})")

            bloque_actual = []  # Reiniciar el bloque tras procesar una optativa
        else:
            bloque_actual.append(linea)

    guardar_estudiantes(estudiantes)

    respuesta = f"✅ {asignados} estudiante(s) asignado(s).\n"
    if errores:
        respuesta += "\n⚠️ Errores:\n" + "\n".join(errores)
    await update.message.reply_text(respuesta)
    return ConversationHandler.END

async def manejar_consulta_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.message.text.strip().lower()
    user_id = update.effective_user.id

    # No hacer nada si el usuario es un profesor logueado
    if user_id in usuarios_logueados:
        return

    optativas = cargar_optativas()
    coincidencias_opt = [o for o in optativas if o["nombre"].lower() == mensaje]

    if coincidencias_opt:
        opt = coincidencias_opt[0]
        texto = f"📘 *{opt['nombre']}*\n👨‍🏫 Profesor: {opt['profesor']}\n📝 {opt.get('descripcion', 'Sin descripción')}"
        await update.message.reply_markdown(texto)
        return

    # Buscar por nombre de profesor
    profesores = {}
    for o in optativas:
        prof = o["profesor"].lower()
        profesores.setdefault(prof, []).append(o)

    if mensaje in profesores:
        cursos = profesores[mensaje]
        texto = f"👨‍🏫 *{cursos[0]['profesor']}* imparte:\n\n"
        for c in cursos:
            texto += f"• *{c['nombre']}* — {c.get('descripcion', '')}\n"
        await update.message.reply_markdown(texto)
        return

# ---------- MAIN ----------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login)],
        states={
            LOGIN_USUARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_usuario)],
            LOGIN_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_clave)],
        },
        fallbacks=[]
    )

    profesor_conv = ConversationHandler(
        entry_points=[MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(user_id=usuarios_logueados),
            manejar_menu
        )],
        states={
            ESPERAR_ESTUDIANTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_estudiantes)],
            ESPERAR_NOMBRE_ELIMINAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_eliminar)],
            ESPERAR_ASIGNAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_asignar)],
        },
        fallbacks=[CallbackQueryHandler(cancelar_callback, pattern="^cancelar$")]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(profesor_conv)
    app.add_handler(CallbackQueryHandler(cancelar_callback, pattern="^cancelar$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_consulta_estudiante))
    print("🤖 Bot corriendo...")
    app.run_polling()