import type { AvaliacaoGeral, LinhaRobustez, Municipio } from './dados';
import { graficoCasosAvaliacao, quadradinhos, ROTULOS_LINHA } from './graficos';
import { decimal, el, pct, somarSemanas } from './formato';

const ANTECEDENCIAS = [0, 1, 2, 3, 4];
const INICIO_AVALIACAO = '2019-01-01';

let anoInicio: number | null = null; // null: os últimos 2 anos
let antecedenciaCasos = 2;
let escalaLog = true;

export function metrica(av: AvaliacaoGeral, teste: string, conjunto: string, lacuna: number, metodo: string,
  nome: string): LinhaRobustez | undefined {
  return av.niveis_robustez.find((r) => r.teste === teste && r.conjunto === conjunto && r.lacuna === lacuna &&
    r.metodo === metodo && r.metrica === nome);
}

const comIc = (r: LinhaRobustez | undefined, f: (x: number | null) => string) =>
  r ? el('span', {}, f(r.valor), el('br'), el('span', { class: 'sub' }, `${f(r.ic95_inf)} a ${f(r.ic95_sup)}`)) : '—';

function tabela(cabecalho: string[], linhas: (Node | string)[][]): HTMLElement {
  return el('div', { class: 'tabela-rolagem' }, el('table', {},
    el('thead', {}, el('tr', {}, ...cabecalho.map((c, i) => el('th', { scope: 'col', class: i ? 'num' : '' }, c)))),
    el('tbody', {}, ...linhas.map(([rotulo, ...valores]) =>
      el('tr', {}, el('th', { scope: 'row' }, rotulo), ...valores.map((v) => el('td', { class: 'num' }, v)))))));
}

// --------------------------------------------------------------- neste município

function resumoMunicipio(m: Municipio): HTMLElement {
  const s = m.serie;
  const linhas = ANTECEDENCIAS.map((a) => {
    let semanas = 0, acertos = 0, acertosPersist = 0, dentro = 0, nCasos = 0;
    s.semana.forEach((sem, i) => {
      const real = s.nivel[i];
      const atraso = i - a - m.lacuna; // semana confirmada quando a previsão foi feita
      if (sem < INICIO_AVALIACAO || real == null || atraso < 0) return;
      const prev = m.avaliacao.niveis[String(a)][i];
      const conhecido = s.nivel[atraso];
      if (prev != null && conhecido != null) {
        semanas++; acertos += Number(prev === real); acertosPersist += Number(conhecido === real);
      }
      const c = m.avaliacao.casos[String(a)];
      if (c.previsto[i] != null && s.casos[i] != null) {
        nCasos++; dentro += Number((s.casos[i] as number) >= (c.inferior[i] as number) &&
          (s.casos[i] as number) <= (c.superior[i] as number));
      }
    });
    return [ROTULOS_LINHA[a], pct(acertos / semanas), pct(acertosPersist / semanas), pct(dentro / nCasos)];
  });
  return tabela(['Previsão feita', 'Acerto do nível', 'Repetir o nível confirmado', 'Casos dentro da faixa de 80%'],
    linhas);
}

function controlesMunicipio(m: Municipio, aoMudar: () => void): HTMLElement {
  const anos = [...new Set(m.serie.semana.filter((s) => s >= INICIO_AVALIACAO).map((s) => Number(s.slice(0, 4))))];
  const ano = el('select', { 'aria-label': 'Período' }, el('option', { value: '' }, 'Últimos 2 anos'),
    ...anos.slice(0, -1).map((a) => el('option', { value: String(a) }, `Jul/${a} a jul/${a + 2}`)));
  ano.value = anoInicio == null ? '' : String(anoInicio);
  ano.addEventListener('change', () => { anoInicio = ano.value ? Number(ano.value) : null; aoMudar(); });
  const ant = el('select', { 'aria-label': 'Antecedência da previsão de casos' },
    ...ANTECEDENCIAS.map((a) => el('option', { value: String(a) }, `Previsão feita ${ROTULOS_LINHA[a].toLowerCase()}`)));
  ant.value = String(antecedenciaCasos);
  ant.addEventListener('change', () => { antecedenciaCasos = Number(ant.value); aoMudar(); });
  const escala = el('select', { 'aria-label': 'Escala' }, el('option', { value: 'log' }, 'Escala logarítmica'),
    el('option', { value: 'linear' }, 'Escala linear'));
  escala.value = escalaLog ? 'log' : 'linear';
  escala.addEventListener('change', () => { escalaLog = escala.value === 'log'; aoMudar(); });
  return el('div', { class: 'controles' }, el('label', {}, 'Período ', ano), el('label', {}, ' Casos ', ant),
    el('label', {}, ' ', escala));
}

function blocoMunicipio(m: Municipio): HTMLElement {
  const ultima = m.serie.semana[m.serie.semana.length - 1];
  const corpo = el('div', {});
  const desenhar = () => {
    const inicio = anoInicio == null ? somarSemanas(ultima, -103) : `${anoInicio}-07-01`;
    const fim = anoInicio == null ? somarSemanas(ultima, 1) : `${anoInicio + 2}-07-01`;
    corpo.replaceChildren(
      controlesMunicipio(m, desenhar),
      el('h4', {}, 'Nível: o que aconteceu e o que foi previsto'),
      el('p', { class: 'nota' }, 'Cada coluna é uma semana. Em cada linha de previsão, a cor é o nível mais provável ' +
        `previsto para aquela semana, com os dados confirmados disponíveis na época (${m.lacuna} semanas de atraso). A previsão ` +
        'acertou quando a cor é a mesma da linha "Aconteceu".'),
      el('div', { class: 'grafico' }, quadradinhos(m, inicio, fim, ANTECEDENCIAS)),
      el('h4', {}, 'Casos: o que aconteceu e o que foi previsto'),
      el('div', { class: 'grafico' }, graficoCasosAvaliacao(m, antecedenciaCasos, inicio, fim, escalaLog)),
      el('div', { class: 'legenda' },
        ...[['linha-mudo', 'casos (aconteceu)'], ['linha-azul', 'casos previstos'], ['faixa-azul', 'faixa provável (80%)'],
          ['tracejado-amarelo', 'limiar pré-epidêmico'], ['tracejado-vermelho', 'limiar epidêmico']]
          .map(([c, t]) => el('span', { class: 'item' }, el('span', { class: `chave ${c}` }), t))),
      el('h4', {}, `Acerto neste município (de ${INICIO_AVALIACAO.slice(0, 4)} em diante)`),
      resumoMunicipio(m),
    );
  };
  desenhar();
  const papel = m.papel === 'validacao'
    ? 'Município de validação: o modelo nunca viu os seus dados durante o desenvolvimento.'
    : 'Município de treino: as previsões vêm de modelos treinados sem ele (validação cruzada por município).';
  return el('section', { class: 'card largo' }, el('h3', {}, `${m.nome} (${m.uf})`), el('p', { class: 'nota' }, papel),
    corpo);
}

// --------------------------------------------------------------- geral

function blocoGeral(av: AvaliacaoGeral, lacuna: number): HTMLElement {
  const M = 'Modelo: alerta de vermelho';
  const R = 'Regra simples (subindo há 2 semanas)';
  const D = 'Modelo: nível previsto em S+2 deixa o vermelho';
  const Q = 'Regra simples (caindo há 2 semanas)';
  const cv = 'validacao_cruzada', vf = 'validacao_final';
  const g = (t: string, c: string, l: number, m: string, k: string, f: (x: number | null) => string) =>
    comIc(metrica(av, t, c, l, m, k), f);
  const falsos = (x: number | null) => decimal(x);
  const nAvisos = (x: number | null) => decimal(x, 1);

  const mobilizacao = tabela(['', '100 municípios', '15 nunca vistos', 'Regra simples (100 municípios)'], [
    ['Epidemias avisadas antes de os dados mostrarem o início',
      g('mobilizacao', cv, lacuna, M, 'avisadas_antes_dos_dados', pct), g('mobilizacao', vf, lacuna, M, 'avisadas_antes_dos_dados', pct),
      g('mobilizacao', cv, lacuna, R, 'avisadas_antes_dos_dados', pct)],
    ['Epidemias avisadas antes de começar', g('mobilizacao', cv, lacuna, M, 'epidemias_avisadas', pct),
      g('mobilizacao', vf, lacuna, M, 'epidemias_avisadas', pct), g('mobilizacao', cv, lacuna, R, 'epidemias_avisadas', pct)],
    ['Alertas que se confirmaram', g('mobilizacao', cv, lacuna, M, 'alarmes_corretos', pct),
      g('mobilizacao', vf, lacuna, M, 'alarmes_corretos', pct), g('mobilizacao', cv, lacuna, R, 'alarmes_corretos', pct)],
    ['Alarmes falsos por município por ano', g('mobilizacao', cv, lacuna, M, 'alarmes_falsos_por_municipio_ano', falsos),
      g('mobilizacao', vf, lacuna, M, 'alarmes_falsos_por_municipio_ano', falsos),
      g('mobilizacao', cv, lacuna, R, 'alarmes_falsos_por_municipio_ano', falsos)],
  ]);
  const desmobilizacao = tabela(['', '100 municípios', '15 nunca vistos', 'Regra de queda (100 municípios)'], [
    ['Fins indicados antes de os dados os mostrarem', g('desmobilizacao', cv, lacuna, D, 'fins_indicados_antes_dos_dados', pct),
      g('desmobilizacao', vf, lacuna, D, 'fins_indicados_antes_dos_dados', pct),
      g('desmobilizacao', cv, lacuna, Q, 'fins_indicados_antes_dos_dados', pct)],
    ['Fins indicados nas 2 semanas antes', g('desmobilizacao', cv, lacuna, D, 'fins_indicados', pct),
      g('desmobilizacao', vf, lacuna, D, 'fins_indicados', pct), g('desmobilizacao', cv, lacuna, Q, 'fins_indicados', pct)],
    ['Sinais de fim antecipados por epidemia', g('desmobilizacao', cv, lacuna, D, 'avisos_prematuros_por_episodio', nAvisos),
      g('desmobilizacao', vf, lacuna, D, 'avisos_prematuros_por_episodio', nAvisos),
      g('desmobilizacao', cv, lacuna, Q, 'avisos_prematuros_por_episodio', nAvisos)],
  ]);
  const atraso = tabela(['100 municípios', 'Sem atraso', '2 semanas', '3 semanas', '4 semanas'], [
    ['Epidemias avisadas antes de começar', ...[0, 2, 3, 4].map((l) => g('mobilizacao', cv, l, M, 'epidemias_avisadas', pct))],
    ['Regra simples: avisadas antes de começar', ...[0, 2, 3, 4].map((l) => g('mobilizacao', cv, l, R, 'epidemias_avisadas', pct))],
    ['Alertas que se confirmaram', ...[0, 2, 3, 4].map((l) => g('mobilizacao', cv, l, M, 'alarmes_corretos', pct))],
    ['Nível em 4 semanas: acerto do modelo', ...[0, 2, 3, 4].map((l) => g('nivel_4_semanas', cv, l, 'Modelo e persistência', 'acerto', pct))],
    ['Nível em 4 semanas: repetir o nível conhecido',
      ...[0, 2, 3, 4].map((l) => g('nivel_4_semanas', cv, l, 'Modelo e persistência', 'acerto_persistencia', pct))],
  ]);
  const nivel = tabela(['Previsão feita', 'Acerto (100 municípios)', 'Repetir o nível confirmado', 'Acerto quando o nível muda',
    'Acerto (15 nunca vistos)'], [2, 3, 4].map((h) => {
    const t = `nivel_${h}_semanas`;
    return [ROTULOS_LINHA[h], g(t, cv, lacuna, 'Modelo e persistência', 'acerto', pct),
      g(t, cv, lacuna, 'Modelo e persistência', 'acerto_persistencia', pct), g(t, cv, lacuna, 'Modelo e persistência', 'acerto_quando_muda', pct),
      g(t, vf, lacuna, 'Modelo e persistência', 'acerto', pct)];
  }));
  const casos = (conjunto: string, k: 'razao_erro' | 'cobertura_80', f: (x: number | null) => string) => (a: number) => {
    const r = av.casos_atraso.find((x) => x.conjunto === conjunto && x.lacuna === lacuna && x.antecedencia === a &&
      x.metrica === k);
    return r ? el('span', {}, f(r.valor), el('br'), el('span', { class: 'sub' }, `${f(r.ic95_inf)} a ${f(r.ic95_sup)}`)) : '—';
  };
  const tabelaCasos = tabela(['Previsão feita', 'Erro em relação a repetir os casos confirmados', 'Casos dentro da faixa de 80%',
    'Erro (15 nunca vistos)', 'Dentro da faixa (15 nunca vistos)'], ANTECEDENCIAS.map((a) => [ROTULOS_LINHA[a],
    casos(cv, 'razao_erro', decimal)(a), casos(cv, 'cobertura_80', pct)(a), casos(vf, 'razao_erro', decimal)(a),
    casos(vf, 'cobertura_80', pct)(a)]));

  return el('section', { class: 'card largo' }, el('h3', {}, 'Todos os municípios'),
    el('p', { class: 'nota' }, `Previsões de ${INICIO_AVALIACAO.slice(0, 4)} em diante, feitas como o painel as faz para ` +
      `este município: com os dados confirmados até ${lacuna} semanas antes (${lacuna === 2 ? 'municípios com estimativa ' +
      'do InfoDengue para as semanas recentes' : 'municípios sem estimativa do InfoDengue para as semanas recentes'}) e ` +
      'modelos que não viram o município (validação cruzada por município nos 100 de treino; os 15 de validação nunca ' +
      'foram usados no desenvolvimento). Abaixo de cada número, o intervalo de confiança de 95%.'),
    el('h4', {}, 'Alerta de epidemia (mobilização)'), mobilizacao,
    el('p', { class: 'nota' }, 'Uma epidemia é um período de 2 semanas ou mais no nível epidêmico. Um alerta se confirma ' +
      'quando uma epidemia começa durante ele ou até 4 semanas depois. A regra simples alerta quando os casos sobem há 2 ' +
      'semanas e passam de metade do limiar epidêmico.'),
    el('h4', {}, 'Sinal de fim de epidemia (desmobilização)'), desmobilizacao,
    el('h4', {}, 'Nível mais provável'), nivel,
    el('h4', {}, 'Casos aproximados'), tabelaCasos,
    el('p', { class: 'nota' }, 'Erro: erro absoluto médio do modelo dividido pelo de repetir os casos da última semana ' +
      'confirmada (abaixo de 1, o modelo erra menos). A faixa de 80% deveria conter o valor real em cerca de 80% das semanas.'),
    el('h4', {}, 'Efeito do atraso das notificações'), atraso,
    el('p', { class: 'nota' }, 'Sem atraso: como se os dados da semana atual já estivessem completos. O painel usa 2 ' +
      'semanas de atraso nos municípios com estimativa do InfoDengue para as semanas recentes e 3 nos demais; 4 semanas é o ' +
      'pior caso.'));
}

export function renderAvaliacao(alvo: HTMLElement, m: Municipio, av: AvaliacaoGeral): void {
  alvo.replaceChildren(
    el('p', { class: 'contexto' }, 'Como o modelo teria se saído no passado, com as mesmas regras do painel. Esta seção ' +
      'serve para avaliar o modelo; para acompanhar o município, use Indicadores.'),
    blocoMunicipio(m), blocoGeral(av, m.lacuna));
}
