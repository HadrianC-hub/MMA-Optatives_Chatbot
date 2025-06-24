import json
import os
import random
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import matplotlib.gridspec as gridspec
from sklearn.metrics import precision_score, recall_score, f1_score
from search_engine import buscar_optativas as search_engine_buscar
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =====================================
# CARGA DE DATOS
# =====================================

def load_optativas(path="data/optativas.json"):
    """
    Carga el archivo JSON de optativas y devuelve una lista de dicts.
    Cada dict contiene: 'nombre', 'profesor', 'descripcion', 'plazas', 'relacionadas'.

    Lanza FileNotFoundError si la ruta no existe o ValueError si el contenido no es válido.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo de optativas en: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        optativas = json.load(f)
    if not isinstance(optativas, list) or any(not all(k in opt for k in ['nombre', 'profesor', 'descripcion', 'plazas', 'relacionadas']) for opt in optativas):
        raise ValueError("El archivo de optativas debe contener una lista de diccionarios con claves 'nombre', 'profesor', 'descripcion', 'plazas' y 'relacionadas'.")
    
    # Agregar un ID único a cada optativa para facilitar las referencias
    for i, opt in enumerate(optativas):
        opt['id'] = i + 1
        
    return optativas

# =====================================
# SIMULACIÓN DE ASIGNACIONES REALES (GROUND TRUTH)
# =====================================

def simulate_real_student_choices(optativas, num_students=70):
    """
    Simula las elecciones reales de los estudiantes que usaremos como ground truth.
    
    Parámetros:
      - optativas: lista de dicts con información de optativas
      - num_students: número de estudiantes
      
    Retorna:
      - DataFrame con las elecciones reales de cada estudiante
    """
    random.seed(42)  # Semilla fija para reproducibilidad
    
    # Lista para almacenar las elecciones
    student_choices = []
    
    # Pesos basados en popularidad simulada de cada optativa
    popularities = {opt['id']: random.uniform(0.5, 2.0) for opt in optativas}
    
    # Para cada estudiante, simular elección
    for student_id in range(1, num_students + 1):
        # Crear pesos ponderados por popularidad
        weights = [popularities[opt['id']] for opt in optativas]
        
        # Normalizar pesos
        total = sum(weights)
        probabilities = [w/total for w in weights]
        
        # Seleccionar optativa
        selected_idx = np.random.choice(len(optativas), p=probabilities)
        selected_optativa = optativas[selected_idx]
        
        # Registrar elección
        student_choices.append({
            'estudiante_id': student_id,
            'optativa_id': selected_optativa['id'],
            'optativa_nombre': selected_optativa['nombre']
        })
    
    return pd.DataFrame(student_choices)

# =====================================
# SISTEMA DE RECOMENDACIÓN BASADO EN CONTENIDO
# =====================================

def generate_content_based_recommendations(optativas, num_recommendations=3):
    """
    Genera recomendaciones para cada estudiante basadas en el contenido de las optativas
    utilizando el mismo motor de búsqueda que usa el bot real.
    
    Parámetros:
      - optativas: lista de dicts con información de optativas
      - num_recommendations: número de recomendaciones por estudiante
    
    Retorna:
      - DataFrame con recomendaciones para cada estudiante
    """
    # Crear perfiles ficticios de estudiantes basados en palabras clave de interés
    student_profiles = [
        {'id': i+1, 'interests': random.sample(['programación', 'matemáticas', 'estadística', 'comunicación', 'software', 'teoría'], 
                                          k=random.randint(1, 3))} 
        for i in range(70)
    ]
    
    # Construir corpus para TF-IDF
    corpus = []
    for opt in optativas:
        texto = f"{opt['nombre']} {opt['profesor']} {opt['descripcion']} {' '.join(opt.get('relacionadas', []))}"
        corpus.append(texto)
    
    # Crear vectorizador TF-IDF
    vectorizer = TfidfVectorizer()
    matriz = vectorizer.fit_transform(corpus)
    
    recommendations = []
    
    for student in student_profiles:
        # Convertir intereses en consulta para el motor de búsqueda
        query = ' '.join(student['interests'])
        
        # Vectorizar la consulta
        query_vector = vectorizer.transform([query])
        
        # Calcular similitud de coseno con todas las optativas
        similitudes = cosine_similarity(query_vector, matriz)[0]
        
        # Crear lista de (id_optativa, score)
        scores = [(opt['id'], similitudes[i]) for i, opt in enumerate(optativas)]
        
        # Ordenar por puntuación descendente
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Tomar las top N recomendaciones
        top_recommendations = scores[:num_recommendations]
        
        # Registrar recomendaciones
        for rank, (optativa_id, score) in enumerate(top_recommendations, 1):
            opt_name = next(opt['nombre'] for opt in optativas if opt['id'] == optativa_id)
            recommendations.append({
                'estudiante_id': student['id'],
                'optativa_id': optativa_id,
                'optativa_nombre': opt_name,
                'rank': rank,
                'score': float(score)  # Convertir a float para evitar problemas con numpy.float32
            })
    
    return pd.DataFrame(recommendations)

# =====================================
# MÉTRICAS DE EVALUACIÓN
# =====================================

def evaluate_recommendations(real_choices_df, recommendations_df, optativas, output_dir="results"):
    """
    Evalúa la precisión de las recomendaciones comparándolas con las elecciones reales.
    
    Parámetros:
      - real_choices_df: DataFrame con elecciones reales de estudiantes
      - recommendations_df: DataFrame con recomendaciones generadas
      - optativas: lista de diccionarios con información de optativas
      - output_dir: directorio donde guardar resultados
      
    Retorna:
      - Dict con métricas de evaluación
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Precisión: Porcentaje de recomendaciones relevantes
    metrics = {}
    
    # Crear un DataFrame con todas las recomendaciones y elecciones reales
    evaluation_data = []
    
    for student_id in real_choices_df['estudiante_id'].unique():
        # Obtener la elección real
        real_choice = real_choices_df[real_choices_df['estudiante_id'] == student_id]['optativa_id'].iloc[0]
        
        # Obtener las recomendaciones para este estudiante
        student_recs = recommendations_df[recommendations_df['estudiante_id'] == student_id]
        recommended_ids = student_recs['optativa_id'].tolist()
        
        # Comprobar si la elección real está en las recomendaciones
        is_hit = real_choice in recommended_ids
        
        # Si está en las recomendaciones, obtener su posición
        if is_hit:
            rank = student_recs[student_recs['optativa_id'] == real_choice]['rank'].iloc[0]
        else:
            rank = None
        
        evaluation_data.append({
            'estudiante_id': student_id,
            'eleccion_real_id': real_choice,
            'eleccion_real_nombre': real_choices_df[real_choices_df['estudiante_id'] == student_id]['optativa_nombre'].iloc[0],
            'recomendaciones': recommended_ids,
            'is_hit': is_hit,
            'rank': rank
        })
    
    eval_df = pd.DataFrame(evaluation_data)
    
    # Calcular métricas
    precision_at_k = eval_df['is_hit'].mean()
    metrics['precision_at_k'] = precision_at_k
    
    # Calcular Mean Reciprocal Rank (MRR)
    mrr = (1 / eval_df[eval_df['rank'].notnull()]['rank']).mean()
    metrics['mrr'] = mrr if not pd.isna(mrr) else 0
    
    # Calcular cobertura (porcentaje de optativas que aparecen en las recomendaciones)
    unique_recommended = recommendations_df['optativa_id'].nunique()
    total_optativas = len(optativas)
    coverage = unique_recommended / total_optativas
    metrics['coverage'] = coverage
    
    # Calcular F1 Score (media armónica de precision y recall)
    # Como solo hay una elección real por estudiante, el recall es igual a la precisión
    recall = precision_at_k
    f1 = 2 * (precision_at_k * recall) / (precision_at_k + recall) if (precision_at_k + recall) > 0 else 0
    metrics['f1_score'] = f1
    
    # Guardar resultados en CSV
    eval_df.to_csv(os.path.join(output_dir, 'evaluacion_recomendaciones.csv'), index=False)
    
    # Crear y guardar tabla de métricas
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(os.path.join(output_dir, 'metricas_recomendacion.csv'), index=False)
    
    return metrics

# =====================================
# VISUALIZACIONES DE EVALUACIÓN
# =====================================

def visualize_recommendation_evaluation(real_choices_df, recommendations_df, metrics, optativas, output_dir="results"):
    """
    Genera visualizaciones para evaluar la calidad de las recomendaciones.
    
    Parámetros:
      - real_choices_df: DataFrame con elecciones reales
      - recommendations_df: DataFrame con recomendaciones
      - metrics: diccionario con métricas calculadas
      - optativas: lista de diccionarios con información de optativas
      - output_dir: directorio donde guardar visualizaciones
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Distribución de elecciones reales vs recomendaciones
    plt.figure(figsize=(14, 8))
    
    # Contar frecuencias de elecciones reales
    real_counts = real_choices_df['optativa_id'].value_counts().sort_index()
    
    # Contar frecuencias de recomendaciones en posición 1
    top1_recs = recommendations_df[recommendations_df['rank'] == 1]
    rec_counts = top1_recs['optativa_id'].value_counts().sort_index()
    
    # Crear DataFrame para visualización
    compare_df = pd.DataFrame({
        'Elecciones reales': real_counts,
        'Recomendaciones (Top-1)': rec_counts
    })
    
    # Rellenar NaN con ceros
    compare_df = compare_df.fillna(0)
    
    # Crear nombres legibles para optativas
    id_to_name = {opt['id']: opt['nombre'] for opt in optativas}
    compare_df.index = [id_to_name.get(idx, f'Optativa {idx}') for idx in compare_df.index]
    
    # Crear gráfico de barras
    compare_df.plot(kind='bar', ax=plt.gca())
    plt.title('Comparación entre elecciones reales y recomendaciones top-1')
    plt.xlabel('Optativa')
    plt.ylabel('Número de estudiantes')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'comparacion_elecciones_recomendaciones.png'), dpi=300)
    plt.close()
    
    # 2. Heatmap de coincidencia entre elecciones reales y recomendaciones
    plt.figure(figsize=(12, 10))
    
    # Crear matriz de coincidencia
    match_matrix = np.zeros((len(optativas), len(optativas)))
    
    # Para cada estudiante
    for student_id in real_choices_df['estudiante_id'].unique():
        # Obtener elección real (índice -1 para convertir a 0-based)
        real_choice = real_choices_df[real_choices_df['estudiante_id'] == student_id]['optativa_id'].iloc[0] - 1
        
        # Obtener top recomendación
        if student_id in recommendations_df['estudiante_id'].values:
            top_rec = recommendations_df[(recommendations_df['estudiante_id'] == student_id) & 
                                       (recommendations_df['rank'] == 1)]['optativa_id'].iloc[0] - 1
            
            # Incrementar contador en matriz
            match_matrix[real_choice, top_rec] += 1
    
    # Normalizar por filas (para cada elección real, distribución de recomendaciones)
    row_sums = match_matrix.sum(axis=1, keepdims=True)
    norm_matrix = np.divide(match_matrix, row_sums, out=np.zeros_like(match_matrix), where=row_sums!=0)
    
    # Crear mapa de calor
    optativa_names = [opt['nombre'] for opt in optativas]
    sns.heatmap(norm_matrix, xticklabels=optativa_names, yticklabels=optativa_names, 
                cmap='YlGnBu', annot=False)
    plt.title('Matriz de coincidencia: Elecciones reales vs. Recomendaciones')
    plt.xlabel('Recomendaciones Top-1')
    plt.ylabel('Elecciones reales')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'matriz_coincidencia.png'), dpi=300)
    plt.close()
    
    # 3. Gráfico de métricas
    plt.figure(figsize=(10, 6))
    metrics_values = [metrics['precision_at_k'], metrics['mrr'], metrics['coverage'], metrics['f1_score']]
    metrics_names = ['Precisión', 'MRR', 'Cobertura', 'F1']
    
    # Crear gráfico de barras
    plt.bar(metrics_names, metrics_values, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
    
    # Añadir etiquetas de valores
    for i, v in enumerate(metrics_values):
        plt.text(i, v + 0.02, f'{v:.3f}', ha='center', va='bottom')
    
    plt.title('Métricas de evaluación del sistema de recomendación')
    plt.ylabel('Valor')
    plt.ylim(0, 1.1)  # Todas las métricas están entre 0 y 1
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'metricas_recomendacion.png'), dpi=300)
    plt.close()
    
    # 4. Distribución de ranking de coincidencias
    plt.figure(figsize=(10, 6))
    
    # Crear DataFrame con elecciones reales y recomendaciones
    match_ranks = []
    
    for student_id in real_choices_df['estudiante_id'].unique():
        real_choice = real_choices_df[real_choices_df['estudiante_id'] == student_id]['optativa_id'].iloc[0]
        
        # Buscar en qué posición se recomendó la elección real
        student_recs = recommendations_df[recommendations_df['estudiante_id'] == student_id]
        
        if real_choice in student_recs['optativa_id'].values:
            rank = student_recs[student_recs['optativa_id'] == real_choice]['rank'].iloc[0]
            match_ranks.append(rank)
    
    if match_ranks:
        # Histograma de posiciones
        sns.histplot(match_ranks, bins=range(1, max(match_ranks)+2), discrete=True)
        plt.title('Distribución de posiciones donde se encontró la elección real')
        plt.xlabel('Posición en las recomendaciones')
        plt.ylabel('Número de estudiantes')
        plt.xticks(range(1, max(match_ranks)+1))
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'distribucion_ranks.png'), dpi=300)
    plt.close()

# =====================================
# SIMULACIÓN Y ANÁLISIS DE INFLUENCIA DE RESEÑAS
# =====================================

def simulate_review_influence(optativas, num_students=70, influence_levels=10, num_simulations=50):
    """
    Simula cómo cambian las elecciones de los estudiantes según el nivel de influencia de las reseñas.
    
    Parámetros:
      - optativas: lista de dicts con información de optativas
      - num_students: número de estudiantes por simulación
      - influence_levels: número de niveles de influencia a probar
      - num_simulations: número de simulaciones por nivel
      
    Retorna:
      - DataFrame con resultados de las simulaciones
    """
    # Generar reseñas base (iniciales) para cada optativa
    random.seed(42)
    base_ratings = {opt['id']: random.uniform(3.0, 4.5) for opt in optativas}
    
    # Generar matriz de resultados
    results = []
    
    # Simular para cada nivel de influencia
    for lvl in range(influence_levels + 1):
        influence = lvl / influence_levels  # Nivel de influencia de 0 a 1
        
        for sim in range(num_simulations):
            # Semilla específica para reproducibilidad
            seed = lvl * 1000 + sim
            np.random.seed(seed)
            random.seed(seed)
            
            # Registrar selecciones para esta simulación
            selections = {opt['id']: 0 for opt in optativas}
            ratings = {opt['id']: base_ratings[opt['id']] for opt in optativas}
            
            # Simular selecciones de estudiantes
            for student in range(num_students):
                # Calcular probabilidades basadas en calificaciones y nivel de influencia
                probs = []
                for opt in optativas:
                    # Peso intrínseco (aleatorio) de cada optativa
                    intrinsic_weight = random.uniform(0.5, 1.5)
                    
                    # Combinar peso intrínseco con calificaciones según nivel de influencia
                    weight = (1 - influence) * intrinsic_weight + influence * ratings[opt['id']]
                    probs.append(weight)
                
                # Normalizar probabilidades
                sum_probs = sum(probs)
                probs = [p / sum_probs for p in probs]
                
                # Seleccionar optativa
                selected_idx = np.random.choice(len(optativas), p=probs)
                selected_id = optativas[selected_idx]['id']
                
                # Registrar selección
                selections[selected_id] += 1
                
                # Generar nueva calificación (con ruido)
                new_rating = ratings[selected_id] + random.uniform(-0.5, 0.5)
                new_rating = max(1.0, min(5.0, new_rating))  # Limitar entre 1 y 5
                
                # Actualizar calificación (media ponderada)
                ratings[selected_id] = (ratings[selected_id] * selections[selected_id] + new_rating) / (selections[selected_id] + 1)
            
            # Calcular diversidad de selecciones (entropía)
            counts = np.array(list(selections.values()))
            probs = counts / counts.sum()
            probs = probs[probs > 0]  # Eliminar ceros
            entropy = -np.sum(probs * np.log2(probs))
            
            # Calcular concentración (Gini coefficient)
            counts_sorted = np.sort(counts)
            n = len(counts_sorted)
            index = np.arange(1, n + 1)
            gini = np.sum((2 * index - n - 1) * counts_sorted) / (n * np.sum(counts_sorted))
            
            # Guardar resultados
            result_row = {
                'nivel_influencia': influence,
                'simulacion': sim,
                'entropia': entropy,
                'gini': gini
            }
            
            # Añadir conteo por optativa
            for opt_id, count in selections.items():
                result_row[f'optativa_{opt_id}'] = count
                
            results.append(result_row)
            
    return pd.DataFrame(results)

def analyze_review_influence(df_influence, optativas, output_dir="results"):
    """
    Analiza cómo la influencia de las reseñas afecta la selección de optativas.
    Realiza pruebas de hipótesis para determinar si hay cambios significativos.
    
    Parámetros:
      - df_influence: DataFrame con resultados de simulaciones
      - optativas: lista de dicts con información de optativas
      - output_dir: directorio donde guardar resultados
      
    Retorna:
      - dict con resultados estadísticos
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Análisis de tendencia de entropía y concentración
    plt.figure(figsize=(12, 6))
    
    # Crear un grid de 1x2 para gráficos
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Gráfico 1: Entropía vs Nivel de influencia
    entropy_stats = df_influence.groupby('nivel_influencia')['entropia'].agg(['mean', 'std']).reset_index()
    ax1.errorbar(entropy_stats['nivel_influencia'], entropy_stats['mean'], 
                 yerr=entropy_stats['std'], fmt='o-', capsize=5)
    ax1.set_xlabel('Nivel de influencia de reseñas')
    ax1.set_ylabel('Entropía (diversidad de selecciones)')
    ax1.set_title('Efecto de las reseñas en la diversidad de selecciones')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Gráfico 2: Concentración (Gini) vs Nivel de influencia
    gini_stats = df_influence.groupby('nivel_influencia')['gini'].agg(['mean', 'std']).reset_index()
    ax2.errorbar(gini_stats['nivel_influencia'], gini_stats['mean'], 
                yerr=gini_stats['std'], fmt='o-', capsize=5, color='orange')
    ax2.set_xlabel('Nivel de influencia de reseñas')
    ax2.set_ylabel('Coeficiente Gini (concentración)')
    ax2.set_title('Efecto de las reseñas en la concentración de selecciones')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'tendencia_influencia_resenas.png'), dpi=300)
    plt.close()
    
    # 2. Prueba de hipótesis: ¿Hay diferencia significativa entre influencia baja y alta?
    # Comparar el primer y último nivel de influencia
    low_influence = df_influence[df_influence['nivel_influencia'] == 0]['entropia']
    high_influence = df_influence[df_influence['nivel_influencia'] == 1]['entropia']
    
    # Prueba t de Student para muestras independientes
    t_stat, p_value = stats.ttest_ind(low_influence, high_influence, equal_var=False)
    
    # 3. Análisis de regresión para cuantificar el efecto
    plt.figure(figsize=(10, 6))
    
    # Regresión lineal para entropía
    X = df_influence['nivel_influencia'].values.reshape(-1, 1)
    y_entropy = df_influence['entropia'].values
    
    # Ajustar modelo de regresión
    modelo_entropy = stats.linregress(df_influence['nivel_influencia'], df_influence['entropia'])
    
    # Visualizar datos y regresión
    plt.scatter(df_influence['nivel_influencia'], df_influence['entropia'], 
                alpha=0.3, color='blue', label='Observaciones (Entropía)')
    
    # Línea de regresión
    x_line = np.array([0, 1])
    y_line_entropy = modelo_entropy.slope * x_line + modelo_entropy.intercept
    plt.plot(x_line, y_line_entropy, 'b-', 
             label=f'Regresión Entropía: β = {modelo_entropy.slope:.4f} (p={modelo_entropy.pvalue:.4f})')
    
    # Regresión lineal para Gini
    y_gini = df_influence['gini'].values
    modelo_gini = stats.linregress(df_influence['nivel_influencia'], df_influence['gini'])
    
    plt.scatter(df_influence['nivel_influencia'], df_influence['gini'], 
                alpha=0.3, color='orange', label='Observaciones (Gini)')
    
    # Línea de regresión
    y_line_gini = modelo_gini.slope * x_line + modelo_gini.intercept
    plt.plot(x_line, y_line_gini, 'orange', 
             label=f'Regresión Gini: β = {modelo_gini.slope:.4f} (p={modelo_gini.pvalue:.4f})')
    
    plt.title('Análisis de regresión: Efecto de las reseñas en la distribución de selecciones')
    plt.xlabel('Nivel de influencia de reseñas')
    plt.ylabel('Medidas de distribución')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'regresion_influencia_resenas.png'), dpi=300)
    plt.close()
    
    # 4. Análisis de distribución de selecciones
    # Seleccionar solo niveles extremos para comparar
    df_low = df_influence[df_influence['nivel_influencia'] == 0]
    df_high = df_influence[df_influence['nivel_influencia'] == 1]
    
    # Calcular selecciones promedio por optativa
    opt_cols = [col for col in df_influence.columns if col.startswith('optativa_')]
    
    # Crear dataframe para comparación
    comparison_data = []
    
    for col in opt_cols:
        opt_id = int(col.split('_')[1])
        opt_name = next(opt['nombre'] for opt in optativas if opt['id'] == opt_id)
        
        low_avg = df_low[col].mean()
        high_avg = df_high[col].mean()
        change_pct = ((high_avg - low_avg) / low_avg) * 100 if low_avg > 0 else 0
        
        # Realizar prueba t para cada optativa
        t_stat_opt, p_value_opt = stats.ttest_ind(df_low[col], df_high[col], equal_var=False)
        
        comparison_data.append({
            'optativa_id': opt_id,
            'optativa_nombre': opt_name,
            'promedio_sin_influencia': low_avg,
            'promedio_con_influencia': high_avg,
            'cambio_porcentual': change_pct,
            't_statistic': t_stat_opt,
            'p_value': p_value_opt,
            'significativo': p_value_opt < 0.05
        })
    
    # Convertir a DataFrame y ordenar por cambio porcentual
    df_comparison = pd.DataFrame(comparison_data)
    df_comparison = df_comparison.sort_values('cambio_porcentual', ascending=False)
    
    # Guardar comparación en CSV
    df_comparison.to_csv(os.path.join(output_dir, 'comparacion_influencia_resenas.csv'), index=False)
    
    # 5. Visualizar cambios por optativa
    plt.figure(figsize=(14, 8))
    
    # Seleccionar las 10 optativas con mayor cambio absoluto (positivo o negativo)
    df_plot = df_comparison.copy()
    df_plot['cambio_abs'] = np.abs(df_plot['cambio_porcentual'])
    df_plot = df_plot.sort_values('cambio_abs', ascending=False).head(10)
    
    # Ordenar por cambio porcentual para el gráfico
    df_plot = df_plot.sort_values('cambio_porcentual')
    
    # Crear nombres cortos para el eje y
    df_plot['nombre_corto'] = df_plot['optativa_nombre'].apply(lambda x: x[:30] + '...' if len(x) > 30 else x)
    
    # Gráfico de barras horizontales
    bars = plt.barh(df_plot['nombre_corto'], df_plot['cambio_porcentual'], color=[
        'green' if x > 0 else 'red' for x in df_plot['cambio_porcentual']
    ])
    
    # Añadir etiquetas a las barras
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width if width >= 0 else width - 10
        plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.1f}%', 
                 va='center', ha='left' if width >= 0 else 'right')
    
    plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    plt.xlabel('Cambio porcentual en selecciones (%)')
    plt.ylabel('Optativa')
    plt.title('Cambio en la selección de optativas debido a la influencia de las reseñas', fontsize=14, fontweight='bold')
    plt.legend([plt.Rectangle((0,0),1,1,fc='darkgreen'), 
               plt.Rectangle((0,0),1,1,fc='lightgreen'),
               plt.Rectangle((0,0),1,1,fc='darkred'),
               plt.Rectangle((0,0),1,1,fc='lightcoral')],
              ['Aumento significativo', 'Aumento no significativo', 
               'Disminución significativa', 'Disminución no significativa'],
              loc='lower right')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cambio_seleccion_optativas.png'), dpi=300)
    plt.close()
    
    # Calcular error estándar para cada optativa
    std_errors = []
    for _, row in df_plot.iterrows():
        opt_id = row['optativa_id']
        col = f'optativa_{opt_id}'
        low_std = df_low[col].std()
        high_std = df_high[col].std()
        # Error estándar del cambio porcentual (aproximado)
        std_error = np.sqrt((low_std**2 + high_std**2)) / row['promedio_sin_influencia'] * 100 if row['promedio_sin_influencia'] > 0 else 0
        std_errors.append(std_error)
    
    df_plot['error_std'] = std_errors
    
    # Retornar resultados de las pruebas
    return {
        'p_value_global': p_value,
        'effect_entropy': modelo_entropy.slope,
        'p_value_entropy': modelo_entropy.pvalue,
        'effect_gini': modelo_gini.slope,
        'p_value_gini': modelo_gini.pvalue,
        'optativas_significativas': df_comparison[df_comparison['significativo']].shape[0],
        'total_optativas': len(opt_cols)
    }

# =====================================
# EJECUCIÓN PRINCIPAL
# =====================================

def main():
    parser = argparse.ArgumentParser(description="Evaluación de sistemas de recomendación y análisis de influencia de reseñas.")
    parser.add_argument('--optativas', type=str, default='data/optativas.json', help='Ruta al JSON de optativas')
    parser.add_argument('--students', type=int, default=70, help='Número de estudiantes')
    parser.add_argument('--top_n', type=int, default=3, help='Número de recomendaciones por estudiante')
    parser.add_argument('--sims_infl', type=int, default=50, help='Número de simulaciones con influencia')
    parser.add_argument('--levels', type=int, default=10, help='Niveles de influencia (discretos)')
    parser.add_argument('--output_dir', type=str, default='results', help='Directorio donde guardar resultados')
    args = parser.parse_args()

    # Cargar optativas
    optativas = load_optativas(args.optativas)
    
    # 1. ANÁLISIS DE RECOMENDACIONES
    print("\n=== ANÁLISIS DE SISTEMAS DE RECOMENDACIÓN ===")
    
    # Simular elecciones reales de estudiantes (ground truth)
    print("Simulando elecciones reales de estudiantes...")
    real_choices_df = simulate_real_student_choices(optativas, num_students=args.students)
    
    # Generar recomendaciones
    print("Generando recomendaciones basadas en contenido...")
    recommendations_df = generate_content_based_recommendations(optativas, num_recommendations=args.top_n)
    
    # Evaluar recomendaciones
    print("Evaluando calidad de las recomendaciones...")
    metrics = evaluate_recommendations(real_choices_df, recommendations_df, optativas, output_dir=args.output_dir)
    
    # Generar visualizaciones
    print("Generando visualizaciones de evaluación...")
    visualize_recommendation_evaluation(real_choices_df, recommendations_df, metrics, optativas, output_dir=args.output_dir)
    
    # Guardar datos
    os.makedirs(args.output_dir, exist_ok=True)
    real_choices_df.to_csv(os.path.join(args.output_dir, "elecciones_reales.csv"), index=False)
    recommendations_df.to_csv(os.path.join(args.output_dir, "recomendaciones.csv"), index=False)
    
    print(f"Resultados de la evaluación de recomendaciones:")
    print(f"Precisión: {metrics['precision_at_k']:.3f}")
    print(f"MRR: {metrics['mrr']:.3f}")
    print(f"Cobertura: {metrics['coverage']:.3f}")
    print(f"F1 Score: {metrics['f1_score']:.3f}")
    
    # 2. ANÁLISIS DE INFLUENCIA DE RESEÑAS
    print("\n=== ANÁLISIS DE INFLUENCIA DE RESEÑAS EN SELECCIÓN DE OPTATIVAS ===")
    
    # Simulación con diferentes niveles de influencia
    print("Simulando cómo las reseñas influyen en las decisiones de los estudiantes...")
    df_influence = simulate_review_influence(optativas, num_students=args.students,
                                           influence_levels=args.levels,
                                           num_simulations=args.sims_infl)
    df_influence.to_csv(os.path.join(args.output_dir, "simulaciones_influencia.csv"), index=False)
    
    # Análisis estadístico de la influencia
    print("Realizando pruebas de hipótesis sobre el efecto de las reseñas...")
    stats_influence = analyze_review_influence(df_influence, optativas, output_dir=args.output_dir)
    
    print(f"\nResultados de la prueba de hipótesis sobre influencia de reseñas:")
    print(f"P-valor (diferencia global): {stats_influence['p_value_global']:.4f}")
    sig_global = "SÍ" if stats_influence['p_value_global'] < 0.05 else "NO"
    print(f"¿Hay efecto significativo global?: {sig_global}")
    print(f"Efecto en diversidad (entropía): {stats_influence['effect_entropy']:.4f}, p={stats_influence['p_value_entropy']:.4f}")
    print(f"Efecto en concentración (Gini): {stats_influence['effect_gini']:.4f}, p={stats_influence['p_value_gini']:.4f}")
    print(f"Optativas con cambios significativos: {stats_influence['optativas_significativas']} de {stats_influence['total_optativas']}")
    
    print(f"\nTodos los resultados y visualizaciones guardados en: {args.output_dir}")

if __name__ == "__main__":
    main()
