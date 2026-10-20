import * as Plot from '@observablehq/plot';
import type { Municipio, Nivel } from './dados';
import { data, diaMesAno, n, NOMES_NIVEL, somarSemanas } from './formato';

// Cores lidas do CSS: assim os gráficos seguem o modo claro ou escuro
function cor(nome: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}

function cores() {
  return {
    nivel: [cor('--verde'), cor('--amarelo'), cor('--vermelho')],
    tinta: cor('--tinta'), tintaSec: cor('--tinta-sec'), mudo: cor('--mudo'), grade: cor('--grade'),
    previsto: cor('--azul'), faixa: cor('--azul-faixa'), fundo: cor('--fundo-card'),
  };
}

interface Ponto { semana: Date; valor: number }

function pontos(semanas: string[], valores: (number | null)[]): Ponto[] {
  return semanas.flatMap((s, i) => (valores[i] == null ? [] : [{ semana: data(s), valor: valores[i] as number }]));
}

// Largura disponível para o gráfico (o conteúdo principal menos o recuo do card)
function largura(): number {
  return Math.max(320, (document.querySelector('main')?.clientWidth ?? 900) - 34);
}

// Eixo de tempo em português: mês abreviado e o ano em janeiro
function mesAno(d: Date): string {
  const mes = d.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '');
  return d.getMonth() === 0 ? `${mes}
${d.getFullYear()}` : mes;
}

function eixoY(log: boolean) {
  return log
    ? { type: 'log' as const, label: 'Casos por semana (escala logarítmica)', grid: true, tickFormat: (v: number) => n(v),
        ticks: 6 }
    : { label: 'Casos por semana', grid: true, tickFormat: (v: number) => n(v), zero: true };
}

const MARGEM_ESQ = 64;
const MARGEM_DIR = 20;

/** Indicadores: casos das últimas semanas e, embaixo, os níveis confirmados no mesmo eixo de tempo. */
export function graficoCasos(m: Municipio, semanas: number, log: boolean): Element {
  const ini = Math.max(0, m.serie.semana.length - semanas);
  const dominio: [Date, Date] = [data(m.serie.semana[ini]),
    data(somarSemanas(m.previsoes[m.previsoes.length - 1].semana, 1))];
  const div = document.createElement('div');
  div.append(linhaCasos(m, ini, dominio, log), faixaNiveis(m, ini, dominio));
  return div;
}

/** Casos das últimas semanas, semanas incompletas, previsão com faixa de 80% e limiares. */
function linhaCasos(m: Municipio, ini: number, dominio: [Date, Date], log: boolean): Element {
  const c = cores();
  const s = m.serie;
  const total = s.semana.length;
  const confirmadas = total - m.lacuna;
  const sem = s.semana.slice(ini);
  const conf = pontos(sem.slice(0, confirmadas - ini), s.casos.slice(ini, confirmadas));
  // As semanas incompletas ligam-se à última confirmada para a linha não ficar solta
  const incompletas = pontos(s.semana.slice(confirmadas - 1), s.casos.slice(confirmadas - 1));
  const prev = m.previsoes.map((p) => ({ semana: data(p.semana), casos: p.casos, inf: p.casos_inf, sup: p.casos_sup }));
  // A previsão parte da última semana confirmada: o traço fino mostra de onde ela sai
  const partida = [{ semana: data(s.semana[confirmadas - 1]), casos: s.casos[confirmadas - 1] }, prev[0]];

  // Limiares: os da série e, nas semanas previstas, os da temporada de cada semana
  const limiar = (campo: 'limiar_amarelo' | 'limiar_vermelho') => [
    ...pontos(sem, s[campo].slice(ini)),
    ...m.previsoes.map((p) => ({ semana: data(p.semana), valor: p[campo] })),
  ];
  const amarelo = limiar('limiar_amarelo');
  const vermelho = limiar('limiar_vermelho');

  return Plot.plot({
    width: largura(),
    height: 300,
    marginLeft: MARGEM_ESQ,
    marginRight: MARGEM_DIR,
    marginBottom: 8,
    style: { background: 'transparent', color: c.tintaSec, fontSize: '12px' },
    x: { type: 'time', domain: dominio, axis: null },
    y: eixoY(log),
    marks: [
      Plot.areaY(prev, { x: 'semana', y1: 'inf', y2: 'sup', fill: c.faixa, curve: 'monotone-x' }),
      Plot.line(amarelo, { x: 'semana', y: 'valor', stroke: c.nivel[1], strokeWidth: 1.5, strokeDasharray: '5,4',
        curve: 'step-after' }),
      Plot.line(vermelho, { x: 'semana', y: 'valor', stroke: c.nivel[2], strokeWidth: 1.5, strokeDasharray: '5,4',
        curve: 'step-after' }),
      Plot.line(conf, { x: 'semana', y: 'valor', stroke: c.tinta, strokeWidth: 2 }),
      Plot.line(incompletas, { x: 'semana', y: 'valor', stroke: c.tinta, strokeWidth: 2, strokeDasharray: '2,3' }),
      Plot.dot(incompletas.slice(1), { x: 'semana', y: 'valor', r: 4, fill: c.fundo, stroke: c.tinta, strokeWidth: 1.5 }),
      Plot.line(partida, { x: 'semana', y: 'casos', stroke: c.previsto, strokeWidth: 1.5, strokeDasharray: '2,3' }),
      Plot.line(prev, { x: 'semana', y: 'casos', stroke: c.previsto, strokeWidth: 2 }),
      Plot.dot(prev, { x: 'semana', y: 'casos', r: 4, fill: c.previsto, stroke: c.fundo, strokeWidth: 2 }),
      Plot.tip([...conf.map((p) => ({ ...p, tipo: 'confirmado' })),
        ...incompletas.slice(1).map((p) => ({ ...p, tipo: 'estimativa nowcast' }))],
      Plot.pointerX({ x: 'semana', y: 'valor', title: (p: Ponto & { tipo: string }) =>
        `Semana de ${diaMesAno(fmtIso(p.semana))}\n${n(p.valor)} casos (${p.tipo})` })),
      Plot.tip(prev, Plot.pointerX({ x: 'semana', y: 'casos', title: (p: (typeof prev)[number]) =>
        `Semana de ${diaMesAno(fmtIso(p.semana))}\nPrevisto: ${n(p.casos)} casos\nFaixa de 80%: ${n(p.inf)} a ${n(p.sup)}` })),
    ],
  });
}

/** Faixa com o nível de cada semana: cheio nas confirmadas, hachurado nas previstas (nível mais provável).
 * As semanas incompletas sem previsão ficam em branco. Um triângulo no eixo marca a última semana confirmada,
 * de onde partem as previsões. */
function faixaNiveis(m: Municipio, ini: number, dominio: [Date, Date]): Element {
  const c = cores();
  const meiaSemana = 3.5 * 86_400_000; // a célula fica centrada no ponto da semana, como na linha
  const celula = (sem: string, nivel: Nivel, previsto: boolean) => {
    const t = data(sem).getTime();
    return { semana: data(sem), x1: new Date(t - meiaSemana), x2: new Date(t + meiaSemana), linha: 'Nível', nivel,
      previsto };
  };
  const confirmadas = m.serie.semana.slice(ini).flatMap((sem, i) => {
    const nivel = m.serie.nivel[ini + i];
    return nivel == null ? [] : [celula(sem, nivel, false)];
  });
  const previstas = m.previsoes.map((p) => celula(p.semana, p.nivel, true));
  const id = `hachura-${++faixas}`;
  const svg = Plot.plot({
    width: largura(),
    height: 30 + 34,
    marginLeft: MARGEM_ESQ,
    marginRight: MARGEM_DIR,
    marginTop: 4,
    marginBottom: 36,
    style: { background: 'transparent', color: c.tintaSec, fontSize: '12px' },
    x: { type: 'time', label: null, domain: dominio, tickFormat: mesAno, tickSize: 0, tickPadding: 16 },
    y: { domain: ['Nível'], label: null, padding: 0.12 },
    color: { type: 'ordinal', domain: [0, 1, 2], range: c.nivel },
    marks: [
      Plot.rect(confirmadas, { x1: 'x1', x2: 'x2', y: 'linha', fill: 'nivel', inset: 0.5, clip: true }),
      // Previstas: listras na cor do nível (padrão SVG acrescentado abaixo) e contorno na mesma cor
      ...([0, 1, 2] as Nivel[]).map((nv) => Plot.rect(previstas.filter((x) => x.nivel === nv), {
        x1: 'x1', x2: 'x2', y: 'linha', fill: `url(#${id}-${nv})`, stroke: c.nivel[nv], strokeWidth: 1, inset: 1,
        clip: true })),
      Plot.text([data(m.confirmada.semana)], { x: (d: Date) => d, frameAnchor: 'bottom', dy: 8, text: () => '▲',
        fill: c.tinta, fontSize: 11, title: () => `Última semana confirmada (${diaMesAno(m.confirmada.semana)})` }),
      Plot.tip([...confirmadas, ...previstas], Plot.pointerX({ x: 'semana', y: 'linha',
        title: (x: (typeof confirmadas)[number]) => `Semana de ${diaMesAno(fmtIso(x.semana))}
` +
          (x.previsto ? `Nível mais provável (previsto): ${NOMES_NIVEL[x.nivel]}` : `Nível: ${NOMES_NIVEL[x.nivel]}`) })),
    ],
  });
  svg.prepend(hachuras(id, c.nivel));
  return svg;
}

let faixas = 0; // ids únicos para os padrões de hachura

function hachuras(id: string, cores: string[]): SVGDefsElement {
  const ns = 'http://www.w3.org/2000/svg';
  const defs = document.createElementNS(ns, 'defs');
  cores.forEach((cor, nv) => {
    const padrao = document.createElementNS(ns, 'pattern');
    for (const [k, v] of Object.entries({ id: `${id}-${nv}`, width: '6', height: '6', patternUnits: 'userSpaceOnUse',
      patternTransform: 'rotate(45)' })) padrao.setAttribute(k, v);
    const listra = document.createElementNS(ns, 'rect');
    for (const [k, v] of Object.entries({ width: '3', height: '6', fill: cor })) listra.setAttribute(k, v);
    padrao.append(listra);
    defs.append(padrao);
  });
  return defs;
}

function fmtIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export const ROTULOS_LINHA: Record<string, string> = {
  real: 'Aconteceu', 0: 'Na própria semana', 1: '1 semana antes', 2: '2 semanas antes', 3: '3 semanas antes',
  4: '4 semanas antes',
};

/** Avaliação: quadradinhos do que aconteceu e do previsto com cada antecedência. */
export function quadradinhos(m: Municipio, inicio: string, fim: string, antecedencias: number[]): Element {
  const c = cores();
  const linhas = ['real', ...antecedencias.map(String)];
  const celulas: { semana: Date; linha: string; nivel: Nivel; real: Nivel | null }[] = [];
  m.serie.semana.forEach((s, i) => {
    if (s < inicio || s >= fim) return;
    const real = m.serie.nivel[i];
    if (real != null) celulas.push({ semana: data(s), linha: 'real', nivel: real, real });
    for (const a of antecedencias) {
      const v = m.avaliacao.niveis[String(a)]?.[i];
      if (v != null) celulas.push({ semana: data(s), linha: String(a), nivel: v, real });
    }
  });
  const nSemanas = new Set(celulas.map((x) => x.semana.getTime())).size;
  return Plot.plot({
    width: largura(),
    height: 40 + 34 * linhas.length,
    marginLeft: 130,
    marginBottom: 30,
    style: { background: 'transparent', color: c.tintaSec, fontSize: '12px' },
    x: { type: 'band', label: null, padding: nSemanas > 60 ? 0.15 : 0.1,
      tickFormat: (d: Date) => (d.getDate() <= 7 && [0, 3, 6, 9].includes(d.getMonth())
        ? d.toLocaleDateString('pt-BR', { month: '2-digit', year: 'numeric' }) : '') },
    y: { domain: linhas, label: null, tickFormat: (l: string) => ROTULOS_LINHA[l], padding: 0.12 },
    color: { type: 'ordinal', domain: [0, 1, 2], range: c.nivel },
    marks: [
      Plot.cell(celulas, { x: 'semana', y: 'linha', fill: 'nivel', inset: 0 }),
      Plot.tip(celulas, Plot.pointer({ x: 'semana', y: 'linha', title: (x: (typeof celulas)[number]) =>
        `Semana de ${diaMesAno(fmtIso(x.semana))}\n${x.linha === 'real' ? 'Aconteceu' : `Previsto ${ROTULOS_LINHA[x.linha].toLowerCase()}`}: ${NOMES_NIVEL[x.nivel]}` +
        (x.linha !== 'real' && x.real != null ? `\nAconteceu: ${NOMES_NIVEL[x.real]}` : '') })),
    ],
  });
}

/** Avaliação: casos reais e a previsão feita com uma antecedência, com a faixa de 80% e os limiares. */
export function graficoCasosAvaliacao(m: Municipio, antecedencia: number, inicio: string, fim: string,
  log: boolean): Element {
  const c = cores();
  const s = m.serie;
  const idx = s.semana.map((x, i) => [x, i] as const).filter(([x]) => x >= inicio && x < fim).map(([, i]) => i);
  const sem = idx.map((i) => s.semana[i]);
  const p = m.avaliacao.casos[String(antecedencia)];
  const prev = idx.flatMap((i) => (p.previsto[i] == null ? [] : [{
    semana: data(s.semana[i]), casos: p.previsto[i] as number, inf: p.inferior[i] as number, sup: p.superior[i] as number,
    real: s.casos[i] }]));
  return Plot.plot({
    width: largura(),
    height: 300,
    marginLeft: 64,
    style: { background: 'transparent', color: c.tintaSec, fontSize: '12px' },
    x: { type: 'time', label: null, tickFormat: mesAno },
    y: eixoY(log),
    marks: [
      Plot.areaY(prev, { x: 'semana', y1: 'inf', y2: 'sup', fill: c.faixa }),
      Plot.line(pontos(sem, idx.map((i) => s.limiar_amarelo[i])), { x: 'semana', y: 'valor', stroke: c.nivel[1],
        strokeWidth: 1.5, strokeDasharray: '5,4', curve: 'step-after' }),
      Plot.line(pontos(sem, idx.map((i) => s.limiar_vermelho[i])), { x: 'semana', y: 'valor', stroke: c.nivel[2],
        strokeWidth: 1.5, strokeDasharray: '5,4', curve: 'step-after' }),
      Plot.line(pontos(sem, idx.map((i) => s.casos[i])), { x: 'semana', y: 'valor', stroke: c.mudo, strokeWidth: 1.5 }),
      Plot.line(prev, { x: 'semana', y: 'casos', stroke: c.previsto, strokeWidth: 2 }),
      Plot.tip(prev, Plot.pointerX({ x: 'semana', y: 'casos', title: (x: (typeof prev)[number]) =>
        `Semana de ${diaMesAno(fmtIso(x.semana))}\nAconteceu: ${n(x.real)} casos\nPrevisto: ${n(x.casos)} (${n(x.inf)} a ${n(x.sup)})` })),
    ],
  });
}
