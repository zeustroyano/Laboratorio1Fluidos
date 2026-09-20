#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera los datos que necesita la pagina web (web/index.html): parametros
fisicos para animar la caida de cada esfera Y todos los resultados
numericos ya calculados del laboratorio (5.1 a 5.4), para mostrarlos en
un panel de resultados dentro de la misma pagina.

Fisica del modelo animado
--------------------------
En regimen de Stokes (Re << 1) el arrastre viscoso es LINEAL en la
velocidad: F_arrastre = 6*pi*mu*r*V. El balance de fuerzas de la
ecuacion (1) se reduce entonces a una ODE lineal de primer orden:

    m dV/dt = (4/3) pi r^3 (rho_e - rho_f) g  -  6 pi mu r V

cuya solucion analitica, partiendo de V(0) = 0, es:

    V(t) = V_lim * (1 - exp(-t/tau))          tau = m / (6 pi mu r)
    y(t) = V_lim * (t - tau*(1 - exp(-t/tau)))

Con los valores reales de este laboratorio (fluido muy viscoso, esferas
pequenas, Re_c << 1) tau resulta del orden de microsegundos: la esfera
alcanza v_lim practicamente al instante. Esto NO es un error del modelo:
es precisamente la firma del regimen de creeping flow que la pregunta
5.2 pide verificar. La pagina lo explica en vez de ocultarlo.

El tiempo de llegada a S_max se aproxima con la forma asintotica
(excelente aqui, dado que t_llegada >> tau):
    t_llegada = S_max / V_lim + tau

El mu ponderado, su incertidumbre y el chi^2 reducido se recalculan
aqui mismo (formulas identicas a analisis_lab1.py) para no depender de
valores que solo se imprimieron en consola durante el analisis
principal. Lo mismo con el ajuste potencial Cd = a*Re^b de la seccion 5.4.

Uso
---
Colocar este archivo junto a "datos/" y "resultados/" (en la raiz del
proyecto, o dentro de una subcarpeta "web/": el script busca en ambos
lugares automaticamente). Luego:

    python3 generar_datos_animacion.py

Genera "datos_animacion.js" junto a este script, que index.html carga
con <script src="datos_animacion.js"></script> (evita problemas de CORS
al abrir el HTML sin servidor local).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WEB_DIR = Path(__file__).resolve().parent

# Busca 'datos/' y 'resultados/' junto al script o un nivel arriba, para
# funcionar tanto si lo corres en la raiz del proyecto como en 'web/'.
CANDIDATOS = [WEB_DIR, WEB_DIR.parent]
PROJECT_DIR = None
for candidato in CANDIDATOS:
    if (candidato / "datos").is_dir() and (candidato / "resultados").is_dir():
        PROJECT_DIR = candidato
        break

if PROJECT_DIR is None:
    raise FileNotFoundError(
        "No se encontraron las carpetas 'datos/' y 'resultados/' ni junto a "
        f"este script ({WEB_DIR}) ni un nivel arriba ({WEB_DIR.parent}).\n"
        "Verifica que este archivo este dentro de tu proyecto del laboratorio."
    )

PARAM_PATH = PROJECT_DIR / "datos" / "parametros_generales.csv"
RESULTADOS_PATH = PROJECT_DIR / "resultados" / "resultados_5_1_5_2_5_3.csv"
DIM_PATH = PROJECT_DIR / "resultados" / "resultados_5_4_analisis_dimensional.csv"
OUT_PATH = WEB_DIR / "datos_animacion.js"

for p in (PARAM_PATH, RESULTADOS_PATH):
    if not p.exists():
        raise FileNotFoundError(
            f"No se encontro '{p}'.\n"
            f"Se detecto la carpeta del proyecto en: {PROJECT_DIR}\n"
            "pero falta ese archivo especifico. Verifica que hayas corrido "
            "antes analisis_lab1.py."
        )

# Misma paleta que las figuras PDF del informe (analisis_lab1.py), para
# que la pagina se vea visualmente consistente con el documento.
PALETA = ["#8c1c13", "#1b6ea8", "#2f7a3d", "#7b3f9e"]
S_MAX = 0.65  # recorrido tipico medido en el laboratorio [m]

# ---------------------------------------------------------------------------
# Parametros generales y resultados 5.1-5.3
# ---------------------------------------------------------------------------
parametros = dict(zip(*pd.read_csv(PARAM_PATH)[["parametro", "valor"]].to_numpy().T))
rho_f = float(parametros["densidad_fluido"])
rho_e = float(parametros["densidad_esfera"])
g = float(parametros["gravedad"])
fluido_nombre = str(parametros["fluido_nombre"])

tabla = pd.read_csv(RESULTADOS_PATH).sort_values("D [mm]").reset_index(drop=True)

mus = tabla["mu [Pa.s]"].to_numpy()
d_mus = tabla["d_mu [Pa.s]"].to_numpy()
pesos = 1.0 / d_mus ** 2
mu_pond = float(np.sum(mus * pesos) / np.sum(pesos))
d_mu_pond = float(1.0 / np.sqrt(np.sum(pesos)))
chi2 = float(np.sum((mus - mu_pond) ** 2 / d_mus ** 2))
chi2_red = chi2 / (len(mus) - 1)

esferas = []
for i, row in tabla.iterrows():
    D = row["D [mm]"] / 1000.0
    r = D / 2.0
    v_lim = float(row["v_lim [m/s]"])
    masa = rho_e * (4 / 3) * np.pi * r ** 3
    peso = masa * g
    empuje = rho_f * (4 / 3) * np.pi * r ** 3 * g
    B = 6 * np.pi * mu_pond * r          # coeficiente de arrastre lineal (Stokes)
    tau = masa / B
    t_llegada = S_MAX / v_lim + tau      # forma asintotica (tau << t_llegada aqui)

    esferas.append({
        "nombre": row["Esfera"],
        "D_mm": float(row["D [mm]"]),
        "color": PALETA[i % len(PALETA)],
        "n_puntos": int(row["n puntos"]),
        "v_m": float(row["v_m [m/s]"]),
        "R2": float(row["R^2"]),
        "v_lim": v_lim,
        "tau": tau,
        "t_llegada": t_llegada,
        "masa": masa,
        "peso": peso,
        "empuje": empuje,
        "mu_pas": float(row["mu [Pa.s]"]),
        "d_mu_pas": float(row["d_mu [Pa.s]"]),
        "d_mu_rel_pct": float(row["d_mu/mu [%]"]),
        "Re_c": float(row["Re_c"]),
    })

# ---------------------------------------------------------------------------
# Resultados 5.4 (analisis dimensional): si el CSV existe, se recalcula el
# ajuste potencial Cd = a*Re^b a partir de los mismos puntos ya guardados.
# ---------------------------------------------------------------------------
analisis_dim = None
if DIM_PATH.exists():
    tabla_dim = pd.read_csv(DIM_PATH).sort_values("D_mm").reset_index(drop=True)
    ln_Re = np.log(tabla_dim["Re"].to_numpy())
    ln_Cd = np.log(tabla_dim["Cd"].to_numpy())
    reg_dim = stats.linregress(ln_Re, ln_Cd)
    a_coef = float(np.exp(reg_dim.intercept))
    b_exp = float(reg_dim.slope)
    r2_dim = float(reg_dim.rvalue ** 2)

    puntos_dim = []
    for _, row in tabla_dim.iterrows():
        punto = {"D_mm": float(row["D_mm"]), "Re": float(row["Re"]), "Cd": float(row["Cd"])}
        if "d_Re" in row and not pd.isna(row.get("d_Re")):
            punto["d_Re"] = float(row["d_Re"])
        if "d_Cd" in row and not pd.isna(row.get("d_Cd")):
            punto["d_Cd"] = float(row["d_Cd"])
        puntos_dim.append(punto)

    analisis_dim = {
        "a_coef": a_coef, "b_exp": b_exp, "r2_dim": r2_dim,
        "puntos": puntos_dim,
    }
else:
    print(f"Aviso: no se encontro '{DIM_PATH.name}' — la pagina se generara "
          "sin la seccion de analisis dimensional (5.4).")

# ---------------------------------------------------------------------------
# Ensamblar y escribir
# ---------------------------------------------------------------------------
datos = {
    "fluido": fluido_nombre,
    "rho_f": rho_f,
    "rho_e": rho_e,
    "g": g,
    "mu_pond": mu_pond,
    "d_mu_pond": d_mu_pond,
    "chi2_red": chi2_red,
    "S_max": S_MAX,
    "esferas": esferas,
    "analisis_dim": analisis_dim,
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("// Generado automaticamente por generar_datos_animacion.py — no editar a mano.\n")
    f.write("const LAB_DATA = ")
    json.dump(datos, f, indent=2, ensure_ascii=False)
    f.write(";\n")

print(f"Listo: {OUT_PATH}")
print(f"mu ponderado: ({mu_pond:.4f} +/- {d_mu_pond:.4f}) Pa.s  (chi2_red={chi2_red:.2f})")
for e in esferas:
    print(f"  {e['nombre']}: D={e['D_mm']:.0f} mm, v_lim={e['v_lim']:.5f} m/s, "
          f"tau={e['tau']*1e6:.2f} us, t_llegada={e['t_llegada']:.2f} s")
if analisis_dim:
    print(f"Ajuste 5.4: Cd = {analisis_dim['a_coef']:.3f} * Re^{analisis_dim['b_exp']:.3f} "
          f"(R^2={analisis_dim['r2_dim']:.4f})")
