import type { Indice, Municipio, Previsao } from './dados';
import { graficoCasos } from './graficos';
import { data, diaMes, el, n, pct, periodoSemana, seloNivel } from './formato';

const PERIODOS: [string, number][] = [['6 meses', 26], ['1 ano', 52], ['2 anos', 104]];
let periodo = 52;
let escalaLog = false;

function card(titulo: string, classe: string, ...conteudo: (Node | string | null | false)[]): HTMLElement {
  return el('section', { class: `card ${classe}` }, el('h3', {}, titulo), ...conteudo);
}

function cardConfirmado(m: Municipio): HTMLElement {
  const c = m.confirmada;
  const dias = Math.round((Date.now() - data(c.semana).getTime()) / 86_400_000);
  return card('Último nível confirmado', 'confirmado',
    el('div', { class: 'destaque' }, seloNivel(c.nivel)),
    el('p', { class: 'valor' }, `${n(c.casos)} casos`),
    el('p', {}, `Semana ${diaMes(c.semana)}; há ${dias}d`));
}

function cardAlerta(m: Municipio): HTMLElement {
  const a = m.alerta;
  const ate = (h: number) => diaMes(m.previsoes.find((p) => p.antecedencia === h)!.semana);
  switch (a.estado) {
    case 'alerta':
      return card('Alertas', 'alerta ativo',
        el('div', { class: 'destaque' }, seloNivel(2, 'Alerta')),
        el('p', { class: 'valor' }, `Chance de ${pct(a.p_vermelho_max)}`),
        el('p', {}, `de nível epidêmico até ${ate(4)} · alerta a partir de ${pct(a.corte)}`));
    case 'sem_alerta':
      return card('Alertas', 'alerta',
        el('div', { class: 'destaque' }, el('span', { class: 'selo neutro' }, 'Sem alerta')),
        el('p', { class: 'valor' }, `Chance de ${pct(a.p_vermelho_max)}`),
        el('p', {}, `de nível epidêmico até ${ate(4)} · alerta a partir de ${pct(a.corte)}`));
    case 'epidemia_continua':
      return card('Alertas', 'alerta ativo',
        el('div', { class: 'destaque' }, seloNivel(2, 'Epidemia em curso')),
        el('p', {}, `Nível epidêmico deve continuar até ${ate(2)}`));
    case 'fim_indicado':
      return card('Alertas', 'alerta',
        el('div', { class: 'destaque' }, seloNivel(1, 'Sinal de fim')),
        el('p', {}, `Deve sair do nível epidêmico até ${ate(2)}`));
  }
}

function cardLimiares(m: Municipio): HTMLElement {
  const [atual] = m.limiares;
  return card('Limiares epidêmicos', 'limiares',
    el('dl', {},
      el('dt', {}, seloNivel(1, 'Pré-epidêmico')), el('dd', {}, `${n(atual.pre_epidemico)} casos / semana`),
      el('dt', {}, seloNivel(2, 'Epidêmico')), el('dd', {}, `${n(atual.epidemico)} casos / semana`)));
}

// "<1%" em vez de "menos de 1%": cabe na coluna da tabela
const pctCurto = (x: number) => (x > 0 && x < 0.005 ? '<1%' : pct(x));
const casosFaixa = (p: Previsao, sep = ' a ') => el('span', {}, n(p.casos), el('br'),
  el('span', { class: 'sub' }, `${n(p.casos_inf)}${sep}${n(p.casos_sup)}`));

function tabelaPrevisoes(m: Municipio): HTMLElement {
  // Tela estreita: uma linha por semana, para não precisar rolar para o lado
  if (window.matchMedia('(max-width: 640px)').matches) return tabelaPrevisoesVertical(m);
  const titulo = (p: Previsao) => (p.antecedencia === 0 ? 'Esta semana' : `Em ${p.antecedencia} semana${p.antecedencia > 1 ? 's' : ''}`);
  const linha = (rotulo: string, f: (p: Previsao) => Node | string) =>
    el('tr', {}, el('th', { scope: 'row' }, rotulo), ...m.previsoes.map((p) => el('td', {}, f(p))));
  return el('div', { class: 'tabela-rolagem' }, el('table', { class: 'previsoes' },
    el('thead', {}, el('tr', {}, el('th', {}, ''), ...m.previsoes.map((p) =>
      el('th', { scope: 'col' }, titulo(p), el('br'), el('span', { class: 'sub' }, periodoSemana(p.semana)))))),
    el('tbody', {},
      linha('Nível mais provável', (p) => seloNivel(p.nivel)),
      linha('Chance de nível epidêmico', (p) => pctCurto(p.p_vermelho)),
      linha('Casos aproximados', (p) => casosFaixa(p)))));
}

function tabelaPrevisoesVertical(m: Municipio): HTMLElement {
  return el('div', { class: 'tabela-rolagem' }, el('table', { class: 'previsoes vertical' },
    el('thead', {}, el('tr', {}, ...['Semana', 'Nível', 'Chance de epidemia', 'Casos'].map((t) => el('th', { scope: 'col' }, t)))),
    el('tbody', {}, ...m.previsoes.map((p) => el('tr', {},
      el('th', { scope: 'row' }, diaMes(p.semana), p.antecedencia === 0 && el('br'),
        p.antecedencia === 0 && el('span', { class: 'sub' }, 'atual')),
      el('td', {}, seloNivel(p.nivel)), el('td', {}, pctCurto(p.p_vermelho)), el('td', {}, casosFaixa(p, '–')))))));
}

function controles(aoMudar: () => void): HTMLElement {
  const grupo = (rotulo: string, opcoes: [string, () => boolean, () => void][]) =>
    el('div', { class: 'segmentado', role: 'group', 'aria-label': rotulo }, ...opcoes.map(([texto, ativo, acao]) => {
      const b = el('button', { type: 'button', 'aria-pressed': String(ativo()) }, texto);
      b.addEventListener('click', () => { acao(); aoMudar(); });
      return b;
    }));
  return el('div', { class: 'controles' },
    grupo('Período', PERIODOS.map(([t, v]) => [t, () => periodo === v, () => { periodo = v; }])),
    grupo('Escala', [['Linear', () => !escalaLog, () => { escalaLog = false; }],
      ['Logarítmica', () => escalaLog, () => { escalaLog = true; }]]));
}

function legendaCasos(): HTMLElement {
  const item = (classe: string, texto: string) => el('span', { class: 'item' }, el('span', { class: `chave ${classe}` }), texto);
  return el('div', { class: 'legenda' },
    item('linha-tinta', 'casos (semanas confirmadas)'), item('linha-pontilhada', 'estimativa nowcast'),
    item('linha-azul', 'casos previstos'), item('faixa-azul', 'faixa provável (80%)'),
    item('tracejado-amarelo', 'limiar pré-epidêmico'), item('tracejado-vermelho', 'limiar epidêmico'),
    item('quadrados', 'nível confirmado (verde, amarelo, vermelho)'),
    item('quadrados hachurado', 'nível mais provável (previsto)'),
    el('span', { class: 'item' }, el('span', { class: 'chave-texto', 'aria-hidden': 'true' }, '▲'),
      'última semana confirmada'));
}

export function renderIndicadores(alvo: HTMLElement, m: Municipio, indice: Indice): void {
  const grafico = el('div', { class: 'grafico' });
  const desenhar = () => {
    grafico.replaceChildren(graficoCasos(m, periodo, escalaLog));
    const novo = controles(desenhar);
    blocoGrafico.querySelector('.controles')?.replaceWith(novo);
  };
  const blocoGrafico = el('section', { class: 'card largo' },
    el('h3', {}, 'Casos por semana'), controles(() => desenhar()), grafico, legendaCasos());
  alvo.replaceChildren(
    el('p', { class: 'contexto' }, `Dados até a semana de ${periodoSemana(m.semana_atual)}. ` +
      `Atualizado em ${indice.gerado_em.split(' ')[0].split('-').reverse().join('/')}.`),
    el('div', { class: 'cards' }, cardConfirmado(m), cardAlerta(m), cardLimiares(m)),
    el('section', { class: 'card largo' }, el('h3', {}, 'Próximas semanas'),
      el('p', { class: 'nota' }, `Previsões feitas a partir da última semana confirmada (${diaMes(m.confirmada.semana)}).`),
      tabelaPrevisoes(m)),
    blocoGrafico,
  );
  desenhar();
}
