import type { AvaliacaoGeral, Indice, Municipio, Previsao } from './dados';
import { graficoCasos } from './graficos';
import { metrica } from './avaliacao';
import { diaMes, el, n, pct, periodoSemana, se, seloNivel } from './formato';

const PERIODOS: [string, number][] = [['6 meses', 26], ['1 ano', 52], ['2 anos', 104]];
let periodo = 52;
let escalaLog = false;

function card(titulo: string, classe: string, ...conteudo: (Node | string | null | false)[]): HTMLElement {
  return el('section', { class: `card ${classe}` }, el('h3', {}, titulo), ...conteudo);
}

function cardConfirmado(m: Municipio): HTMLElement {
  const c = m.confirmada;
  return card('Último nível confirmado', 'confirmado',
    el('div', { class: 'destaque' }, seloNivel(c.nivel)),
    el('p', { class: 'valor' }, `${n(c.casos)} casos`),
    el('p', {}, `Semana de ${periodoSemana(c.semana)} (${se(c.se)}).`),
    el('p', { class: 'nota' }, 'As 2 semanas seguintes ainda estão recebendo notificações; o nível só é confirmado depois disso.'));
}

function cardAlerta(m: Municipio, av: AvaliacaoGeral): HTMLElement {
  const a = m.alerta;
  const ate = m.previsoes[m.previsoes.length - 1].semana;
  const corretos = metrica(av, 'mobilizacao', 'validacao_cruzada', 2, 'Modelo: alerta de vermelho', 'alarmes_corretos');
  const antes = metrica(av, 'mobilizacao', 'validacao_cruzada', 2, 'Modelo: alerta de vermelho', 'avisadas_antes_dos_dados');
  const fins = metrica(av, 'desmobilizacao', 'validacao_cruzada', 2, 'Modelo: nível previsto em S+2 deixa o vermelho',
    'fins_indicados_antes_dos_dados');
  const prematuros = metrica(av, 'desmobilizacao', 'validacao_cruzada', 2,
    'Modelo: nível previsto em S+2 deixa o vermelho', 'avisos_prematuros_por_episodio');
  const confianca = (texto: string) => el('p', { class: 'nota' }, texto);
  switch (a.estado) {
    case 'alerta':
      return card('Alerta de epidemia', 'alerta ativo',
        el('div', { class: 'destaque' }, seloNivel(2, 'Alerta')),
        el('p', { class: 'valor' }, `${pct(a.p_vermelho_max)} de chance`),
        el('p', {}, `de o município entrar no nível epidêmico nas próximas 2 a 4 semanas (até ${diaMes(ate)}). ` +
          'É o momento de considerar a mobilização.'),
        confianca(`Nos testes com dados do passado, ${pct(corretos?.valor)} dos alertas se confirmaram, e ` +
          `${pct(antes?.valor)} das epidemias foram avisadas antes de os dados mostrarem o início.`));
    case 'sem_alerta':
      return card('Sem alerta de epidemia', 'alerta',
        el('div', { class: 'destaque' }, el('span', { class: 'selo neutro' }, 'Sem alerta')),
        el('p', { class: 'valor' }, `${pct(a.p_vermelho_max)} de chance`),
        el('p', {}, `de nível epidêmico nas próximas 2 a 4 semanas (até ${diaMes(ate)}). ` +
          `O alerta acende a partir de ${pct(a.corte)}.`),
        confianca(`Quando acende, o alerta se confirma em cerca de ${pct(corretos?.valor)} das vezes.`));
    case 'epidemia_continua':
      return card('Em epidemia', 'alerta ativo',
        el('div', { class: 'destaque' }, seloNivel(2, 'Epidemia em curso')),
        el('p', {}, 'O nível epidêmico deve continuar nas próximas 2 semanas. Mantenha as ações em curso.'),
        confianca(`Quando o fim se aproxima, o painel indica: ${pct(fins?.valor)} dos fins de epidemia foram ` +
          'indicados antes de os dados os mostrarem.'));
    case 'fim_indicado':
      return card('Em epidemia, com sinal de fim', 'alerta',
        el('div', { class: 'destaque' }, seloNivel(1, 'Sinal de fim')),
        el('p', {}, 'O município deve sair do nível epidêmico em até 2 semanas. É o momento de planejar a desmobilização.'),
        confianca(`Nos testes, ${pct(fins?.valor)} dos fins de epidemia foram indicados antes de os dados os ` +
          `mostrarem, com cerca de ${n(prematuros?.valor)} sinal antecipado por epidemia.`));
  }
}

function cardNotificados(m: Municipio): HTMLElement {
  const atual = m.recentes[m.recentes.length - 1];
  const anterior = m.recentes.length > 1 ? m.recentes[0] : null;
  return card('Casos notificados até o momento', 'notificados',
    el('p', { class: 'valor' }, n(atual.notificados)),
    el('p', {}, `Semana de ${periodoSemana(atual.semana)} (${se(atual.se)}), ainda incompleta.`),
    el('p', {}, `Estimativa do InfoDengue, que corrige o atraso das notificações: ${n(atual.estimados)} ` +
      `(entre ${n(atual.estimados_min)} e ${n(atual.estimados_max)}).`),
    anterior && el('p', {}, `Semana anterior (${diaMes(anterior.semana)}): ${n(anterior.notificados)} notificados; ` +
      `estimativa de ${n(anterior.estimados)}.`),
    el('p', { class: 'nota cuidado' }, 'Provavelmente subnotificado: as notificações de uma semana continuam chegando ' +
      'por várias semanas. Para a semana mais recente, o número de notificados pode mais que dobrar.'));
}

function cardLimiares(m: Municipio): HTMLElement {
  const [atual, proxima] = m.limiares;
  const muda = m.previsoes.some((p) => p.limiar_vermelho !== m.previsoes[0].limiar_vermelho);
  return card(`Limiares da temporada ${atual.temporada}`, 'limiares',
    el('dl', {},
      el('dt', {}, seloNivel(1, 'Pré-epidêmico')), el('dd', {}, `${n(atual.pre_epidemico)} casos por semana`),
      el('dt', {}, seloNivel(2, 'Epidêmico')), el('dd', {}, `${n(atual.epidemico)} casos por semana`)),
    muda && el('p', {}, `A partir da ${se(proxima.inicio_se)}, temporada ${proxima.temporada}: ` +
      `${n(proxima.pre_epidemico)} e ${n(proxima.epidemico)} casos por semana.`),
    el('p', { class: 'nota' }, 'Calculados pelo Método da Epidemia Móvel (MEM), como no InfoDengue, com as ' +
      'temporadas anteriores do município. Mudam a cada temporada, na semana epidemiológica 41.'));
}

function tabelaPrevisoes(m: Municipio): HTMLElement {
  const titulo = (p: Previsao) => (p.antecedencia === 0 ? 'Esta semana' : `Em ${p.antecedencia} semana${p.antecedencia > 1 ? 's' : ''}`);
  const linha = (rotulo: string, f: (p: Previsao) => Node | string) =>
    el('tr', {}, el('th', { scope: 'row' }, rotulo), ...m.previsoes.map((p) => el('td', {}, f(p))));
  return el('div', { class: 'tabela-rolagem' }, el('table', { class: 'previsoes' },
    el('thead', {}, el('tr', {}, el('th', {}, ''), ...m.previsoes.map((p) =>
      el('th', { scope: 'col' }, titulo(p), el('br'), el('span', { class: 'sub' }, periodoSemana(p.semana)))))),
    el('tbody', {},
      linha('Nível mais provável', (p) => seloNivel(p.nivel)),
      linha('Chance de nível epidêmico', (p) => pct(p.p_vermelho)),
      linha('Casos aproximados', (p) => el('span', {}, n(p.casos), el('br'),
        el('span', { class: 'sub' }, `${n(p.casos_inf)} a ${n(p.casos_sup)}`))))));
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
    item('linha-tinta', 'casos (semanas confirmadas)'), item('linha-pontilhada', 'semanas incompletas (estimativa)'),
    item('linha-azul', 'casos previstos'), item('faixa-azul', 'faixa provável (80%)'),
    item('tracejado-amarelo', 'limiar pré-epidêmico'), item('tracejado-vermelho', 'limiar epidêmico'));
}

export function renderIndicadores(alvo: HTMLElement, m: Municipio, indice: Indice, av: AvaliacaoGeral): void {
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
    el('div', { class: 'cards' }, cardConfirmado(m), cardAlerta(m, av), cardNotificados(m), cardLimiares(m)),
    el('section', { class: 'card largo' }, el('h3', {}, 'Próximas semanas'),
      el('p', { class: 'nota' }, `Previsões feitas a partir da última semana confirmada (${diaMes(m.confirmada.semana)}).`),
      tabelaPrevisoes(m)),
    blocoGrafico,
  );
  desenhar();
}
