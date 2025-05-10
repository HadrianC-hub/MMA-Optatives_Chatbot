import json
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def cargar_optativas():
    with open("optativas.json", "r", encoding="utf-8") as f:
        return json.load(f)

def construir_corpus(optativas):
    corpus = []
    for opt in optativas:
        texto = f"{opt['nombre']} {opt['profesor']} {opt['descripcion']} Plazas: {opt['plazas']}"
        corpus.append(texto)
    return corpus

def buscar_optativas(query):
    optativas = cargar_optativas()
    corpus = construir_corpus(optativas)

    vectorizer = TfidfVectorizer()
    matriz = vectorizer.fit_transform(corpus + [query])  # añadimos la query al final
    similitudes = cosine_similarity(matriz[-1], matriz[:-1])[0]

    resultados = sorted(zip(optativas, similitudes), key=lambda x: x[1], reverse=True)
    mejores = [opt for opt, score in resultados if score > 0][:10]
    return mejores

if __name__ == "__main__":
    consulta = " ".join(sys.argv[1:])
    resultados = buscar_optativas(consulta)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
