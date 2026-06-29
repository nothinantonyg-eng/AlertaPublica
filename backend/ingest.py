import pandas as pd
import sqlite3
import os

DATA_PATH = "../data/CONOSCE_ADJUDICACIONES2026_0.xlsx"
DB_PATH = "../data/alertapublica.db"

def cargar_datos():
    print("Cargando datos del SEACE...")
    df = pd.read_excel(DATA_PATH, dtype=str)
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()
    
    # Convertir columnas numéricas
    df["monto_referencial"] = pd.to_numeric(
        df["monto_referencial_item_soles"], errors="coerce"
    )
    df["monto_adjudicado"] = pd.to_numeric(
        df["monto_adjudicado_item_soles"], errors="coerce"
    )
    
    # Convertir fechas
    df["fecha_convocatoria"] = pd.to_datetime(
        df["fecha_convocatoria"], errors="coerce"
    )
    df["fecha_buenapro"] = pd.to_datetime(
        df["fecha_buenapro"], errors="coerce"
    )
    
    # Calcular días entre convocatoria y buena pro
    df["dias_proceso"] = (
        df["fecha_buenapro"] - df["fecha_convocatoria"]
    ).dt.days
    
    # Calcular diferencia porcentual entre monto referencial y adjudicado
    df["diferencia_pct"] = (
        (df["monto_adjudicado"] - df["monto_referencial"])
        / df["monto_referencial"] * 100
    ).round(2)
    
    print(f"Filas cargadas: {len(df)}")
    print(f"Columnas: {list(df.columns)}")
    print(f"\nMuestra de montos:")
    print(df[["entidad", "proveedor", "monto_referencial", 
              "monto_adjudicado", "dias_proceso"]].head(5))
    
    return df

def guardar_en_sqlite(df):
    print("\nGuardando en base de datos...")
    conn = sqlite3.connect(DB_PATH)
    
    # Guardar tabla principal
    df.to_sql("contratos", conn, if_exists="replace", index=False)
    
    # Crear índices para búsqueda rápida
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ruc ON contratos(ruc_proveedor)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entidad ON contratos(codigoentidad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_monto ON contratos(monto_adjudicado)")
    
    conn.commit()
    
    # Verificar
    total = conn.execute("SELECT COUNT(*) FROM contratos").fetchone()[0]
    print(f"Contratos guardados en SQLite: {total}")
    
    conn.close()

def estadisticas_basicas(df):
    print("\n=== ESTADÍSTICAS BÁSICAS ===")
    print(f"Total contratos: {len(df)}")
    print(f"Monto total adjudicado: S/ {df['monto_adjudicado'].sum():,.0f}")
    print(f"Monto promedio: S/ {df['monto_adjudicado'].mean():,.0f}")
    print(f"Monto máximo: S/ {df['monto_adjudicado'].max():,.0f}")
    print(f"Proveedores únicos: {df['ruc_proveedor'].nunique()}")
    print(f"Entidades únicas: {df['codigoentidad'].nunique()}")
    print(f"Departamentos: {df['entidad_departamento'].nunique()}")
    
    print("\nTop 5 proveedores por monto total:")
    top = df.groupby("proveedor")["monto_adjudicado"].sum().sort_values(
        ascending=False
    ).head(5)
    print(top.to_string())

if __name__ == "__main__":
    df = cargar_datos()
    guardar_en_sqlite(df)
    estadisticas_basicas(df)
    print("\n✅ Ingesta completada. Base de datos lista.")