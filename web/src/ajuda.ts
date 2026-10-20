import { el, seloNivel } from './formato';

// Esboço: o conteúdo completo depende das definições ainda em discussão
export function renderAjuda(alvo: HTMLElement): void {
  const secao = (titulo: string, ...conteudo: (Node | string)[]) =>
    el('section', { class: 'card largo texto' }, el('h3', {}, titulo), ...conteudo);
  alvo.replaceChildren(
    el('p', { class: 'contexto' }, 'Seção em construção.'),
    secao('Como ler o painel',
      el('p', {}, 'O painel mostra, para cada município, em que nível a dengue está e em que nível deve estar nas ' +
        'próximas semanas, para ajudar a decidir quando mobilizar, manter e desmobilizar recursos.'),
      el('ul', {},
        el('li', {}, seloNivel(0), ' normal: abaixo do limiar pré-epidêmico.'),
        el('li', {}, seloNivel(1), ' elevado: entre os limiares pré-epidêmico e epidêmico.'),
        el('li', {}, seloNivel(2), ' epidêmico: acima do limiar epidêmico.'))),
    secao('Por que o nível "confirmado" é de 2 semanas atrás',
      el('p', {}, 'As notificações de uma semana continuam chegando por várias semanas. Por isso, o painel usa como ' +
        'base a última semana com dados quase completos; as duas mais recentes aparecem no gráfico com a estimativa ' +
        'do InfoDengue que corrige o atraso das notificações (nowcast).')),
    secao('De onde vêm as previsões',
      el('p', {}, 'Um único modelo (LightGBM por quantis, treinado com 100 municípios e com o clima das 4 semanas ' +
        'anteriores) prevê a faixa provável de casos de cada semana. A chance de cada nível sai dessa faixa: é a chance ' +
        'de os casos ficarem abaixo, entre ou acima dos limiares. Por isso os casos previstos e o nível mais provável ' +
        'sempre concordam.')),
    secao('Como os limiares são calculados',
      el('p', {}, 'Pelo Método da Epidemia Móvel (MEM; Vega et al., 2013), com as mesmas configurações do InfoDengue, ' +
        'a partir das temporadas anteriores de cada município (da semana 41 de um ano à 40 do seguinte).')),
    secao('Aviso',
      el('p', {}, 'Trabalho acadêmico (Projeto Integrador IV, UNIVESP). As previsões são experimentais e não devem ser ' +
        'usadas como base para decisões oficiais de vigilância ou de saúde pública. Dados: InfoDengue e Open-Meteo.')),
  );
}
