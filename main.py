# region Imports

import json
import os
import subprocess
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters,
)

# end region
# region Constantes

TOKEN = '8024056515:AAF5hkA6X24P6ivtc2GG0nTZPUZ6xj8xPs0'    # Token del bot generado con BotFather
usuarios_logueados = set()
LOGIN_USUARIO, LOGIN_CLAVE, ESPERAR_ESTUDIANTES, ESPERAR_NOMBRE_ELIMINAR, ESPERAR_ASIGNAR = range(5)
ESTUDIANTES_FILE = "data/estudiantes.json"
OPTATIVAS_FILE = "data/optativas.json"
PROFESORES_FILE = "data/profesores.json"

# ---------- TECLADO ESPECIAL PARA PROFESORES ----------
menu_profesor = ReplyKeyboardMarkup([
    [KeyboardButton("👥 Ver estudiantes"), KeyboardButton("➕ Agregar estudiantes"), KeyboardButton("❌ Eliminar estudiante")],
    [KeyboardButton("📚 Ver optativas"), KeyboardButton("➕ Crear optativa"), KeyboardButton("🗑️ Eliminar optativas")],
    [KeyboardButton("👨‍🏫 Ver profesores"), KeyboardButton("➕ Agregar profesores"), KeyboardButton("❌ Eliminar profesores")],
    [KeyboardButton("📌 Asignar optativa"), KeyboardButton("🔓 Cerrar sesión")]
], resize_keyboard=True)

# ---------- BOTONES DE CANCELAR INLINE ----------
cancelar_inline = InlineKeyboardMarkup([
    [InlineKeyboardButton("❎ Cancelar", callback_data="cancelar")]
])

cancelar_creacion_optativa_inline = InlineKeyboardMarkup([
    [InlineKeyboardButton("❎ Cancelar Creación de Optativa", callback_data="cancelar_creacion_optativa")]
])

# end region
# region Carga de datos

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

def cargar_profesores():
    try:
        with open(PROFESORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# end region
# region Salva de datos

def guardar_estudiantes(estudiantes):
    with open(ESTUDIANTES_FILE, "w", encoding="utf-8") as f:
        json.dump(estudiantes, f, indent=4, ensure_ascii=False)

def guardar_optativas(optativas):
    with open(OPTATIVAS_FILE, "w", encoding="utf-8") as file:
        json.dump(optativas, file, indent=4)

def guardar_profesores(profesores):
    with open(PROFESORES_FILE, "w", encoding="utf-8") as f:
        json.dump(profesores, f, indent=4, ensure_ascii=False)

# end region
# region Comandos principales

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    optativos = cargar_optativas()  # Cargar las optativas desde el archivo
    texto = "📚 *Cursos optativos disponibles:*\n\n"
    for curso in optativos:
        plazas = curso.get('plazas', 'No disponible')
        plazas_str = "ilimitadas" if plazas == -1 else plazas
        texto += f"• *{curso['nombre']}* (Prof: {curso['profesor']}, Plazas: {plazas_str})\n"
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
        usuarios_logueados.add(user_id)

        # Guardar datos útiles
        context.user_data["usuario"] = profesor["usuario"]
        context.user_data["nombre"] = profesor["nombre"]
        context.user_data["es_superadmin"] = profesor["usuario"] == "superadmin"

        await update.message.reply_text(
            f"🔓 Bienvenido, {profesor['nombre']}!", 
            reply_markup=menu_profesor
        )
        return ConversationHandler.END
    else:
        context.user_data.pop("usuario", None)  # Limpiar el usuario
        await update.message.reply_text("❌ Credenciales incorrectas. Vuelve a introducir tu usuario con /login.")
        return ConversationHandler.END

def validar_credenciales(usuario, clave):
    if usuario == "superadmin" and clave == "spr1234":
        return {"usuario": "superadmin", "nombre": "SuperAdmin"}
    profesores = cargar_profesores()
    for prof in profesores:
        if prof["usuario"] == usuario and prof["clave"] == clave:
            return prof  # Devuelve el objeto completo
    return None

# end region
# region Funciones de cancelación

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

    # Preservar datos importantes
    usuario = context.user_data.get("usuario")
    nombre = context.user_data.get("nombre")
    es_superadmin = context.user_data.get("es_superadmin")

    # Limpiar solo datos temporales
    context.user_data.clear()

    # Restaurar los datos importantes
    context.user_data["usuario"] = usuario
    context.user_data["nombre"] = nombre
    context.user_data["es_superadmin"] = es_superadmin

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

# end region
# region Manejo de optativas

# ---------- CREACIÓN DE OPTATIVAS ----------

# Estados de la conversación
CREAR_NOMBRE, CREAR_PROFESOR, CREAR_DESCRIPCION, CREAR_PLAZAS = range(4)

# Función para iniciar la creación de optativa
async def iniciar_crear_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Vamos a crear una nueva optativa.\n\nPor favor, ingresa el nombre de la optativa:",
        reply_markup=cancelar_creacion_optativa_inline  # Usar el nuevo botón de cancelación
    )
    return CREAR_NOMBRE

# Estados de la conversación
async def recibir_nombre_optativa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    
    # Cargar optativas existentes
    with open(OPTATIVAS_FILE, "r", encoding="utf-8") as f:
        optativas = json.load(f)
    
    # Verificar si ya existe una optativa con ese nombre
    if any(optativa["nombre"].lower() == nombre.lower() for optativa in optativas):
        await update.message.reply_text("⚠️ Ya existe una optativa con ese nombre. Por favor, elige uno diferente.")
        return CREAR_NOMBRE

    # Guardar nombre temporalmente
    context.user_data["optativa"] = {"nombre": nombre}
    await update.message.reply_text("✏️ Ahora ingresa el nombre del profesor que impartirá la optativa:")
    return CREAR_PROFESOR

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
        if plazas < 0:
            plazas = -1  # Capacidad ilimitada
        context.user_data["optativa"]["plazas"] = plazas
    except ValueError:
        await update.message.reply_text("⚠️ Por favor, ingresa un número válido para las plazas.")
        return CREAR_PLAZAS  # Vuelve a pedir el número de plazas si no es válido

    # Guardamos la nueva optativa
    optativas = cargar_optativas()
    optativas.append(context.user_data["optativa"])
    guardar_optativas(optativas)

    texto_plazas = "Ilimitadas" if plazas == -1 else str(plazas)

    await update.message.reply_text(
        f"✅ Optativa '{context.user_data['optativa']['nombre']}' creada con éxito.\n"
        f"Profesor: {context.user_data['optativa']['profesor']}\n"
        f"Descripción: {context.user_data['optativa']['descripcion']}\n"
        f"Plazas: {texto_plazas}"
    )
    context.user_data.pop("optativa", None)
    return ConversationHandler.END

# ---------- ELIMINACIÓN DE OPTATIVAS ----------

ELIMINAR_OPTATIVAS = range(1)

async def iniciar_eliminar_optativas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗑️ Envía los nombres de las optativas que deseas eliminar, uno por línea:",
        reply_markup=cancelar_inline
    )
    return ELIMINAR_OPTATIVAS

async def procesar_eliminar_optativas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    nombres_a_eliminar = [line.strip() for line in texto.splitlines() if line.strip()]

    optativas = cargar_optativas()
    nombres_existentes = {opt["nombre"] for opt in optativas}

    if texto == "TODO":
        guardar_optativas([])

        estudiantes = cargar_estudiantes()
        for est in estudiantes:
            est["optativa"] = ""
        guardar_estudiantes(estudiantes)

        await update.message.reply_text("🗑️ Todas las optativas han sido eliminadas y los estudiantes desasignados.")
        return ConversationHandler.END

    eliminadas = []
    no_encontradas = []

    for nombre in nombres_a_eliminar:
        if nombre in nombres_existentes:
            optativas = [opt for opt in optativas if opt["nombre"] != nombre]
            eliminadas.append(nombre)
        else:
            no_encontradas.append(nombre)

    guardar_optativas(optativas)

    # Desasignar estudiantes que tenían alguna optativa eliminada
    if eliminadas:
        estudiantes = cargar_estudiantes()
        for est in estudiantes:
            if est["optativa"] in eliminadas:
                est["optativa"] = ""
        guardar_estudiantes(estudiantes)

    mensaje = ""
    if eliminadas:
        mensaje += "✅ Optativas eliminadas:\n" + "\n".join(f"• {n}" for n in eliminadas) + "\n"
    if no_encontradas:
        mensaje += "\n⚠️ No se encontraron:\n" + "\n".join(f"• {n}" for n in no_encontradas)

    if not mensaje:
        mensaje = "⚠️ No se procesó ninguna entrada válida."

    await update.message.reply_text(mensaje, reply_markup=menu_profesor)
    return ConversationHandler.END


# ---------- VISUALIZACIÓN DE OPTATIVAS ----------

async def ver_optativas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    optativas = cargar_optativas()

    if not optativas:
        await update.message.reply_text("📭 No hay optativas registradas.")
        return

    mensaje = "📚 *Listado de Optativas:*\n\n"
    for i, opt in enumerate(optativas, 1):
        plazas = "Ilimitadas" if opt.get("plazas") == -1 else opt.get("plazas")
        mensaje += (
            f"🔹 *{i}. {opt.get('nombre')}*\n"
            f"   👨‍🏫 Profesor: {opt.get('profesor')}\n"
            f"   📝 Descripción: {opt.get('descripcion')}\n"
            f"   👥 Plazas: {plazas}\n\n"
        )

    await update.message.reply_text(mensaje, parse_mode="Markdown")

# end region
# region Funciones de profesor

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

    if texto == "TODO":
        guardar_estudiantes([])
        await update.message.reply_text("🗑️ Todos los estudiantes han sido eliminados.")
        context.user_data.pop("estado", None)
        return ConversationHandler.END

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
    optativas = cargar_optativas()
    asignados = 0
    errores = []

    bloque_actual = []
    optativa_actual = None

    for linea in lineas + [""]:  # Agregamos línea vacía para procesar el último bloque
        linea = linea.strip()
        if not linea:
            continue

        if linea.startswith("-"):
            nombre_optativa = linea[1:].strip()
            optativa = next((o for o in optativas if o["nombre"].lower() == nombre_optativa.lower()), None)

            if not optativa:
                errores.append(f"❌ Optativa no encontrada: {nombre_optativa}")
                bloque_actual = []
                optativa_actual = None
                continue

            # Procesar estudiantes del bloque anterior
            for est_linea in bloque_actual:
                est_partes = est_linea.strip().split()
                if len(est_partes) < 4:
                    errores.append(f"❌ Formato inválido: {est_linea}")
                    continue

                nombre = " ".join(est_partes[:-1])
                grupo = est_partes[-1]

                estudiante = next((e for e in estudiantes if e["nombre"] == nombre and e["grupo"] == grupo), None)
                if not estudiante:
                    errores.append(f"❌ Estudiante no encontrado: {nombre} ({grupo})")
                    continue

                if estudiante["optativa"] == optativa["nombre"]:
                    continue  # Ya asignado a esta optativa

                # Verificar plazas disponibles
                if optativa["plazas"] != -1:
                    asignados_actuales = sum(1 for e in estudiantes if e["optativa"] == optativa["nombre"])
                    if asignados_actuales >= optativa["plazas"]:
                        errores.append(f"🚫 Sin plazas: {nombre} → {optativa['nombre']}")
                        continue
                    optativa["plazas"] -= 1

                # Liberar plaza de optativa anterior si corresponde
                if estudiante["optativa"]:
                    opt_anterior = next((o for o in optativas if o["nombre"] == estudiante["optativa"]), None)
                    if opt_anterior and opt_anterior["plazas"] != -1:
                        opt_anterior["plazas"] += 1

                estudiante["optativa"] = optativa["nombre"]
                asignados += 1

            bloque_actual = []
            optativa_actual = optativa
        else:
            bloque_actual.append(linea)

    guardar_estudiantes(estudiantes)
    guardar_optativas(optativas)

    respuesta = f"✅ {asignados} estudiante(s) asignado(s).\n"
    if errores:
        respuesta += "\n⚠️ Errores:\n" + "\n".join(errores)
    await update.message.reply_text(respuesta)
    context.user_data.pop("estado", None)
    return ConversationHandler.END

async def ver_profesores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profesores = cargar_profesores()
    profesores = [p for p in profesores if p["usuario"] != "admin"]

    if not profesores:
        await update.message.reply_text("📭 No hay profesores registrados.")
        return

    mensaje = "👨‍🏫 *Lista de profesores:*\n\n"
    for prof in profesores:
        mensaje += f"• *{prof['nombre']}* — Usuario: `{prof['usuario']}`\n"
    await update.message.reply_markdown(mensaje)

async def recibir_agregar_profesores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("usuario") != "superadmin":
        await update.message.reply_text("❌ Solo el superadmin puede agregar profesores.")
        return ConversationHandler.END

    texto = update.message.text.strip()
    lineas = texto.split("\n")
    profesores = cargar_profesores()
    nuevos = 0
    duplicados = []

    for linea in lineas:
        partes = linea.strip().split()
        if len(partes) < 3:
            continue
        usuario = partes[0]
        clave = partes[1]
        nombre = " ".join(partes[2:])

        if any(p["usuario"] == usuario for p in profesores):
            duplicados.append(usuario)
            continue

        profesores.append({"usuario": usuario, "clave": clave, "nombre": nombre})
        nuevos += 1

    guardar_profesores(profesores)

    respuesta = f"✅ {nuevos} profesor(es) agregado(s).\n"
    if duplicados:
        respuesta += "\n⚠️ Usuarios duplicados (no agregados):\n" + "\n".join(duplicados)
    await update.message.reply_markdown(respuesta)
    context.user_data.pop("estado", None)
    return ConversationHandler.END

async def recibir_eliminar_profesores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("usuario") != "superadmin":
        await update.message.reply_text("❌ Solo el superadmin puede eliminar profesores.")
        return ConversationHandler.END

    texto = update.message.text.strip()
    lineas = texto.split("\n")
    profesores = cargar_profesores()
    eliminados = 0
    no_encontrados = []

    for usuario in lineas:
        usuario = usuario.strip()
        if usuario == "admin":
            continue
        original_len = len(profesores)
        profesores = [p for p in profesores if p["usuario"] != usuario]
        if len(profesores) == original_len:
            no_encontrados.append(usuario)
        else:
            eliminados += 1

    guardar_profesores(profesores)

    respuesta = f"✅ {eliminados} profesor(es) eliminado(s).\n"
    if no_encontrados:
        respuesta += "\n⚠️ No encontrados:\n" + "\n".join(no_encontrados)
    await update.message.reply_markdown(respuesta)
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
        elif estado == "esperando_agregar_profesores":
            return await recibir_agregar_profesores(update, context)
        elif estado == "esperando_eliminar_profesores":
            return await recibir_eliminar_profesores(update, context)

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

        elif texto == "📌 Asignar optativa":
            await update.message.reply_text(
                "📥 Envía los estudiantes a asignar en el formato:\n\n`Nombre Apellido1 Apellido2 Grupo\nNombre Apellido1 Apellido2 Grupo\n...\n-Optativa`\n",
                parse_mode="Markdown",
                reply_markup=cancelar_inline
            )
            context.user_data["estado"] = "esperando_asignar"

        elif texto == "🔓 Cerrar sesión":
            usuarios_logueados.discard(user_id)
            context.user_data.clear()
            await update.message.reply_text("👋 Sesión cerrada.", reply_markup=ReplyKeyboardRemove())

        elif texto == "👨‍🏫 Ver profesores":
            return await ver_profesores(update, context)

        elif texto == "➕ Agregar profesores":
            if context.user_data.get("usuario") != "superadmin":
                await update.message.reply_text("❌ Solo el superadmin puede agregar profesores.")
                return
            await update.message.reply_text(
                "📨 Envía los profesores en el formato:\n\n`usuario clave Nombre Apellido`",
                parse_mode="Markdown",
                reply_markup=cancelar_inline
            )
            context.user_data["estado"] = "esperando_agregar_profesores"

        elif texto == "❌ Eliminar profesores":
            if context.user_data.get("usuario") != "superadmin":
                await update.message.reply_text("❌ Solo el superadmin puede eliminar profesores.")
                return
            await update.message.reply_text(
                "🗑️ Escribe los usuarios de los profesores a eliminar, uno por línea.",
                reply_markup=cancelar_inline
            )
            context.user_data["estado"] = "esperando_eliminar_profesores"

        return

    return await consulta_estudiante(update, context)

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

# end region
# region Manejo de consultas

async def consulta_estudiante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().lower()
    profesores = cargar_profesores()

    # Buscar si corresponde a un profesor
    for prof in profesores:
        if prof["nombre"].lower() == texto:
            usuario = prof["usuario"]
            optativas = [opt for opt in cargar_optativas() if opt["profesor"] == prof["nombre"]]

            mensaje = f"👨‍🏫 *Usuario:* `{usuario}`\n📚 *Optativas que imparte:*"
            if optativas:
                for opt in optativas:
                    mensaje += f"\n• *{opt['nombre']}* - {opt['descripcion']}"
            else:
                mensaje += "\n(No imparte ninguna optativa)"
            await update.message.reply_markdown(mensaje)
            return

    # Si no es profesor, buscar por modelo vectorial
    ruta_script = os.path.join(os.path.dirname(__file__), "search_engine.py")

    resultado = subprocess.run(
        ["python", ruta_script, texto],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    try:
        optativas = json.loads(resultado.stdout)
        if not optativas:
            await update.message.reply_text("🔍 No se encontraron optativas relacionadas.")
            return

        mensaje = "🔍 *Resultados más relevantes:*\n\n"
        for opt in optativas:
            mensaje += f"• *{opt['nombre']}* (Prof: {opt['profesor']})\n  _{opt['descripcion']}_\n\n"
        await update.message.reply_markdown(mensaje)
    except Exception as e:
        await update.message.reply_text("❌ Error procesando la consulta.")
        print("Error:", e)




# end region
# region Handlers

login_conv = ConversationHandler(
    entry_points=[CommandHandler("login", login)],
    states={
        LOGIN_USUARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_usuario)],
        LOGIN_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_clave)],
    },
    fallbacks=[]
)

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

eliminar_optativas_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🗑️ Eliminar optativas$"), iniciar_eliminar_optativas)],
    states={
        ELIMINAR_OPTATIVAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_eliminar_optativas)],
    },
    fallbacks=[CallbackQueryHandler(cancelar_callback, pattern="^cancelar$")]
)

# end region
# region Ejecución principal

if __name__ == "__main__":

    # Construcción de la app mediante el token
    app = ApplicationBuilder().token(TOKEN).build()

    # Agregando handlers
    app.add_handler(MessageHandler(filters.Regex("^📚 Ver optativas$"), ver_optativas))
    app.add_handler(eliminar_optativas_handler)
    app.add_handler(CallbackQueryHandler(cancelar_callback, pattern="^cancelar$"))
    app.add_handler(crear_optativa_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    print("🤖 Bot corriendo...")
    app.run_polling()