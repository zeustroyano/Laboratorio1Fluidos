#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laboratorio 1 - Mecanica de Fluidos (UNAL Medellin)
Estimacion de la viscosidad dinamica de un fluido newtoniano mediante la
caida de esferas en regimen laminar (Ley de Stokes), corregida por efecto
de pared (efecto Ladenburg).

Corresponde a las preguntas 5.1, 5.2 y 5.3 de la guia de laboratorio:
regresion S vs t, correccion de Ladenburg, calculo de mu, numero de
Reynolds de la caida, y propagacion de error de mu segun las ecuaciones
(4) y (5) de la guia.

Fundamento teorico y ecuaciones
--------------------------------
Ecuacion (2): mu = (2/9) * (rho_e - rho_f) * g * r^2 / v_lim
Ecuacion (3): v_lim = (1 + 2.4 * D/phi) * v_m          [correccion de Ladenburg]
Numero de Reynolds de la caida: Re_c = rho_f * v_m * D / mu  (con v_m, no v_lim;
    ver seccion 3 de la guia)

Referencias
-----------
Cengel, Y. A., y Cimbala, J. M. (2012). Mecanica de fluidos: Fundamentos y
    aplicaciones (2a ed.). McGraw-Hill.
Ladenburg, R. von. (1907). Ueber den Einfluss von Waenden auf die Bewegung
    einer Kugel in einer reibenden Fluessigkeit. Annalen der Physik, 23,
    447-458.

Fuente de datos
----------------
Los datos NO se leen de un archivo Excel. Se leen de tres archivos CSV
planos, auditables y editables con cualquier editor de texto:
    datos/parametros_generales.csv    -> propiedades del fluido, la esfera
                                          y el recipiente
    datos/datos_caida_esferas.csv     -> serie (S, t) de las 4 esferas,
                                          en formato "tidy" (una fila por
                                          punto medido)
    datos/incertidumbres_tabla1.csv   -> incertidumbres instrumentales
                                          (Tabla 1 de la guia + nota de
                                          la seccion 4)
Esto evita depender de la posicion de las celdas en una hoja de calculo
(fragil ante cualquier reordenamiento) y deja el dato crudo en un formato
que se puede versionar, diferenciar y revisar linea por linea.

Instrucciones de uso (en su computador, no en un entorno remoto)
------------------------------------------------------------------
1. Coloque este archivo junto a la carpeta "datos/" (con los tres CSV
   descritos arriba) en la misma carpeta de trabajo.
2. (Recomendado) Cree un entorno virtual e instale las dependencias:
       python3 -m venv venv
       source venv/bin/activate          # Windows: venv\\Scripts\\activate
       pip install -r requirements.txt
3. Ejecute:
       python analisis_lab1.py
4. El script crea, DENTRO DE ESTA MISMA CARPETA:
       figuras/      -> graficas en PDF vectorial (listas para \\includegraphics
                         en Overleaf) y PNG de respaldo a 600 dpi
       resultados/   -> resultados_5_1_5_2_5_3.csv con la tabla numerica

Todas las rutas se calculan de forma relativa a la ubicacion de este
archivo (BASE_DIR), por lo que el script es portable entre computadores.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 0. Rutas portables (relativas a la ubicacion de este script)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "datos"
PARAM_PATH = DATA_DIR / "parametros_generales.csv"
SERIES_PATH = DATA_DIR / "datos_caida_esferas.csv"
INCERT_PATH = DATA_DIR / "incertidumbres_tabla1.csv"
FIG_DIR = BASE_DIR / "figuras"
RESULTS_DIR = BASE_DIR / "resultados"
FIG_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

for p in (PARAM_PATH, SERIES_PATH, INCERT_PATH):
    if not p.exists():
        raise FileNotFoundError(
            f"No se encontro '{p.relative_to(BASE_DIR)}' junto a este script en:\n  {BASE_DIR}\n"
            "Verifique que la carpeta 'datos/' este junto a analisis_lab1.py."
        )

# ---------------------------------------------------------------------------
# 1. Estilo grafico de calidad de publicacion (coherente con un documento
#    tipografiado en LaTeX/Overleaf: fuente Computer Modern via mathtext)
# ---------------------------------------------------------------------------
USE_SYSTEM_LATEX = False  # cambie a True solo si tiene una distribucion
                          # LaTeX instalada localmente (TeX Live/MiKTeX)

plt.rcParams.update({
    "text.usetex": USE_SYSTEM_LATEX,
    "mathtext.fontset": "cm",          # formulas ($...$) en estilo Computer Modern (LaTeX)
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Nimbus Roman No9 L",
                   "Liberation Serif"],  # texto normal: serif con soporte Unicode completo (tildes)
    "axes.formatter.use_mathtext": True,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
})

COLOR_DATOS = "#8c1c13"
COLOR_AJUSTE = "#1b2a4a"
COLOR_BANDA = "#1b2a4a"
PALETA_COMPARATIVA = ["#8c1c13", "#1b6ea8", "#2f7a3d", "#7b3f9e"]

ALPHA = 0.05  # nivel de significancia para intervalos de confianza (95 %)


# ---------------------------------------------------------------------------
# 2. Lectura de datos desde los CSV planos (fuente de verdad del analisis)
# ---------------------------------------------------------------------------
def leer_parametros_generales(path: Path) -> dict:
    """Lee parametros_generales.csv (columnas: parametro, valor, unidad)."""
    df = pd.read_csv(path)
    return dict(zip(df["parametro"], df["valor"]))


def leer_bloques_esferas(path: Path) -> dict:
    """
    Lee datos_caida_esferas.csv (formato tidy: esfera, D_mm, S_m, t_s) y
    agrupa por esfera, ordenando de menor a mayor diametro.
    """
    df = pd.read_csv(path)
    bloques: dict[str, dict] = {}
    for nombre, grupo in df.groupby("esfera"):
        grupo = grupo.sort_values("t_s")
        bloques[nombre] = {
            "D_mm": float(grupo["D_mm"].iloc[0]),
            "S": grupo["S_m"].to_numpy(dtype=float),
            "t": grupo["t_s"].to_numpy(dtype=float),
        }
    return dict(sorted(bloques.items(), key=lambda kv: kv[1]["D_mm"]))


parametros = leer_parametros_generales(PARAM_PATH)
rho_f = float(parametros["densidad_fluido"])
T_fluido = float(parametros["temperatura_fluido"])
g = float(parametros["gravedad"])
rho_e = float(parametros["densidad_esfera"])
phi = float(parametros["diametro_recipiente"]) / 1000.0  # mm -> m

bloques = leer_bloques_esferas(SERIES_PATH)

print(f"Fluido de trabajo: {parametros.get('fluido_nombre')}  (T = {T_fluido:.1f} C)")
print(f"rho_f = {rho_f:.1f} kg/m3 | rho_e = {rho_e:.1f} kg/m3 | "
      f"phi tubo = {phi*1000:.1f} mm | esferas detectadas: {len(bloques)}\n")

# ---------------------------------------------------------------------------
# 2b. Incertidumbres instrumentales (Tabla 1 de la guia + nota seccion 4)
#     -> convertidas aqui a unidades SI, una sola vez.
#
# NOTA METODOLOGICA: la Tabla 1 de la guia titula la columna "Error
# relativo" pero lista cada valor junto a la unidad propia de la variable
# (°C, cm/s2, g/cm3, mm). Un error relativo es adimensional, por lo que
# esos valores solo tienen sentido fisico como INCERTIDUMBRES ABSOLUTAS
# expresadas en esa unidad (p. ej. resolucion de un calibrador de 0.05 mm,
# de un termometro de 0.1 C, de un densimetro de 0.02 g/cm3). Esa es la
# interpretacion que se usa en este script. Verifique con su profesor si
# su guia especifica lo contrario.
# ---------------------------------------------------------------------------
def leer_incertidumbres(path: Path) -> dict:
    df = pd.read_csv(path)
    return dict(zip(df["variable"], df["valor"]))


incert = leer_incertidumbres(INCERT_PATH)

d_T = incert["temperatura"]                       # C (informativo; no entra en ec. 5)
d_g = incert["gravedad"] / 100.0                   # cm/s2 -> m/s2
d_rho_e = incert["densidad_esfera"] * 1000.0       # g/cm3 -> kg/m3
d_rho_f = incert["densidad_fluido"] * 1000.0       # g/cm3 -> kg/m3
d_D = incert["diametro_esfera"] / 1000.0           # mm -> m
d_phi = incert["diametro_probeta"] / 1000.0        # mm -> m (informativo; no entra en ec. 5)
d_S = incert["longitud_S"] / 100.0                 # cm -> m
d_t_medida = incert["tiempo_t"]                    # s

print(f"Incertidumbres instrumentales (SI): dg={d_g:.4f} m/s2, "
      f"d(rho_e)=d(rho_f)={d_rho_e:.1f} kg/m3, dD={d_D*1000:.3f} mm, "
      f"dS={d_S*100:.2f} cm, dt={d_t_medida:.3f} s\n")


# ---------------------------------------------------------------------------
# 3. Regresion S vs t, correccion de Ladenburg y viscosidad por esfera
# ---------------------------------------------------------------------------
def procesar_esfera(nombre: str, D_mm: float, S: np.ndarray, t: np.ndarray) -> dict:
    """
    Ajusta S(t) = v_m * t + b por minimos cuadrados ordinarios, corrige la
    velocidad por efecto de pared (ec. 3), propaga el error (ec. 4 y 5) y
    calcula la viscosidad dinamica (ec. 2) con su incertidumbre, y el
    numero de Reynolds de la caida.
    """
    n = len(t)
    D = D_mm / 1000.0
    r = D / 2.0

    reg = stats.linregress(t, S)
    v_m, b, r2, se_slope = reg.slope, reg.intercept, reg.rvalue ** 2, reg.stderr

    residuales = S - (v_m * t + b)
    s_d = float(np.sqrt(np.sum(residuales ** 2) / (n - 2)))
    t_crit = float(stats.t.ppf(1 - ALPHA / 2, df=n - 2))

    # Correccion de Ladenburg (ecuacion 3)
    factor_pared = 1 + 2.4 * (D / phi)
    v_lim = factor_pared * v_m

    # -----------------------------------------------------------------
    # Ecuacion (4): error relativo de V_L = componente sistematica +
    # componente aleatoria. S_total y t_total son la longitud y el
    # tiempo acumulados en el ultimo punto de la caida (la magnitud
    # medida directamente con el instrumento cuya resolucion es dS, dt).
    # -----------------------------------------------------------------
    S_total, t_total = S[-1], t[-1]
    err_sist2 = (d_S / S_total) ** 2 + (d_t_medida / t_total) ** 2
    err_aleat2 = (t_crit * s_d / (v_m * np.sqrt(n))) ** 2
    err_VL2 = err_sist2 + err_aleat2          # (delta V_L / V_L)^2, ec. (4)
    err_VL = np.sqrt(err_VL2)

    se_v_lim = v_lim * err_VL   # propaga igual en v_lim (factor_pared es constante conocido)

    # Viscosidad dinamica (ecuacion 2)
    mu = (2 / 9) * (rho_e - rho_f) * g * r ** 2 / v_lim

    # -----------------------------------------------------------------
    # Ecuacion (5): propagacion completa del error en mu
    # (delta_mu/mu)^2 = (delta(rho_e-rho_f)/(rho_e-rho_f))^2
    #                  + (delta V_L/V_L)^2 + (delta g/g)^2 + 4(delta r/r)^2
    # -----------------------------------------------------------------
    delta_rho_dif = np.sqrt(d_rho_e ** 2 + d_rho_f ** 2)     # propagacion de una resta
    err_rho2 = (delta_rho_dif / (rho_e - rho_f)) ** 2
    err_g2 = (d_g / g) ** 2
    err_r2 = 4 * (d_D / D) ** 2                               # delta_r/r = delta_D/D

    err_mu2 = err_rho2 + err_VL2 + err_g2 + err_r2
    err_mu_rel = np.sqrt(err_mu2)
    d_mu = mu * err_mu_rel

    # Numero de Reynolds de la caida (usa v_m, no v_lim; ver seccion 3 de la guia)
    Re_c = rho_f * v_m * D / mu

    return dict(
        esfera=nombre, D_mm=D_mm, D=D, r=r, n=n,
        v_m=v_m, se_slope=se_slope, intercepto=b, R2=r2,
        s_d=s_d, t_crit=t_crit,
        v_lim=v_lim, se_v_lim=se_v_lim,
        err_sist=np.sqrt(err_sist2), err_aleat=np.sqrt(err_aleat2), err_VL=err_VL,
        mu=mu, d_mu=d_mu, err_mu_rel=err_mu_rel,
        Re_c=Re_c,
        S=S, t=t, residuales=residuales,
    )


resultados = [
    procesar_esfera(nombre, datos["D_mm"], datos["S"], datos["t"])
    for nombre, datos in bloques.items()
]

tabla = pd.DataFrame([
    {
        "Esfera": r_["esfera"],
        "D [mm]": r_["D_mm"],
        "n puntos": r_["n"],
        "v_m [m/s]": r_["v_m"],
        "R^2": r_["R2"],
        "v_lim [m/s]": r_["v_lim"],
        "dV_L/V_L sist [%]": 100 * r_["err_sist"],
        "dV_L/V_L aleat [%]": 100 * r_["err_aleat"],
        "dV_L/V_L total [%]": 100 * r_["err_VL"],
        "mu [Pa.s]": r_["mu"],
        "d_mu [Pa.s]": r_["d_mu"],
        "d_mu/mu [%]": 100 * r_["err_mu_rel"],
        "Re_c": r_["Re_c"],
    }
    for r_ in resultados
])

with pd.option_context("display.float_format", lambda x: f"{x:.6g}"):
    print(tabla.to_string(index=False))

tabla.to_csv(RESULTS_DIR / "resultados_5_1_5_2_5_3.csv", index=False)


def redondear_con_incertidumbre(valor: float, incertidumbre: float) -> tuple[str, str]:
    """
    Redondea (valor, incertidumbre) a las cifras significativas correctas:
    1 cifra en la incertidumbre (2 si el primer digito es 1), y el valor
    central al mismo decimal. Devuelve strings ya formateados.
    """
    if incertidumbre == 0 or not np.isfinite(incertidumbre):
        return f"{valor:.4g}", f"{incertidumbre:.4g}"
    exp = int(np.floor(np.log10(abs(incertidumbre))))
    primer_digito = incertidumbre / 10 ** exp
    cifras = 2 if primer_digito < 2 else 1
    decimales = -(exp - (cifras - 1))
    decimales = max(decimales, 0)
    return f"{valor:.{decimales}f}", f"{incertidumbre:.{decimales}f}"


print("\nResultados con cifras significativas correctas (mu ± d_mu):")
for r_ in resultados:
    v_txt, d_txt = redondear_con_incertidumbre(r_["mu"], r_["d_mu"])
    print(f"  {r_['esfera']} (D={r_['D_mm']:.0f} mm): "
          f"mu = ({v_txt} \u00b1 {d_txt}) Pa\u00b7s "
          f"({100*r_['err_mu_rel']:.2f} %)")

# ---------------------------------------------------------------------------
# Consistencia entre las 4 estimaciones independientes de mu:
# media ponderada por el inverso de la varianza + chi-cuadrado reducido.
# ---------------------------------------------------------------------------
mus = tabla["mu [Pa.s]"].to_numpy()
d_mus = tabla["d_mu [Pa.s]"].to_numpy()
pesos = 1.0 / d_mus ** 2
mu_ponderado = float(np.sum(mus * pesos) / np.sum(pesos))
d_mu_ponderado = float(1.0 / np.sqrt(np.sum(pesos)))
chi2 = float(np.sum((mus - mu_ponderado) ** 2 / d_mus ** 2))
chi2_red = chi2 / (len(mus) - 1)

v_txt, d_txt = redondear_con_incertidumbre(mu_ponderado, d_mu_ponderado)
print(f"\nmu ponderado (las 4 esferas): ({v_txt} \u00b1 {d_txt}) Pa\u00b7s")
print(f"chi^2 reducido = {chi2_red:.2f} "
      f"({'consistente' if chi2_red < 2 else 'dispersion mayor a la esperada'} "
      f"con las incertidumbres declaradas, para chi^2_red ~ 1)")


# ---------------------------------------------------------------------------
# 4. Figuras vectoriales (PDF, listas para \includegraphics en Overleaf)
# ---------------------------------------------------------------------------
def graficar_regresion(r_: dict) -> None:
    """
    Figura de dos paneles por esfera:
      (a) S vs t con datos (+ barras de error instrumentales dS, dt),
          recta ajustada, banda de confianza 95% y cuadro de estadisticos.
      (b) Residuales (S_obs - S_pred) vs t, para verificar visualmente que
          no hay curvatura sistematica (supuesto de linealidad).
    """
    t_ = r_["t"]
    S_ = r_["S"]
    v_m, b = r_["v_m"], r_["intercepto"]
    s_d, t_crit, n = r_["s_d"], r_["t_crit"], r_["n"]
    residuales_mm = r_["residuales"] * 1000  # a mm para que se lea mejor

    fig = plt.figure(figsize=(4.6, 4.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax = fig.add_subplot(gs[0])
    ax_res = fig.add_subplot(gs[1], sharex=ax)

    t_line = np.linspace(0, t_.max(), 200)
    S_line = v_m * t_line + b

    # Banda de confianza (95 %) de la recta de regresion (no de un dato individual)
    t_mean = t_.mean()
    Sxx = np.sum((t_ - t_mean) ** 2)
    se_media = s_d * np.sqrt(1.0 / n + (t_line - t_mean) ** 2 / Sxx)
    banda = t_crit * se_media

    ax.fill_between(t_line, S_line - banda, S_line + banda,
                     color=COLOR_BANDA, alpha=0.15, linewidth=0,
                     label="IC 95 % de la recta")
    ax.plot(t_line, S_line, "-", color=COLOR_AJUSTE, linewidth=1.4, zorder=3,
            label="Ajuste por m\u00ednimos cuadrados")
    ax.errorbar(t_, S_, yerr=d_S, xerr=d_t_medida, fmt="o", color=COLOR_DATOS,
                markersize=4.5, markeredgecolor="white", markeredgewidth=0.4,
                ecolor=COLOR_DATOS, elinewidth=0.8, capsize=2, zorder=4,
                label=rf"Datos ($\delta S$={d_S*100:.1f} cm, $\delta t$={d_t_medida*1000:.0f} ms)")

    cuadro = (
        rf"$v_m$ = {v_m:.4e} $\pm$ {r_['se_slope']:.1e} m/s" "\n"
        rf"$R^2$ = {r_['R2']:.5f}" "\n"
        rf"$s_d$ = {s_d*1000:.2f} mm,  $n$ = {n}" "\n"
        rf"$\mu$ = ({redondear_con_incertidumbre(r_['mu'], r_['d_mu'])[0]} $\pm$ "
        rf"{redondear_con_incertidumbre(r_['mu'], r_['d_mu'])[1]}) Pa$\cdot$s"
    )
    ax.text(0.03, 0.97, cuadro, transform=ax.transAxes, va="top", ha="left",
            fontsize=7.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#999999", alpha=0.92))

    ax.set_ylabel(r"Longitud acumulada, $S$ [m]")
    ax.set_title(rf"{r_['esfera']} ($D$ = {r_['D_mm']:.0f} mm)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.9, fontsize=7.5)
    plt.setp(ax.get_xticklabels(), visible=False)

    # --- Panel de residuales ---
    ax_res.axhline(0, color="#555555", linewidth=0.9, linestyle="-")
    ax_res.fill_between(t_line, -1000 * banda, 1000 * banda,
                         color=COLOR_BANDA, alpha=0.15, linewidth=0)
    ax_res.errorbar(t_, residuales_mm, yerr=d_S * 1000, xerr=d_t_medida, fmt="o",
                     color=COLOR_DATOS, markersize=3.5, ecolor=COLOR_DATOS,
                     elinewidth=0.7, capsize=2)
    ax_res.set_xlabel(r"Tiempo acumulado, $t$ [s]")
    ax_res.set_ylabel("Residual\n[mm]", fontsize=8)
    ax_res.tick_params(axis="both", labelsize=7.5)

    fig.align_ylabels([ax, ax_res])
    slug = r_["esfera"].replace(" ", "_").lower()
    fig.savefig(FIG_DIR / f"regresion_{slug}.pdf")
    fig.savefig(FIG_DIR / f"regresion_{slug}.png")
    plt.close(fig)


def graficar_comparativo(resultados: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    for r_, color in zip(resultados, PALETA_COMPARATIVA):
        ax.plot(r_["t"], r_["S"], "o-", color=color, markersize=4,
                linewidth=1.1, label=rf"{r_['esfera']} ($D$={r_['D_mm']:.0f} mm)")
    ax.set_xlabel(r"Tiempo acumulado, $t$ [s]")
    ax.set_ylabel(r"Longitud acumulada, $S$ [m]")
    ax.set_title("Longitud acumulada vs. tiempo acumulado")
    ax.legend(loc="lower right", frameon=True, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "comparativo_S_vs_t.pdf")
    fig.savefig(FIG_DIR / "comparativo_S_vs_t.png")
    plt.close(fig)


def graficar_consistencia_mu(tabla: pd.DataFrame, mu_ponderado: float, d_mu_ponderado: float,
                              chi2_red: float) -> None:
    """
    Verificacion visual de si las cuatro estimaciones independientes de mu
    (cada una con su incertidumbre propagada segun las ecuaciones 4 y 5)
    son consistentes entre si, contra la media ponderada por el inverso
    de la varianza. Incluye el chi^2 reducido como diagnostico cuantitativo.
    """
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    D = tabla["D [mm]"].to_numpy()
    mu = tabla["mu [Pa.s]"].to_numpy()
    d_mu = tabla["d_mu [Pa.s]"].to_numpy()

    ax.axhspan(mu_ponderado - d_mu_ponderado, mu_ponderado + d_mu_ponderado,
               color="#999999", alpha=0.18,
               label=r"$\bar{\mu}_{pond} \pm \delta\bar{\mu}_{pond}$")
    ax.axhline(mu_ponderado, color="#555555", linestyle="--", linewidth=1)
    ax.errorbar(D, mu, yerr=d_mu, xerr=d_D * 1000, fmt="o", color=COLOR_DATOS,
                capsize=3, markersize=5, elinewidth=1,
                label=r"$\mu_i \pm \delta\mu_i$ (ec. 4 y 5)")

    v_txt, d_txt = redondear_con_incertidumbre(mu_ponderado, d_mu_ponderado)
    cuadro = (rf"$\bar\mu_{{pond}}$ = ({v_txt} $\pm$ {d_txt}) Pa$\cdot$s" "\n"
              rf"$\chi^2_{{red}}$ = {chi2_red:.2f}  ($n$ = {len(mu)})")
    ax.text(0.97, 0.03, cuadro, transform=ax.transAxes, va="bottom", ha="right",
            fontsize=7.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#999999", alpha=0.92))

    ax.set_xlabel(r"Diámetro de la esfera, $D$ [mm]")
    ax.set_ylabel(r"Viscosidad dinámica, $\mu$ [Pa$\cdot$s]")
    ax.set_title("Consistencia de $\\mu$ entre esferas")
    ax.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "consistencia_mu.pdf")
    fig.savefig(FIG_DIR / "consistencia_mu.png")
    plt.close(fig)


for r_ in resultados:
    graficar_regresion(r_)
graficar_comparativo(resultados)
graficar_consistencia_mu(tabla, mu_ponderado, d_mu_ponderado, chi2_red)

print(f"\nListo. Figuras vectoriales en: {FIG_DIR}")
print(f"Tabla de resultados en: {RESULTS_DIR / 'resultados_5_1_5_2_5_3.csv'}")


# ---------------------------------------------------------------------------
# 5. Analisis dimensional y coeficiente de arrastre (pregunta 5.4)
#
# Variables del problema: f(V_L, D, rho_f, mu, F) = 0  (5 variables, 3
# dimensiones M,L,T -> 2 grupos adimensionales por Buckingham Pi):
#   Pi_1 = Re  = rho_f * V_L * D / mu
#   Pi_2 = C_d = F / (0.5 * rho_f * V_L^2 * (pi*D^2/4))   [coeficiente de arrastre]
#
# F se calcula con la ecuacion (1b): F = (4/3) pi r^3 (rho_e - rho_f) g
#
# IMPORTANTE: aqui mu es el mu PONDERADO de la seccion 5.3 (fijo, el mismo
# para las 4 esferas), NO el mu_i propio de cada esfera. Usar el mu_i de
# cada esfera harta el chequeo circular: ese mu_i se calculo justamente
# forzando la ley de Stokes para esa esfera, asi que Cd*Re=24 saldria
# exacto por construccion y no probaria nada. Con un mu fijo y externo,
# el ajuste Re-Cd es una verificacion independiente de la teoria.
#
# Prediccion teorica (flujo de Stokes, Re << 1): C_d = 24/Re, es decir
# en escala log-log: ln(C_d) = ln(24) - ln(Re)  (pendiente = -1)
# ---------------------------------------------------------------------------
def analisis_dimensional(resultados: list[dict], mu_fijo: float, d_mu_fijo: float) -> pd.DataFrame:
    """
    Calcula F (ec. 1b), Re y Cd para cada esfera, junto con su incertidumbre
    propagada (derivada analiticamente de las formulas, ver docstring de
    graficar_analisis_dimensional para el detalle de cada termino).
    """
    delta_rho_dif = np.sqrt(d_rho_e ** 2 + d_rho_f ** 2)
    err_rho_dif_rel = delta_rho_dif / (rho_e - rho_f)
    err_rho_f_rel = d_rho_f / rho_f
    err_g_rel = d_g / g

    filas = []
    for r_ in resultados:
        D, r_esf, v_lim = r_["D"], r_["r"], r_["v_lim"]
        F = (4 / 3) * np.pi * r_esf ** 3 * (rho_e - rho_f) * g       # ec. (1b)
        A = np.pi * D ** 2 / 4
        Cd = F / (0.5 * rho_f * v_lim ** 2 * A)
        Re = rho_f * v_lim * D / mu_fijo

        err_D_rel = d_D / D
        err_v_rel = r_["se_v_lim"] / v_lim
        err_mu_rel = d_mu_fijo / mu_fijo

        # dRe/Re = drho_f/rho_f + dv/v + dD/D - dmu/mu  (independientes, en cuadratura)
        err_Re_rel = np.sqrt(err_rho_f_rel**2 + err_v_rel**2 + err_D_rel**2 + err_mu_rel**2)
        # dCd/Cd = dD/D + dDrho/Drho + dg/g - drho_f/rho_f - 2 dv/v  (independientes, en cuadratura)
        err_Cd_rel = np.sqrt(err_D_rel**2 + err_rho_dif_rel**2 + err_g_rel**2
                              + err_rho_f_rel**2 + (2 * err_v_rel) ** 2)

        filas.append({
            "Esfera": r_["esfera"], "D_mm": r_["D_mm"],
            "F [N]": F, "Re": Re, "d_Re": Re * err_Re_rel,
            "Cd": Cd, "d_Cd": Cd * err_Cd_rel,
        })
    return pd.DataFrame(filas)


tabla_dim = analisis_dimensional(resultados, mu_ponderado, d_mu_ponderado)

# Regresion potencial Cd = a * Re^b, ajustada en escala log-log
ln_Re = np.log(tabla_dim["Re"].to_numpy())
ln_Cd = np.log(tabla_dim["Cd"].to_numpy())
reg_dim = stats.linregress(ln_Re, ln_Cd)
b_exp = reg_dim.slope
a_coef = np.exp(reg_dim.intercept)
r2_dim = reg_dim.rvalue ** 2

tabla_dim.to_csv(RESULTS_DIR / "resultados_5_4_analisis_dimensional.csv", index=False)

print("\n--- Pregunta 5.4: numeros adimensionales (con incertidumbre propagada) ---")
with pd.option_context("display.float_format", lambda x: f"{x:.6g}"):
    print(tabla_dim.to_string(index=False))
print(f"\nAjuste potencial:  Cd = {a_coef:.3f} * Re^({b_exp:.3f})   (R^2 = {r2_dim:.4f})")
print(f"Prediccion teorica de Stokes (Re << 1):  Cd = 24/Re  "
      f"(a = 24, b = -1)")
print(f"Diferencia con la teoria: a: {100*(a_coef-24)/24:+.1f} %,  "
      f"b: {100*(b_exp+1)/1:+.1f} %")


def graficar_analisis_dimensional(tabla_dim: pd.DataFrame, a_coef: float, b_exp: float, r2_dim: float) -> None:
    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    Re = tabla_dim["Re"].to_numpy()
    Cd = tabla_dim["Cd"].to_numpy()
    d_Re = tabla_dim["d_Re"].to_numpy()
    d_Cd = tabla_dim["d_Cd"].to_numpy()

    Re_line = np.geomspace(Re.min() * 0.7, Re.max() * 1.4, 200)
    ax.plot(Re_line, a_coef * Re_line ** b_exp, "-", color=COLOR_AJUSTE, linewidth=1.4,
            label=rf"Ajuste: $C_d$ = {a_coef:.2f} $\cdot Re^{{{b_exp:.2f}}}$ ($R^2$={r2_dim:.4f})")
    ax.plot(Re_line, 24 / Re_line, "--", color="#555555", linewidth=1.2,
            label=r"Teoria de Stokes: $C_d = 24/Re$")
    ax.errorbar(Re, Cd, yerr=d_Cd, xerr=d_Re, fmt="o", color=COLOR_DATOS,
                markersize=6, markeredgecolor="white", markeredgewidth=0.5,
                ecolor=COLOR_DATOS, elinewidth=1, capsize=3,
                label="Datos (las 4 esferas) $\\pm$ incertidumbre propagada")

    for _, row in tabla_dim.iterrows():
        ax.annotate(f"D={row['D_mm']:.0f} mm", (row["Re"], row["Cd"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=7)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Número de Reynolds, $Re$")
    ax.set_ylabel(r"Coeficiente de arrastre, $C_d$")
    ax.set_title("An\u00e1lisis dimensional: $C_d$ vs. $Re$")
    ax.legend(loc="lower left", frameon=True, framealpha=0.9, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "analisis_dimensional.pdf")
    fig.savefig(FIG_DIR / "analisis_dimensional.png")
    plt.close(fig)


graficar_analisis_dimensional(tabla_dim, a_coef, b_exp, r2_dim)
print(f"Figura guardada en: {FIG_DIR / 'analisis_dimensional.pdf'}")
