# Viscosimetría de Stokes — recurso interactivo

Sitio estático (HTML/CSS/JS, sin build step) que acompaña el informe del
Laboratorio 1 de Mecánica de Fluidos (UNAL Medellín): simulación de la caída
de cuatro esferas en un fluido viscoso, gráficas interactivas de posición y
velocidad, consistencia de la viscosidad estimada, y el análisis dimensional
Cd vs. Re.

## Estructura

```
.
├── index.html          # página principal (única página)
├── assets/
│   ├── style.css        # sistema de diseño (tokens de color/tipografía)
│   ├── data.js           # datos del laboratorio (verificados)
│   └── app.js             # simulación + gráficas (Chart.js vía CDN)
└── reporte_lab1.pdf     # (opcional) informe compilado — ver abajo
```

No hay dependencias que instalar ni paso de compilación: es HTML/CSS/JS
plano. La única librería externa es **Chart.js**, cargada desde un CDN
(`cdn.jsdelivr.net`) en `index.html`.

## Publicar en GitHub Pages

1. Sube estos archivos a un repositorio de GitHub (por ejemplo `lab1-fluidos`),
   manteniendo la misma estructura de carpetas (`index.html` en la raíz).
2. En el repositorio: **Settings → Pages**.
3. En "Build and deployment", elige **Source: Deploy from a branch**.
4. Selecciona la rama `main` (o la que uses) y la carpeta `/ (root)`.
5. Guarda. GitHub publica el sitio en un par de minutos en
   `https://<tu-usuario>.github.io/<nombre-del-repo>/`.

## Antes de publicar: dos enlaces por completar

El sitio trae dos marcadores de posición que debes reemplazar con tus
propios datos (búscalos por `TODO` o por el comentario que los acompaña):

- **Footer → "Ver repositorio"** (`index.html`, cerca del final): cambia
  `href="https://github.com/"` por la URL real de tu repositorio.
- **Botón "Leer el informe completo"** (`index.html`, sección `hero`):
  ya apunta a `reporte_lab1.pdf`. Compila `reporte_lab1.tex` en Overleaf,
  descarga el PDF resultante, y guárdalo con ese mismo nombre en la raíz
  del repositorio (junto a `index.html`).
- **En el informe** (`reporte_lab1.tex`, sección "Simulación interactiva"):
  reemplaza `https://ENLACE-DE-LA-SIMULACION-AQUI` por la URL que te
  entregue GitHub Pages en el paso anterior, y vuelve a compilar el PDF.

## Datos

Todos los números que usa la página (`assets/data.js`) provienen de
`DatosLab1.xlsx` y fueron verificados por recálculo independiente a partir
de los datos crudos (regresión lineal, corrección de Ladenburg, viscosidad,
propagación de error, promedio ponderado y análisis dimensional). No hay
valores inventados ni interpolados más allá de la interpolación lineal
explícita que usa la animación entre los 14 puntos medidos de cada esfera.

## Desarrollo local

Cualquier servidor estático sirve, por ejemplo:

```bash
python3 -m http.server 8000
# abrir http://localhost:8000
```
