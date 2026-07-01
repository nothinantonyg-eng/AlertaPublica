import pandas as pd
import sqlite3
import os

DATA_PATH = "../data/"
DB_PATH = "../data/alertapublica.db"

ARCHIVOS = [
    "CONOSCE_ADJUDICACIONES2024_0.xlsx",
    "CONOSCE_ADJUDICACIONES2025_0.xlsx",
    "CONOSCE_ADJUDICACIONES2026_0.xlsx",
]

def cargar_archivo(filename):
    path = os.path.join(DATA_PATH, filename)
    print(f"Cargando {filename}...")
    df = pd.read_excel(path, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    
    # Extraer año del nombre del archivo
    year = filename.replace("CONOSCE_ADJUDICACIONES","").replace("_0.xlsx","")
    df["año"] = year
    
    return df

def procesar(df):
    df["monto_referencial"] = pd.to_numeric(
        df["monto_referencial_item_soles"], errors="coerce"
    )
    df["monto_adjudicado"] = pd.to_numeric(
        df["monto_adjudicado_item_soles"], errors="coerce"
    )
    df["fecha_convocatoria"] = pd.to_datetime(
        df["fecha_convocatoria"], dayfirst=True, errors="coerce"
    )
    df["fecha_buenapro"] = pd.to_datetime(
        df["fecha_buenapro"], dayfirst=True, errors="coerce"
    )
    df["dias_proceso"] = (
        df["fecha_buenapro"] - df["fecha_convocatoria"]
    ).dt.days
    
    df["diferencia_pct"] = (
        (df["monto_adjudicado"] - df["monto_referencial"])
        / df["monto_referencial"] * 100
    ).round(2)
    
    # Reemplazar infinitos
    df["diferencia_pct"] = df["diferencia_pct"].replace(
        [float('inf'), float('-inf')], 0
    )
    
    return df

def guardar_en_sqlite(df):
    print(f"\nGuardando {len(df)} contratos en base de datos...")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("contratos", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ruc ON contratos(ruc_proveedor)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entidad ON contratos(codigoentidad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_monto ON contratos(monto_adjudicado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_año ON contratos(año)")
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM contratos").fetchone()[0]
    print(f"Total contratos en SQLite: {total}")
    conn.close()

def estadisticas(df):
    print("\n=== ESTADÍSTICAS POR AÑO ===")
    resumen = df.groupby("año").agg(
        contratos=("monto_adjudicado", "count"),
        monto_total=("monto_adjudicado", "sum"),
        promedio=("monto_adjudicado", "mean")
    ).round(0)
    print(resumen.to_string())
    
    print(f"\n=== TOTALES ===")
    print(f"Total contratos: {len(df):,}")
    print(f"Monto total: S/ {df['monto_adjudicado'].sum():,.0f}")
    print(f"Proveedores únicos: {df['ruc_proveedor'].nunique():,}")
    print(f"Entidades únicas: {df['codigoentidad'].nunique():,}")

if __name__ == "__main__":
    # Cargar y combinar todos los años
    dfs = []
    for archivo in ARCHIVOS:
        path = os.path.join(DATA_PATH, archivo)
        if os.path.exists(path):
            df = cargar_archivo(archivo)
            dfs.append(df)
        else:
            print(f"⚠️ No encontrado: {archivo}")
    
    if not dfs:
        print("❌ No se encontraron archivos.")
        exit()
    
    print(f"\nCombinando {len(dfs)} archivos...")
    df_total = pd.concat(dfs, ignore_index=True)
    df_total = procesar(df_total)
    
    guardar_en_sqlite(df_total)
    estadisticas(df_total)
    
    print("\n✅ Ingesta completada.")