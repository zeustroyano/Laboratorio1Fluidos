// app.js — Simulación interactiva del Laboratorio 1 (caída de esferas / viscosidad de Stokes)
// Toda la información numérica proviene de assets/data.js (datos verificados del laboratorio).
// No se generan ni interpolan datos "falsos": la animación interpola linealmente entre los
// 14 puntos realmente medidos de cada esfera.

(function () {
  'use strict';

  const S_MAX = LAB.S[LAB.S.length - 1];
  const T_REAL_MAX = Math.max(...LAB.esferas.map(e => e.t[e.t.length - 1]));
  const T_COMPARADO = 9; // segundos que dura la animación en modo "tiempo comparado"

  /* ---------------------------------------------------------------------
     Utilidades numéricas
     --------------------------------------------------------------------- */

  // Interpola S en función de t, dado un arreglo de tiempos (t) y el arreglo
  // común de posiciones (S), ambos de igual longitud, monótonos crecientes.
  function interpS(tArr, sArr, t) {
    if (t <= tArr[0]) return sArr[0];
    const tEnd = tArr[tArr.length - 1];
    if (t >= tEnd) return sArr[sArr.length - 1];
    for (let i = 0; i < tArr.length - 1; i++) {
      if (t >= tArr[i] && t <= tArr[i + 1]) {
        const f = (t - tArr[i]) / (tArr[i + 1] - tArr[i]);
        return sArr[i] + f * (sArr[i + 1] - sArr[i]);
      }
    }
    return sArr[sArr.length - 1];
  }

  // Velocidad local por diferencias centradas (adelante/atrás en los extremos).
  function velocidadesLocales(tArr, sArr) {
    const n = tArr.length;
    const out = [];
    for (let i = 0; i < n; i++) {
      let v;
      if (i === 0) v = (sArr[1] - sArr[0]) / (tArr[1] - tArr[0]);
      else if (i === n - 1) v = (sArr[n - 1] - sArr[n - 2]) / (tArr[n - 1] - tArr[n - 2]);
      else v = (sArr[i + 1] - sArr[i - 1]) / (tArr[i + 1] - tArr[i - 1]);
      out.push(v);
    }
    return out;
  }

  /* ---------------------------------------------------------------------
     Cabecera: mini animación de fondo (una esfera cayendo, en bucle)
     --------------------------------------------------------------------- */
  function heroAnim() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = 220, H = 360;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.scale(dpr, dpr);

    const tubeX = W / 2, tubeW = 64, tubeTop = 26, tubeBottom = H - 26;
    const esf = LAB.esferas[1]; // esfera de referencia para el bucle
    const tEnd = esf.t[esf.t.length - 1];
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let start = performance.now();

    function frame(now) {
      let elapsed = ((now - start) / 1000) % (tEnd + 1.2);
      const t = Math.min(elapsed, tEnd);
      const s = interpS(esf.t, LAB.S, t);
      const yFrac = s / S_MAX;

      ctx.clearRect(0, 0, W, H);

      // tubo
      ctx.strokeStyle = 'rgba(236,231,220,0.28)';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(tubeX - tubeW / 2, tubeTop, tubeW, tubeBottom - tubeTop);
      // fluido
      ctx.fillStyle = 'rgba(209,154,60,0.14)';
      ctx.fillRect(tubeX - tubeW / 2 + 1, tubeTop + 1, tubeW - 2, tubeBottom - tubeTop - 2);
      // marcas
      ctx.strokeStyle = 'rgba(236,231,220,0.15)';
      for (let i = 1; i < 6; i++) {
        const my = tubeTop + (i / 6) * (tubeBottom - tubeTop);
        ctx.beginPath(); ctx.moveTo(tubeX + tubeW / 2, my); ctx.lineTo(tubeX + tubeW / 2 + 6, my); ctx.stroke();
      }
      // esfera
      const cy = tubeTop + yFrac * (tubeBottom - tubeTop);
      ctx.beginPath();
      ctx.arc(tubeX, Math.min(cy, tubeBottom - 6), 6, 0, Math.PI * 2);
      ctx.fillStyle = esf.color;
      ctx.fill();

      if (!reduce) requestAnimationFrame(frame);
    }
    if (reduce) { frame(start); } else { requestAnimationFrame(frame); }
  }

  /* ---------------------------------------------------------------------
     Simulación principal: 4 tubos
     --------------------------------------------------------------------- */
  const Sim = {
    playing: false,
    mode: 'real', // 'real' | 'norm'
    speed: 1,
    clock: 0,     // segundos de "tiempo real" transcurrido (antes del multiplicador de velocidad)
    lastFrame: null,
    canvases: [],
  };

  function buildTubes() {
    const container = document.getElementById('tubes');
    container.innerHTML = '';
    Sim.canvases = LAB.esferas.map((esf) => {
      const card = document.createElement('div');
      card.className = 'tube-card';

      const label = document.createElement('div');
      label.className = 'tube-label';
      label.innerHTML = `<span style="color:${esf.color}">&#9679;</span> ${esf.nombre} <span class="d">(D = ${esf.D_mm.toFixed(0)} mm)</span>`;
      card.appendChild(label);

      const canvasWrap = document.createElement('div');
      canvasWrap.className = 'tube-canvas-wrap';
      const canvas = document.createElement('canvas');
      canvas.width = 70; canvas.height = 220;
      canvas.style.width = '70px'; canvas.style.height = '220px';
      canvasWrap.appendChild(canvas);
      card.appendChild(canvasWrap);

      const readout = document.createElement('div');
      readout.className = 'tube-readout';
      readout.innerHTML = `<span class="t" data-t>t = 0.00 s</span><span data-s>S = 0.00 m</span>`;
      card.appendChild(readout);

      container.appendChild(card);
      return { esf, canvas, ctx: canvas.getContext('2d'), readout };
    });
    drawAllTubes(0);
  }

  function drawTube(entry, sVal, tVal, finished) {
    const { ctx, esf } = entry;
    const W = 70, H = 220;
    const tubeW = 30, top = 14, bottom = H - 14;
    ctx.clearRect(0, 0, W, H);

    // tubo
    ctx.strokeStyle = '#3a4048';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(W / 2 - tubeW / 2, top, tubeW, bottom - top);
    // fluido
    ctx.fillStyle = 'rgba(209,154,60,0.12)';
    ctx.fillRect(W / 2 - tubeW / 2 + 1, top + 1, tubeW - 2, bottom - top - 2);
    // marcas cada 0.10 m
    ctx.strokeStyle = '#2b313a';
    ctx.font = '7px IBM Plex Mono, monospace';
    ctx.fillStyle = '#6f7580';
    for (let s = 0; s <= S_MAX + 1e-9; s += 0.10) {
      const my = top + (s / S_MAX) * (bottom - top);
      ctx.beginPath(); ctx.moveTo(W / 2 + tubeW / 2, my); ctx.lineTo(W / 2 + tubeW / 2 + 4, my); ctx.stroke();
    }
    // esfera
    const yFrac = sVal / S_MAX;
    const cy = top + yFrac * (bottom - top);
    const r = 5;
    ctx.beginPath();
    ctx.arc(W / 2, Math.min(cy, bottom - r), r, 0, Math.PI * 2);
    ctx.fillStyle = finished ? esf.color : esf.color;
    ctx.globalAlpha = finished ? 1 : 0.95;
    ctx.fill();
    ctx.globalAlpha = 1;
    if (finished) {
      ctx.strokeStyle = '#ece7dc';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(W / 2, Math.min(cy, bottom - r), r + 2.5, 0, Math.PI * 2); ctx.stroke();
    }

    entry.readout.querySelector('[data-t]').textContent = `t = ${tVal.toFixed(2)} s`;
    entry.readout.querySelector('[data-s]').textContent = finished
      ? `v_m = ${(esf.v_m * 1000).toFixed(1)} mm/s`
      : `S = ${sVal.toFixed(2)} m`;
    entry.readout.querySelector('[data-s]').classList.toggle('done', finished);
  }

  function drawAllTubes(realClock) {
    Sim.canvases.forEach((entry) => {
      const { esf } = entry;
      const tEnd = esf.t[esf.t.length - 1];
      let tVal, finished;
      if (Sim.mode === 'real') {
        tVal = Math.min(realClock, tEnd);
        finished = realClock >= tEnd;
      } else {
        const p = Math.min(realClock / T_COMPARADO, 1);
        tVal = p * tEnd;
        finished = p >= 1;
      }
      const sVal = interpS(esf.t, LAB.S, tVal);
      drawTube(entry, sVal, tVal, finished);
    });
  }

  function simFrame(now) {
    if (!Sim.playing) return;
    if (Sim.lastFrame == null) Sim.lastFrame = now;
    const dt = (now - Sim.lastFrame) / 1000;
    Sim.lastFrame = now;
    Sim.clock += dt * Sim.speed;

    const cap = Sim.mode === 'real' ? T_REAL_MAX : T_COMPARADO;
    if (Sim.clock >= cap) {
      Sim.clock = cap;
      drawAllTubes(Sim.clock);
      setPlaying(false);
      return;
    }
    drawAllTubes(Sim.clock);
    requestAnimationFrame(simFrame);
  }

  function setPlaying(state) {
    Sim.playing = state;
    const btn = document.getElementById('btn-play');
    btn.textContent = state ? 'Pausar' : 'Reproducir';
    if (state) {
      Sim.lastFrame = null;
      requestAnimationFrame(simFrame);
    }
  }

  function resetSim() {
    setPlaying(false);
    Sim.clock = 0;
    drawAllTubes(0);
  }

  function initSimControls() {
    document.getElementById('btn-play').addEventListener('click', () => setPlaying(!Sim.playing));
    document.getElementById('btn-reset').addEventListener('click', resetSim);
    document.getElementById('sel-speed').addEventListener('change', (e) => {
      Sim.speed = parseFloat(e.target.value);
    });
    document.querySelectorAll('.toggle-opt').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.toggle-opt').forEach((b) => { b.classList.remove('is-active'); b.setAttribute('aria-checked', 'false'); });
        btn.classList.add('is-active');
        btn.setAttribute('aria-checked', 'true');
        Sim.mode = btn.dataset.mode;
        resetSim();
      });
    });
  }

  /* ---------------------------------------------------------------------
     Leyenda compartida (activa/desactiva esferas en las gráficas)
     --------------------------------------------------------------------- */
  const visibility = {};
  LAB.esferas.forEach((e) => { visibility[e.nombre] = true; });

  function buildLegend() {
    const box = document.getElementById('sphere-legend');
    box.innerHTML = '';
    LAB.esferas.forEach((esf) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'legend-chip';
      chip.innerHTML = `<span class="dot" style="background:${esf.color}"></span>${esf.nombre} (${esf.D_mm.toFixed(0)} mm)`;
      chip.addEventListener('click', () => {
        visibility[esf.nombre] = !visibility[esf.nombre];
        chip.classList.toggle('is-off', !visibility[esf.nombre]);
        refreshCharts();
      });
      box.appendChild(chip);
    });
  }

  /* ---------------------------------------------------------------------
     Gráficas (Chart.js)
     --------------------------------------------------------------------- */
  Chart.defaults.color = '#a6a49a';
  Chart.defaults.font.family = "'IBM Plex Mono', monospace";
  Chart.defaults.font.size = 11;
  Chart.defaults.borderColor = '#2b313a';

  let chartPosicion, chartVelocidad, chartMu, chartDim;

  function baseGridOpts(xTitle, yTitle) {
    return {
      x: {
        type: 'linear',
        title: { display: true, text: xTitle, color: '#a6a49a' },
        grid: { color: '#232830' },
      },
      y: {
        type: 'linear',
        title: { display: true, text: yTitle, color: '#a6a49a' },
        grid: { color: '#232830' },
      },
    };
  }

  function buildChartPosicion() {
    const ctx = document.getElementById('chart-posicion');
    const datasets = LAB.esferas.map((esf) => ({
      label: esf.nombre,
      data: esf.t.map((t, i) => ({ x: t, y: LAB.S[i] })),
      borderColor: esf.color,
      backgroundColor: esf.color,
      pointRadius: 3,
      pointHoverRadius: 5,
      tension: 0,
      borderWidth: 2,
      hidden: !visibility[esf.nombre],
    }));
    chartPosicion = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        parsing: false,
        scales: baseGridOpts('Tiempo acumulado, t [s]', 'Longitud acumulada, S [m]'),
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => `${c.dataset.label}: t=${c.parsed.x.toFixed(2)} s, S=${c.parsed.y.toFixed(2)} m`,
            },
          },
        },
      },
    });
  }

  function buildChartVelocidad() {
    const ctx = document.getElementById('chart-velocidad');
    const datasets = [];
    LAB.esferas.forEach((esf) => {
      const vLocal = velocidadesLocales(esf.t, LAB.S);
      datasets.push({
        label: esf.nombre + ' (local)',
        data: esf.t.map((t, i) => ({ x: t, y: vLocal[i] * 1000 })),
        borderColor: esf.color,
        backgroundColor: esf.color,
        showLine: false,
        pointRadius: 3,
        pointHoverRadius: 5,
        hidden: !visibility[esf.nombre],
        sphereName: esf.nombre,
      });
      datasets.push({
        label: esf.nombre + ' (v_m ajustada)',
        data: [{ x: 0, y: esf.v_m * 1000 }, { x: esf.t[esf.t.length - 1], y: esf.v_m * 1000 }],
        borderColor: esf.color,
        borderDash: [5, 4],
        borderWidth: 1.5,
        pointRadius: 0,
        hidden: !visibility[esf.nombre],
        sphereName: esf.nombre,
      });
    });
    chartVelocidad = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        parsing: false,
        scales: baseGridOpts('Tiempo acumulado, t [s]', 'Velocidad, v [mm/s]'),
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: (item) => true,
            callbacks: {
              label: (c) => `${c.dataset.label}: ${c.parsed.y.toFixed(1)} mm/s`,
            },
          },
        },
      },
    });
  }

  // Plugin manual para barras de error verticales (Chart.js core no las incluye).
  const errorBarsPlugin = {
    id: 'errorBars',
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      chart.data.datasets.forEach((ds, di) => {
        if (!ds.errors) return;
        const meta = chart.getDatasetMeta(di);
        meta.data.forEach((point, i) => {
          if (!point) return;
          const err = ds.errors[i];
          const yScale = chart.scales.y;
          const yTop = yScale.getPixelForValue(ds.data[i].y + err);
          const yBot = yScale.getPixelForValue(ds.data[i].y - err);
          const color = Array.isArray(ds.borderColor) ? ds.borderColor[i] : ds.borderColor;
          ctx.save();
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(point.x, yTop); ctx.lineTo(point.x, yBot);
          ctx.moveTo(point.x - 5, yTop); ctx.lineTo(point.x + 5, yTop);
          ctx.moveTo(point.x - 5, yBot); ctx.lineTo(point.x + 5, yBot);
          ctx.stroke();
          ctx.restore();
        });
      });
    },
  };

  function buildChartMu() {
    const ctx = document.getElementById('chart-mu');
    const band = {
      label: 'Promedio ponderado ± incertidumbre',
      data: [{ x: 2, y: LAB.mu_pond }, { x: 12, y: LAB.mu_pond }],
      borderColor: 'rgba(236,231,220,0.55)',
      borderDash: [4, 4],
      pointRadius: 0,
      borderWidth: 1.5,
      fill: false,
    };
    const puntos = {
      label: 'μ por esfera',
      data: LAB.esferas.map((e) => ({ x: e.D_mm, y: e.mu })),
      errors: LAB.esferas.map((e) => e.d_mu),
      backgroundColor: LAB.esferas.map((e) => e.color),
      borderColor: LAB.esferas.map((e) => e.color),
      pointRadius: 5,
      pointHoverRadius: 7,
      showLine: false,
    };
    chartMu = new Chart(ctx, {
      type: 'line',
      data: { datasets: [band, puntos] },
      plugins: [errorBarsPlugin],
      options: {
        responsive: true, maintainAspectRatio: false,
        parsing: false,
        scales: {
          x: { type: 'linear', min: 2, max: 12, title: { display: true, text: 'Diámetro de la esfera, D [mm]' }, grid: { color: '#232830' } },
          y: { title: { display: true, text: 'Viscosidad dinámica, μ [Pa·s]' }, grid: { color: '#232830' } },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => c.datasetIndex === 1
                ? `μ = ${c.parsed.y.toFixed(3)} ± ${LAB.esferas[c.dataIndex].d_mu.toFixed(3)} Pa·s`
                : `promedio ponderado = ${LAB.mu_pond.toFixed(3)} ± ${LAB.d_mu_pond.toFixed(3)} Pa·s`,
            },
          },
        },
      },
    });
  }

  function buildChartDimensional() {
    const ctx = document.getElementById('chart-dimensional');
    const { a_coef, b_exp } = LAB.analisis_dim;
    const reMin = Math.min(...LAB.esferas.map((e) => e.Re_dim)) * 0.7;
    const reMax = Math.max(...LAB.esferas.map((e) => e.Re_dim)) * 1.4;
    const curvePts = 40;
    const fitLine = [], stokesLine = [];
    for (let i = 0; i <= curvePts; i++) {
      const re = reMin * Math.pow(reMax / reMin, i / curvePts);
      fitLine.push({ x: re, y: a_coef * Math.pow(re, b_exp) });
      stokesLine.push({ x: re, y: 24 / re });
    }
    const puntos = {
      label: 'Datos (4 esferas)',
      data: LAB.esferas.map((e) => ({ x: e.Re_dim, y: e.Cd })),
      backgroundColor: LAB.esferas.map((e) => e.color),
      borderColor: LAB.esferas.map((e) => e.color),
      pointRadius: 5,
      pointHoverRadius: 7,
      showLine: false,
    };
    const ajuste = {
      label: `Ajuste: Cd = ${a_coef.toFixed(2)}·Re^${b_exp.toFixed(3)}`,
      data: fitLine,
      borderColor: '#ece7dc',
      borderWidth: 1.75,
      pointRadius: 0,
    };
    const stokes = {
      label: 'Teoría de Stokes: Cd = 24/Re',
      data: stokesLine,
      borderColor: 'rgba(236,231,220,0.5)',
      borderDash: [5, 4],
      borderWidth: 1.5,
      pointRadius: 0,
    };
    chartDim = new Chart(ctx, {
      type: 'line',
      data: { datasets: [ajuste, stokes, puntos] },
      options: {
        responsive: true, maintainAspectRatio: false,
        parsing: false,
        scales: {
          x: { type: 'logarithmic', title: { display: true, text: 'Número de Reynolds, Re (escala log)' }, grid: { color: '#232830' } },
          y: { type: 'logarithmic', title: { display: true, text: 'Coeficiente de arrastre, Cd (escala log)' }, grid: { color: '#232830' } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14 } },
          tooltip: {
            callbacks: {
              label: (c) => `${c.dataset.label}: Re=${c.parsed.x.toFixed(3)}, Cd=${c.parsed.y.toFixed(1)}`,
            },
          },
        },
      },
    });

    const r2pct = (LAB.analisis_dim.r2_dim * 100).toFixed(2);
    document.getElementById('fit-note').textContent =
      `Ajuste potencial: Cd = ${a_coef.toFixed(2)} · Re^${b_exp.toFixed(3)}  (R² = ${r2pct}%). ` +
      `Diferencia frente a la teoría de Stokes (Cd = 24/Re): ${(100*(a_coef-24)/24).toFixed(1)}% en el coeficiente, ` +
      `${(100*(b_exp+1)/1).toFixed(1)}% en el exponente.`;
  }

  function refreshCharts() {
    [chartPosicion, chartVelocidad].forEach((chart) => {
      if (!chart) return;
      chart.data.datasets.forEach((ds) => {
        const name = ds.sphereName || ds.label;
        const key = LAB.esferas.find((e) => name.indexOf(e.nombre) === 0);
        if (key) ds.hidden = !visibility[key.nombre];
      });
      chart.update();
    });
  }

  /* ---------------------------------------------------------------------
     Pestañas posición / velocidad
     --------------------------------------------------------------------- */
  function initChartTabs() {
    document.querySelectorAll('.chart-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.chart-tab').forEach((t) => { t.classList.remove('is-active'); t.setAttribute('aria-selected', 'false'); });
        tab.classList.add('is-active');
        tab.setAttribute('aria-selected', 'true');
        const which = tab.dataset.chart;
        document.querySelectorAll('.chart-box[data-panel]').forEach((box) => {
          box.hidden = box.dataset.panel !== which;
        });
        if (which === 'velocidad' && chartVelocidad) chartVelocidad.resize();
        if (which === 'posicion' && chartPosicion) chartPosicion.resize();
      });
    });
  }

  /* ---------------------------------------------------------------------
     Tabla de resultados
     --------------------------------------------------------------------- */
  function buildTable() {
    const tbody = document.querySelector('#tabla-resultados tbody');
    tbody.innerHTML = LAB.esferas.map((e) => `
      <tr>
        <td><span class="sphere-swatch" style="background:${e.color}"></span>${e.nombre}</td>
        <td>${e.D_mm.toFixed(0)}</td>
        <td>${(e.v_m * 1000).toFixed(2)}</td>
        <td>${e.R2.toFixed(5)}</td>
        <td>${e.mu.toFixed(3)} ± ${e.d_mu.toFixed(3)}</td>
        <td>${e.Re_c.toFixed(4)}</td>
      </tr>`).join('');
  }

  /* ---------------------------------------------------------------------
     Estadísticas de la cabecera
     --------------------------------------------------------------------- */
  function fillHeroStats() {
    document.getElementById('stat-mu').textContent = LAB.mu_pond.toFixed(2);
    document.getElementById('stat-chi2').textContent = LAB.chi2_red.toFixed(2);
    const reMax = Math.max(...LAB.esferas.map((e) => e.Re_c));
    document.getElementById('stat-re').textContent = reMax.toFixed(2);
  }

  /* ---------------------------------------------------------------------
     Arranque
     --------------------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', () => {
    fillHeroStats();
    heroAnim();
    buildTubes();
    initSimControls();
    buildLegend();
    buildChartPosicion();
    buildChartVelocidad();
    buildChartMu();
    buildChartDimensional();
    initChartTabs();
    buildTable();
  });
})();
