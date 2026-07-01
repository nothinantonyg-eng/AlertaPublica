from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
import pandas as pd
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(title="Alerta Pública API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "../data/alertapublica.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/stats")
def estadisticas():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM contratos").fetchone()[0]
    alertas = conn.execute("SELECT COUNT(*) FROM alertas").fetchone()[0]
    monto = conn.execute("SELECT SUM(monto_adjudicado) FROM contratos").fetchone()[0]
    max_score = conn.execute("SELECT MAX(score_riesgo) FROM alertas").fetchone()[0]
    conn.close()
    return {
        "total_contratos": total,
        "total_alertas": alertas,
        "monto_total": round(monto or 0, 2),
        "max_score_riesgo": max_score or 0,
        "porcentaje_sospechoso": round(alertas / total * 100, 1)
    }

@app.get("/api/alertas")
def listar_alertas(
    limite: int = Query(50, le=200),
    departamento: str = Query(None),
    score_minimo: int = Query(40)
):
    conn = get_db()
    query = """
        SELECT entidad, proveedor, monto_adjudicado, 
               score_riesgo, dias_proceso, diferencia_pct,
               entidad_departamento, tipoprocesoseleccion,
               descripcion_proceso, fecha_convocatoria, fecha_buenapro
        FROM alertas 
        WHERE score_riesgo >= ?
    """
    params = [score_minimo]
    
    if departamento:
        query += " AND entidad_departamento = ?"
        params.append(departamento)
    
    query += " ORDER BY score_riesgo DESC, monto_adjudicado DESC LIMIT ?"
    params.append(limite)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/departamentos")
def listar_departamentos():
    conn = get_db()
    rows = conn.execute("""
        SELECT entidad_departamento, COUNT(*) as alertas,
               SUM(monto_adjudicado) as monto_total
        FROM alertas 
        GROUP BY entidad_departamento 
        ORDER BY alertas DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/explicar")
async def explicar_alerta(data: dict):
    entidad = data.get("entidad", "")
    proveedor = data.get("proveedor", "")
    monto = data.get("monto_adjudicado", 0)
    score = data.get("score_riesgo", 0)
    dias = data.get("dias_proceso", None)
    diferencia = data.get("diferencia_pct", None)

    prompt = f"""Eres un analista de transparencia gubernamental peruano. 
Analiza esta contratación pública y explica en lenguaje simple y directo 
por qué es sospechosa. Máximo 3 párrafos cortos. En español.

Datos:
- Entidad: {entidad}
- Proveedor: {proveedor}  
- Monto adjudicado: S/ {monto:,.0f}
- Score de riesgo: {score}/100
- Días del proceso: {dias if dias else 'No disponible'}
- Diferencia vs monto referencial: {f'{diferencia:.1f}%' if diferencia else 'No disponible'}

Explica qué patrones son sospechosos y por qué esto podría indicar irregularidades."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
    )
    return {"explicacion": response.choices[0].message.content}

@app.get("/api/tendencia")
def tendencia_anual():
    conn = get_db()
    rows = conn.execute("""
        SELECT año,
               COUNT(*) as total_contratos,
               SUM(CASE WHEN score_riesgo >= 40 THEN 1 ELSE 0 END) as alertas,
               SUM(monto_adjudicado) as monto_total,
               AVG(monto_adjudicado) as monto_promedio
        FROM contratos_scored
        GROUP BY año
        ORDER BY año
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/alertas/año/{year}")
def alertas_por_año(year: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT entidad, proveedor, monto_adjudicado,
               score_riesgo, dias_proceso, entidad_departamento, año
        FROM alertas
        WHERE año = ?
        ORDER BY score_riesgo DESC, monto_adjudicado DESC
        LIMIT 100
    """, [year]).fetchall()
    conn.close()
    return [dict(r) for r in rows]