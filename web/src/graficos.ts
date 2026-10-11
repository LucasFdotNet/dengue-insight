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

/** Indicadores: casos das últimas semanas, semanas incompletas, previsão com faixa de 80% e limiares. */
export function graficoCasos(m: Municipio, semanas: number, log: boolean): Element {
  const c = cores();
  const s = m.serie;
  const total = s.semana.length;
  const ini = Math.max(0, total - semanas);
  const confirmadas = total - m.lacuna;
  const sem = s.semana.slice(ini);
  const conf = pontos(sem.slice(0, confirmadas - ini), s.casos.slice(ini, confirmadas));
  // As semanas incompletas ligam-se à última confirmada para a linha não ficar solta
  const incompletas = pontos(s.semana.slice(confirmadas - 1), s.casos.slice(confirmadas - 1));
  const prev = m.previsoes.map((p) => ({ semana: data(p.semana), casos: p.casos, inf: p.casos_inf, sup: p.casos_sup }));

  // Limiares: os da série e, nas semanas previstas, os da temporada de cada semana
  const limiar = (campo: 'limiar_amarelo' | 'limiar_vermelho') => [
    ...pontos(sem, s[campo].slice(ini)),
    ...m.previsoes.map((p) => ({ semana: data(p.semana), valor: p[campo] })),
  ];
  const amarelo = limiar('limiar_amarelo');
  const vermelho = limiar('limiar_vermelho');
  const fim = data(somarSemanas(m.previsoes[m.previsoes.length - 1].semana, 1));

  return Plot.plot({
    width: largura(),
    height: 320,
    marginLeft: 64,
    style: { background: 'transparent', color: c.tintaSec, fontSize: '12px' },
    x: { type: 'time', label: null, domain: [data(sem[0]), fim], tickFormat: mesAno },
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
      Plot.line(prev, { x: 'semana', y: 'casos', stroke: c.previsto, strokeWidth: 2 }),
      Plot.dot(prev, { x: 'semana', y: 'casos', r: 4, fill: c.previsto, stroke: c.fundo, strokeWidth: 2 }),
      Plot.tip([...conf.map((p) => ({ ...p, tipo: 'confirmado' })),
        ...incompletas.slice(1).map((p) => ({ ...p, tipo: 'semana incompleta (estimativa)' }))],
      Plot.pointerX({ x: 'semana', y: 'valor', title: (p: Ponto & { tipo: string }) =>
        `Semana de ${diaMesAno(fmtIso(p.semana))}\n${n(p.valor)} casos (${p.tipo})` })),
      Plot.tip(prev, Plot.pointerX({ x: 'semana', y: 'casos', title: (p: (typeof prev)[number]) =>
        `Semana de ${diaMesAno(fmtIso(p.semana))}\nPrevisto: ${n(p.casos)} casos\nFaixa de 80%: ${n(p.inf)} a ${n(p.sup)}` })),
    ],
  });
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
