import json
import sys
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

# Forzar UTF-8 en stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extraer_asignaturas_con_peso(query):
    """
    Devuelve una lista de tuplas (asignatura, peso) extraídas de la query.
    Por ejemplo: "estadística***" → ("estadística", 3)
    """
    asignaturas = []
    for linea in query.strip().splitlines():
        match = re.match(r"(.+?)(\*{1,5})?$", linea.strip())
        if match:
            nombre = match.group(1).strip().lower()
            estrellas = match.group(2)
            peso = len(estrellas) if estrellas else 0
            asignaturas.append((nombre, peso))
    return asignaturas

def cargar_optativas():
    try:
        with open("data/optativas.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"No se pudo cargar optativas: {str(e)}"}))
        sys.exit(1)

def construir_corpus(optativas):
    corpus = []
    for opt in optativas:
        relacionadas = " ".join(opt.get("relacionadas", []))
        texto = f"{opt['nombre']} {opt['profesor']} {opt['descripcion']} Plazas: {opt['plazas']} {relacionadas}"
        corpus.append(texto)
    return corpus

def buscar_optativas(query, peso_base=0.1):
    optativas = cargar_optativas()
    corpus = construir_corpus(optativas)
    similitud_total = [0.0 for _ in optativas]

    # TF-IDF completo del corpus
    vectorizer = TfidfVectorizer()
    matriz = vectorizer.fit_transform(corpus)

    # Dividir tokens y clasificarlos
    tokens = re.findall(r"(!?[^\s*]+)(\*{1,5})?", query.lower())

    palabras_prohibidas = set()
    palabras_normales = []
    palabras_con_peso = []

    for palabra, estrellas in tokens:
        if palabra.startswith("!"):
            palabras_prohibidas.add(palabra[1:])
        elif estrellas:
            peso = len(estrellas)
            palabras_con_peso.append((palabra, peso))
        else:
            palabras_normales.append(palabra)

    # TF-IDF para términos normales
    for palabra in palabras_normales:
        tfidf_query = vectorizer.transform([palabra])
        similitudes = cosine_similarity(tfidf_query, matriz)[0]
        for i in range(len(similitudes)):
            similitud_total[i] += similitudes[i]

    # Términos con estrellas → score adicional
    for palabra, peso in palabras_con_peso:
        tfidf_query = vectorizer.transform([palabra])
        similitudes = cosine_similarity(tfidf_query, matriz)[0]
        for i in range(len(similitudes)):
            similitud_total[i] += similitudes[i]
        for i, opt in enumerate(optativas):
            texto_opt = f"{opt['nombre']} {opt['profesor']} {opt['descripcion']} {' '.join(opt.get('relacionadas', []))}".lower()
            if palabra in texto_opt:
                similitud_total[i] += peso_base * peso

    # ⚠️ Eliminar optativas que contengan alguna palabra prohibida
    for i, opt in enumerate(optativas):
        texto_opt = f"{opt['nombre']} {opt['profesor']} {opt['descripcion']} {' '.join(opt.get('relacionadas', []))}".lower()
        if any(palabra in texto_opt for palabra in palabras_prohibidas):
            similitud_total[i] = 0.0

    # Ordenar y devolver
    resultados = sorted(zip(optativas, similitud_total), key=lambda x: x[1], reverse=True)
    mejores = [opt for opt, score in resultados if score > 0][:10]
    return mejores

if __name__ == "__main__":
    consulta = " ".join(sys.argv[1:])
    if not consulta.strip():
        print(json.dumps({"error": "Consulta vacía."}))
        sys.exit(1)

    resultados = buscar_optativas(consulta)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
