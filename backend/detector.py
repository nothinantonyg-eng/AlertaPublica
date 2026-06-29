import pandas as pd
import sqlite3
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

DB_PATH = "../data/alertapublica.db"

def cargar_contratos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM contratos", conn)
    conn.close()
    return df

def detectar_anomalias_monto(df):
    print("\n=== DETECTOR 1: Anomalías de monto (Isolation Forest) ===")
    
    df_valid = df[
        df["monto_adjudicado"].notna() & 
        df["monto_referencial"].notna() &
        (df["monto_adjudicado"] > 0) &
        (df["monto_referencial"] > 0)
    ].copy()
    
    # Reemplazar infinitos y NaN antes de escalar
    df_valid["diferencia_pct"] = df_valid["diferencia_pct"].replace(
        [float('inf'), float('-inf')], 0
    ).fillna(0)
    
    features = df_valid[["monto_adjudicado", "monto_referencial", "diferencia_pct"]]
    
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    model = IsolationForest(contamination=0.05, random_state=42)
    df_valid["anomalia_monto"] = model.fit_predict(features_scaled)
    df_valid["score_monto"] = model.score_samples(features_scaled)
    
    anomalias = df_valid[df_valid["anomalia_monto"] == -1].copy()
    print(f"Contratos anómalos detectados: {len(anomalias)}")
    print(f"Monto promedio de anómalos: S/ {anomalias['monto_adjudicado'].mean():,.0f}")
    
    return df_valid, anomalias

def detectar_proveedor_dominante(df):
    """
    Regla heurística: proveedor que gana más del 60%
    de contratos de una entidad — posible captura
    """
    print("\n=== DETECTOR 2: Proveedores dominantes ===")
    
    # Contratos por entidad
    total_por_entidad = df.groupby("codigoentidad").size().reset_index(name="total")
    
    # Contratos por entidad + proveedor
    por_proveedor = df.groupby(
        ["codigoentidad", "entidad", "ruc_proveedor", "proveedor"]
    ).size().reset_index(name="contratos_proveedor")
    
    merged = por_proveedor.merge(total_por_entidad, on="codigoentidad")
    merged["pct_contratos"] = (
        merged["contratos_proveedor"] / merged["total"] * 100
    ).round(1)
    
    # Filtrar: más del 60% Y al menos 3 contratos
    dominantes = merged[
        (merged["pct_contratos"] >= 60) & 
        (merged["contratos_proveedor"] >= 3)
    ].sort_values("pct_contratos", ascending=False)
    
    print(f"Relaciones proveedor-entidad sospechosas: {len(dominantes)}")
    if len(dominantes) > 0:
        print(dominantes[["entidad", "proveedor", 
                          "contratos_proveedor", "pct_contratos"]].head(5).to_string())
    
    return dominantes

def detectar_proceso_rapido(df):
    """
    Regla heurística: procesos cerrados en menos de 5 días
    — posible adjudicación dirigida
    """
    print("\n=== DETECTOR 3: Procesos sospechosamente rápidos ===")
    
    rapidos = df[
        df["dias_proceso"].notna() & 
        (df["dias_proceso"] <= 5) &
        (df["dias_proceso"] >= 0) &
        (df["monto_adjudicado"] > 50000)
    ].copy()
    
    rapidos = rapidos.sort_values("monto_adjudicado", ascending=False)
    
    print(f"Contratos de alto monto cerrados en ≤5 días: {len(rapidos)}")
    if len(rapidos) > 0:
        print(rapidos[["entidad", "proveedor", "monto_adjudicado", 
                       "dias_proceso"]].head(5).to_string())
    
    return rapidos

def detectar_diferencia_monto(df):
    """
    Regla heurística: monto adjudicado muy diferente
    al monto referencial — posible sobrevaluación
    """
    print("\n=== DETECTOR 4: Diferencia monto referencial vs adjudicado ===")
    
    sospechosos = df[
        df["diferencia_pct"].notna() &
        (df["diferencia_pct"].abs() > 30) &
        (df["monto_adjudicado"] > 100000)
    ].copy()
    
    sospechosos = sospechosos.sort_values("diferencia_pct", ascending=False)
    
    print(f"Contratos con diferencia >30% en monto: {len(sospechosos)}")
    if len(sospechosos) > 0:
        print(sospechosos[["entidad", "proveedor", "monto_referencial",
                           "monto_adjudicado", "diferencia_pct"]].head(5).to_string())
    
    return sospechosos

def calcular_score_riesgo(df, anomalias_if, dominantes, rapidos, diferencias):
    """
    Score de riesgo compuesto 0-100 para cada contrato
    """
    print("\n=== CALCULANDO SCORE DE RIESGO COMPUESTO ===")
    
    df["score_riesgo"] = 0
    
    # +40 puntos si Isolation Forest lo marca como anómalo
    if len(anomalias_if) > 0:
        idx_anomalos = anomalias_if.index
        df.loc[df.index.isin(idx_anomalos), "score_riesgo"] += 40
    
    # +30 puntos si el proveedor es dominante en esa entidad
    if len(dominantes) > 0:
        pares_sospechosos = set(
            zip(dominantes["codigoentidad"], dominantes["ruc_proveedor"])
        )
        mask = df.apply(
            lambda r: (r["codigoentidad"], r["ruc_proveedor"]) in pares_sospechosos, 
            axis=1
        )
        df.loc[mask, "score_riesgo"] += 30
    
    # +20 puntos si el proceso fue muy rápido
    if len(rapidos) > 0:
        df.loc[df.index.isin(rapidos.index), "score_riesgo"] += 20
    
    # +10 puntos si hay gran diferencia de montos
    if len(diferencias) > 0:
        df.loc[df.index.isin(diferencias.index), "score_riesgo"] += 10
    
    alertas = df[df["score_riesgo"] >= 40].sort_values(
        "score_riesgo", ascending=False
    )
    
    print(f"Contratos con score_riesgo >= 40: {len(alertas)}")
    print(f"Contratos con score_riesgo = 100 (máximo): {len(df[df['score_riesgo'] == 100])}")
    
    return df, alertas

def guardar_alertas(df_scored, alertas):
    conn = sqlite3.connect(DB_PATH)
    df_scored.to_sql("contratos_scored", conn, if_exists="replace", index=False)
    alertas.to_sql("alertas", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"\n✅ Alertas guardadas en SQLite: {len(alertas)} contratos sospechosos")

if __name__ == "__main__":
    df = cargar_contratos()
    
    df_scored, anomalias_if = detectar_anomalias_monto(df)
    dominantes = detectar_proveedor_dominante(df)
    rapidos = detectar_proceso_rapido(df)
    diferencias = detectar_diferencia_monto(df)
    
    df_final, alertas = calcular_score_riesgo(
        df_scored, anomalias_if, dominantes, rapidos, diferencias
    )
    
    guardar_alertas(df_final, alertas)
    
    print("\n=== RESUMEN FINAL ===")
    print(f"Total contratos analizados: {len(df)}")
    print(f"Total alertas generadas: {len(alertas)}")
    print(f"Porcentaje sospechoso: {len(alertas)/len(df)*100:.1f}%")