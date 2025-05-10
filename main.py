from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters,
)
import json
import os


TOKEN = '8024056515:AAF5hkA6X24P6ivtc2GG0nTZPUZ6xj8xPs0'  # Reemplaza con tu token real
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

def cargar_profesores():
    try:
        with open("profesores.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def validar_credenciales(usuario, clave):
    if usuario == "superadmin" and clave == "spr1234":
        return {"nombre": "SuperAdmin"}
    profesores = cargar_profesores()
    for prof in profesores:
        if prof["usuario"] == usuario and prof["clave"] == clave:
            return prof  # Devuelve el objeto completo
    return None

# ---------- BOTÓN CANCELAR INLINE ----------
cancelar_inline = InlineKeyboardMarkup([
    [InlineKeyboardButton("❎ Cancelar", callback_data="cancelar")]
])

cancelar_creacion_optativa_inline = InlineKeyboardMarkup([
    [InlineKeyboardButton("❎ Cancelar Creación de Optativa", callback_data="cancelar_creacion_optativa")]
])

menu_profesor = ReplyKeyboardMarkup([
    [KeyboardButton("👥 Ver estudiantes"), KeyboardButton("➕ Agregar estudiantes"), KeyboardButton("❌ Eliminar estudiante")],
    [KeyboardButton("➕ Crear optativa"), KeyboardButton("🗑️ Eliminar optativas"), KeyboardButton("📌 Asignar optativa")],
    [KeyboardButton("🧹 Vaciar lista"), KeyboardButton("🔓 Cerrar sesión")]
], resize_keyboard=True)

# ---------- CREACIÓN DE OPTATIVAS ----------

# Estados de la conversación
CREAR_NOMBRE, CREAR_PROFESOR, CREAR_DESCRIPCION, CREAR_PLAZAS = range(4)

# Cargar las optativas desde el archivo JSON
def cargar_optativas():
    with open("optativas.json", "r", encoding="utf-8") as file:
        return json.load(file)

# Guardar las optativas al archivo JSON
def guardar_optativas(optativas):
    with open("optativas.json", "w", encoding="utf-8") as file:
        json.dump(optativas, file, indent=4)

# Función para iniciar la creación de optativa
async def iniciar_crear_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Vamos a crear una nueva optativa.\n\nPor favor, ingresa el nombre de la optativa:",
        reply_markup=cancelar_creacion_optativa_inline  # Usar el nuevo botón de cancelación
    )
    return CREAR_NOMBRE


# En este paso, recibirás el nombre de la optativa
async def recibir_nombre_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    
    # Cargar optativas existentes
    with open("optativas.json", "r", encoding="utf-8") as f:
        optativas = json.load(f)
    
    # Verificar si ya existe una optativa con ese nombre
    if any(optativa["nombre"].lower() == nombre.lower() for optativa in optativas):
        await update.message.reply_text("⚠️ Ya existe una optativa con ese nombre. Por favor, elige uno diferente.")
        return CREAR_NOMBRE

    # Guardar nombre temporalmente
    context.user_data["optativa"] = {"nombre": nombre}
    await update.message.reply_text("✏️ Ahora ingresa el nombre del profesor que impartirá la optativa:")
    return CREAR_PROFESOR

# Otros estados de la conversación
async def recibir_profesor_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['optativa']['profesor'] = update.message.text
    await update.message.reply_text("✏️ Escribe una descripción para la optativa:")
    return CREAR_DESCRIPCION

async def recibir_descripcion_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    context.user_data["optativa"]["descripcion"] = texto  # Guardamos la descripción
    await update.message.reply_text("🔢 Ingresa el número de plazas disponibles (puedes poner -1 para un número infinito):")
    return CREAR_PLAZAS  # Estado para recibir el número de plazas

async def recibir_plazas_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        plazas = int(texto)
        context.user_data["optativa"]["plazas"] = plazas
    except ValueError:
        await update.message.reply_text("⚠️ Por favor, ingresa un número válido para las plazas.")
        return CREAR_PLAZAS  # Vuelve a pedir el número de plazas si no es válido

    # Guardamos la nueva optativa
    optativas = cargar_optativas()  # Suponiendo que tienes una función para cargar optativas
    optativas.append(context.user_data["optativa"])  # Añadir la nueva optativa
    guardar_optativas(optativas)  # Guardamos las optativas nuevamente

    # Confirmamos la creación de la optativa
    await update.message.reply_text(f"✅ Optativa '{context.user_data['optativa']['nombre']}' creada con éxito.\nProfesor: {context.user_data['optativa']['profesor']}\nDescripción: {context.user_data['optativa']['descripcion']}\nPlazas: {context.user_data['optativa']['plazas']}")
    context.user_data.pop("optativa", None)  # Limpiamos los datos de la optativa
    return ConversationHandler.END

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
    clave = update.message.text.strip()
    usuario = context.user_data.get("usuario")
    profesor = validar_credenciales(usuario, clave)

    if profesor:
        user_id = update.effective_user.id
        usuarios_logueados.add(update.effective_user.id)
        context.user_data.clear()

        await update.message.reply_text(
            f"🔓 Bienvenido, {profesor['nombre']}!", 
            reply_markup=menu_profesor
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Credenciales incorrectas. Intenta nuevamente:")
        return LOGIN_CLAVE

# ---------- CANCELAR OPERACIÓN ----------

async def cancelar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in usuarios_logueados:
        await query.edit_message_text("❌ No tienes una sesión activa.")
        return ConversationHandler.END

    # Borrar el mensaje con el botón
    await query.message.delete()

    # Limpiar los datos del usuario
    context.user_data.clear()

    # Enviar mensaje de cancelación
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="✅ Acción cancelada.\n📋 Menú principal:",
        reply_markup=menu_profesor
    )

    # Terminar la conversación completamente
    return ConversationHandler.END

# ---------- FUNCIÓN CANCELAR CREACIÓN DE OPTATIVA ----------
async def cancelar_creacion_optativa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Limpiar los datos de la creación de optativa
    context.user_data.pop("optativa", None)  # Limpiar cualquier dato temporal relacionado con la optativa

    # Borrar el mensaje con el botón de cancelación
    await query.message.delete()

    # Enviar mensaje confirmando la cancelación
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="✅ La creación de la optativa ha sido cancelada.\n📋 Menú principal:",
        reply_markup=menu_profesor  # Reemplaza esto con el menú que deseas mostrar después de cancelar
    )

    return ConversationHandler.END  # Terminar la conversación de creación de optativa

# ---------- MENÚ DE PROFESOR ----------

async def manejar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in usuarios_logueados:
        return ConversationHandler.END  # <-- Muy importante, no solo "return"

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
    context.user_data.pop("estado", None)
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
    context.user_data.pop("estado", None)
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
    context.user_data.pop("estado", None)
    return ConversationHandler.END

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text.strip()

    estado = context.user_data.get("estado")

    # ---------- PROFESOR EN MODO OPERACIÓN ----------
    if user_id in usuarios_logueados:
        if estado == "esperando_estudiantes":
            return await recibir_estudiantes(update, context)
        elif estado == "esperando_eliminar":
            return await recibir_nombre_eliminar(update, context)
        elif estado == "esperando_asignar":
            return await recibir_asignar(update, context)

        # ---------- PROFESOR EN MENÚ ----------
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
            context.user_data["estado"] = "esperando_estudiantes"

        elif texto == "❌ Eliminar estudiante":
            await update.message.reply_text(
                "✂️ Escribe los estudiantes a eliminar en el formato:\n\n`Nombre Apellido1 Apellido2 Grupo`\nUno por línea.:",
                reply_markup=cancelar_inline
            )
            context.user_data["estado"] = "esperando_eliminar"

        elif texto == "🧹 Vaciar lista":
            guardar_estudiantes([])
            await update.message.reply_text("🗑️ Lista vaciada.")

        elif texto == "📌 Asignar optativa":
            await update.message.reply_text(
                "📥 Envía los estudiantes a asignar en el formato:\n\n`Nombre Apellido Grupo\n...\nOptativa`\n",
                parse_mode="Markdown",
                reply_markup=cancelar_inline
            )
            context.user_data["estado"] = "esperando_asignar"

        elif texto == "🔓 Cerrar sesión":
            usuarios_logueados.discard(user_id)
            context.user_data.clear()
            await update.message.reply_text("👋 Sesión cerrada.", reply_markup=ReplyKeyboardRemove())
        return

    # ---------- ESTUDIANTE ----------
    optativas = cargar_optativas()
    coincidencias_opt = [o for o in optativas if o["nombre"].lower() == texto.lower()]

    if coincidencias_opt:
        opt = coincidencias_opt[0]
        mensaje = f"📘 *{opt['nombre']}*\n👨‍🏫 Profesor: {opt['profesor']}\n📝 {opt.get('descripcion', 'Sin descripción')}"
        await update.message.reply_markdown(mensaje)
        return

    # Buscar por nombre de profesor
    profesores = {}
    for o in optativas:
        prof = o["profesor"].lower()
        profesores.setdefault(prof, []).append(o)

    if texto.lower() in profesores:
        cursos = profesores[texto.lower()]
        mensaje = f"👨‍🏫 *{cursos[0]['profesor']}* imparte:\n\n"
        for c in cursos:
            mensaje += f"• *{c['nombre']}* — {c.get('descripcion', '')}\n"
        await update.message.reply_markdown(mensaje)

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

    # ---------- Configuración del ConversationHandler ----------
    crear_optativa_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Crear optativa$"), iniciar_crear_optativa)],
        states={
            CREAR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_optativa)],
            CREAR_PROFESOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_profesor_optativa)],
            CREAR_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion_optativa)],
            CREAR_PLAZAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_plazas_optativa)],
        },
        fallbacks=[CallbackQueryHandler(cancelar_creacion_optativa_callback, pattern="^cancelar_creacion_optativa$")]
    )



    app.add_handler(CallbackQueryHandler(cancelar_callback, pattern="^cancelar$"))
    app.add_handler(crear_optativa_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))


    print("🤖 Bot corriendo...")
    app.run_polling()