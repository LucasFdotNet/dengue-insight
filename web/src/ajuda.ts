import type { Nivel } from './dados';
import { DESCRICAO_NIVEL, el, seloNivel, SIGNIFICADO_NIVEL } from './formato';

export function renderAjuda(alvo: HTMLElement): void {
  const secao = (titulo: string, ...conteudo: (Node | string)[]) =>
    el('section', { class: 'card largo texto' }, el('h3', {}, titulo), ...conteudo);
  const item = (titulo: string, texto: string) => el('li', {}, el('strong', {}, titulo), ` ${texto}`);
  alvo.replaceChildren(
    secao('O que o painel mostra',
      el('p', {}, 'Para cada um dos 115 municípios, em que nível a dengue está e em que nível deve estar nas próximas ' +
        'semanas, para ajudar a decidir quando mobilizar, manter e desmobilizar ações e equipes.'),
      el('ul', {},
        item('Indicadores:', 'a situação do município, com os níveis, os alertas, os limiares, as previsões das ' +
          'próximas semanas e o gráfico de casos.'),
        item('Resumo:', 'a mesma situação em linguagem simples, com os cuidados contra a dengue.'),
        item('Avaliação:', 'como as previsões teriam acertado no passado, no município e em todos eles.')),
      el('p', {}, 'Os municípios marcados com * são do conjunto de teste: o modelo nunca foi treinado com eles.')),
    secao('Os níveis',
      el('p', {}, 'Cada semana tem um nível, dado pelos casos e pelos dois limiares do município:'),
      el('ul', {}, ...([0, 1, 2] as Nivel[]).map((nv) =>
        el('li', {}, seloNivel(nv), ` ${DESCRICAO_NIVEL[nv]}: ${SIGNIFICADO_NIVEL[nv]}.`))),
      el('p', {}, 'Os limiares vêm do histórico do próprio município, pelo Método da Epidemia Móvel (MEM), o mesmo ' +
        'usado pelo InfoDengue, e são refeitos a cada temporada (da semana 41 de um ano à 40 do seguinte). Onde a ' +
        'dengue chegou há pouco ou passou a ter muito mais casos, o município pode ficar no nível epidêmico por um ' +
        'ano ou mais, até as novas temporadas entrarem no cálculo.')),
    secao('Por que o nível confirmado é de 2 semanas atrás',
      el('p', {}, 'As notificações de uma semana continuam chegando por várias semanas. Por isso, o painel parte da ' +
        'última semana com dados quase completos. As duas semanas mais recentes aparecem no gráfico com a estimativa ' +
        'do InfoDengue que corrige o atraso (nowcast), e o nível delas já é uma previsão.')),
    secao('Previsões',
      el('p', {}, 'Para a semana atual e as 4 seguintes, o painel mostra:'),
      el('ul', {},
        item('Nível mais provável:', 'o nível com a maior chance na semana.'),
        item('Chance de epidemia:', 'a chance de os casos da semana ficarem acima do limiar epidêmico.'),
        item('Casos aproximados:', 'o valor mais provável e, embaixo, a faixa onde os casos devem cair em cerca de ' +
          '8 de cada 10 semanas (faixa de 80%).')),
      el('p', {}, 'Um único modelo de aprendizado de máquina (LightGBM), treinado com 100 municípios, prevê a faixa ' +
        'de casos a partir dos casos e do clima das semanas anteriores. A chance de cada nível sai dessa faixa, ' +
        'comparada aos limiares; por isso os casos e o nível previstos sempre concordam.')),
    secao('Alertas',
      el('ul', {},
        item('Alerta:', 'acende quando o município não está no nível epidêmico e a chance de epidemia, de 2 a 4 semanas ' +
          'à frente, passa do corte mostrado no cartão ("alerta a partir de…"). O corte é escolhido com o histórico ' +
          'para que cerca de metade dos alertas se confirme.'),
        item('Epidemia em curso ou sinal de fim:', 'quando o município já está no nível epidêmico, o cartão diz se ' +
          'ele deve continuar nesse nível ou sair dele nas próximas 2 semanas.')),
      el('p', {}, 'O quanto o alerta e o sinal de fim acertaram no passado está na aba Avaliação.')),
    secao('Aviso',
      el('p', {}, 'Trabalho acadêmico (Projeto Integrador IV, UNIVESP). As previsões são experimentais e não devem ser ' +
        'usadas como base para decisões oficiais de vigilância ou de saúde pública. Dados: InfoDengue (casos e ' +
        'nowcast) e Open-Meteo (clima).')),
  );
}
