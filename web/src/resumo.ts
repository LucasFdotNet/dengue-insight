import type { Indice, Municipio } from './dados';
import { CLASSE_NIVEL, DESCRICAO_NIVEL, diaMes, el, n, pct, periodoSemana, seloNivel, SIGNIFICADO_NIVEL } from './formato';

// Visão para a população: linguagem simples, sem limiares, quantis nem faixa de 80%

const FONTE_CUIDADOS = 'https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue';

// Números arredondados: a leitura rápida não precisa da unidade
function aprox(x: number): string {
  const passo = x < 10 ? 1 : x < 100 ? 5 : x < 1000 ? 10 : 100;
  return n(Math.round(x / passo) * passo);
}

function fraseAlerta(m: Municipio): string {
  const a = m.alerta;
  switch (a.estado) {
    case 'alerta':
      return `Há alerta de epidemia: a chance de epidemia nas próximas 4 semanas é alta (${pct(a.p_vermelho_max)}).`;
    case 'sem_alerta':
      return `Não há alerta de epidemia para as próximas 4 semanas (chance estimada: ${pct(a.p_vermelho_max)}).`;
    case 'epidemia_continua':
      return 'A epidemia deve continuar nas próximas 2 semanas.';
    case 'fim_indicado':
      return 'A epidemia deve terminar nas próximas 2 semanas.';
  }
}

// Tendência pela mesma regra da tendência relativa do projeto (decisão 7): variação de 20% e de 5 casos
function fraseTendencia(m: Municipio): HTMLElement {
  const antes = m.confirmada.casos;
  const depois = m.previsoes[m.previsoes.length - 1];
  const dif = depois.casos - antes;
  const [seta, texto] = Math.abs(dif) < 5 || Math.abs(dif) < 0.2 * Math.max(antes, 1)
    ? ['→', 'ficar estáveis'] : dif > 0 ? ['↑', 'subir'] : ['↓', 'cair'];
  return el('p', { class: 'tendencia' }, el('span', { class: 'seta', 'aria-hidden': 'true' }, seta),
    el('span', {}, el('strong', {}, `Os casos devem ${texto}`),
      `: de cerca de ${aprox(antes)} por semana em ${diaMes(m.confirmada.semana)} para cerca de ` +
      `${aprox(depois.casos)} por semana em ${diaMes(depois.semana)}.`));
}

// Faixa das próximas semanas: um bloco por semana, com a cor do nível previsto
function semanas(m: Municipio): HTMLElement {
  const rotulo = (h: number) => (h === 0 ? 'Esta semana' : `Em ${h} semana${h > 1 ? 's' : ''}`);
  return el('ol', { class: 'semanas', 'aria-label': 'Nível previsto por semana' }, ...m.previsoes.map((p) =>
    el('li', { class: `semana ${CLASSE_NIVEL[p.nivel]}` },
      el('span', { class: 'quando' }, rotulo(p.antecedencia)),
      el('span', { class: 'sub' }, periodoSemana(p.semana)),
      seloNivel(p.nivel))));
}

export function renderResumo(alvo: HTMLElement, m: Municipio, indice: Indice): void {
  const atual = m.previsoes.find((p) => p.antecedencia === 0);
  const previsto = atual == null
    ? el('p', { class: 'frase' }, `Ainda não há previsão para ${m.nome}.`)
    : el('div', { class: 'niveis' },
      el('div', {}, el('span', { class: 'sub' }, 'Previsto para esta semana'), seloNivel(atual.nivel)),
      el('p', { class: 'frase' }, el('strong', {}, `Nível ${DESCRICAO_NIVEL[atual.nivel]}`),
        `: ${SIGNIFICADO_NIVEL[atual.nivel]}.`));

  alvo.replaceChildren(
    el('section', { class: 'card largo resumo' }, el('h3', {}, `Como está a dengue em ${m.nome} (${m.uf})`),
      previsto,
      el('p', { class: 'nota' }, 'O nível desta semana já é uma previsão, porque as notificações levam semanas para chegar.')),
    el('p', { class: 'contexto' }, `Dados até a semana de ${periodoSemana(m.semana_atual)}; ` +
      `atualizado em ${indice.gerado_em.split(' ')[0].split('-').reverse().join('/')}.`),
    el('section', { class: 'card largo resumo' }, el('h3', {}, 'Próximas semanas'),
      semanas(m),
      el('p', { class: 'frase' }, fraseAlerta(m)),
      fraseTendencia(m)),
    el('section', { class: 'card largo resumo texto' }, el('h3', {}, 'O que você pode fazer'),
      el('ul', {},
        el('li', {}, 'Retire ou esvazie recipientes que possam acumular água e virar criadouro do mosquito.'),
        el('li', {}, 'Mantenha caixas d\'água e outros reservatórios tampados, e desentupa calhas, lajes e ralos.'),
        el('li', {}, 'Use telas nas janelas e repelente.'),
        el('li', {}, 'Com febre de início repentino e outros sintomas, como dor de cabeça ou cansaço forte, procure um ' +
          'serviço de saúde; beba bastante líquido e descanse. Em caso de sangramento ou piora, não se automedique e ' +
          'procure a urgência.')),
      el('p', { class: 'nota' }, 'Fonte: Ministério da Saúde, ',
        el('a', { href: FONTE_CUIDADOS, target: '_blank', rel: 'noopener' }, 'página Dengue'), '.')),
    el('p', {}, el('a', { href: `#/indicadores/${m.id}` }, 'Ver detalhes do município (Indicadores) →')),
    el('p', { class: 'nota' }, 'Previsões experimentais, de um trabalho acadêmico: não substituem as orientações da ' +
      'Secretaria de Saúde do seu município.'),
  );
}
