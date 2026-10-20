import './estilo.css';
import { renderAjuda } from './ajuda';
import { renderAvaliacao } from './avaliacao';
import { carregarAvaliacao, carregarIndice, carregarMunicipio, type Indice } from './dados';
import { el } from './formato';
import { renderIndicadores } from './indicadores';

type Secao = 'indicadores' | 'avaliacao' | 'ajuda';
const SECOES: [Secao, string][] = [['indicadores', 'Indicadores'], ['avaliacao', 'Avaliação'], ['ajuda', 'Ajuda']];
const MUNICIPIO_PADRAO = 'campinas';
const CHAVE_AVISO = 'dengue_insight_aviso';
const PALAVRA_ACEITE = 'entendo';

// Endereço: #/secao/municipio (dá para compartilhar o link de um município)
function rota(indice: Indice): { secao: Secao; municipio: string } {
  const [, s, m] = location.hash.split('/');
  const secao = SECOES.some(([k]) => k === s) ? (s as Secao) : 'indicadores';
  const ids = indice.municipios.map((x) => x.id);
  const municipio = ids.includes(m) ? m : ids.includes(MUNICIPIO_PADRAO) ? MUNICIPIO_PADRAO : ids[0];
  return { secao, municipio };
}

function irPara(secao: Secao, municipio: string) {
  location.hash = `#/${secao}/${municipio}`;
}

function seletor(indice: Indice, atual: string, secao: Secao): HTMLElement {
  const porUf = new Map<string, Indice['municipios']>();
  for (const m of [...indice.municipios].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))) {
    porUf.set(m.uf, [...(porUf.get(m.uf) ?? []), m]);
  }
  const select = el('select', { id: 'municipio' },
    ...[...porUf.keys()].sort().map((uf) => el('optgroup', { label: uf },
      ...porUf.get(uf)!.map((m) => el('option', { value: m.id }, m.papel === 'validacao' ? `${m.nome} *` : m.nome)))));
  select.value = atual;
  select.addEventListener('change', () => irPara(secao, select.value));
  return el('div', { class: 'seletor' }, el('label', {}, 'Município ', select),
    el('span', { class: 'nota' }, '* município do conjunto de teste: não usado no treino do modelo'));
}

function cabecalho(secao: Secao, municipio: string): HTMLElement {
  return el('header', {},
    el('div', { class: 'marca' }, el('strong', {}, 'Dengue Insight'),
      el('span', {}, 'Níveis e alertas de dengue para 115 municípios')),
    el('nav', { 'aria-label': 'Seções' }, ...SECOES.map(([k, rotulo]) =>
      el('a', { href: `#/${k}/${municipio}`, ...(k === secao ? { 'aria-current': 'page' } : {}) }, rotulo))));
}

async function mostrar(): Promise<void> {
  const app = document.getElementById('app')!;
  try {
    const indice = await carregarIndice();
    const { secao, municipio } = rota(indice);
    const conteudo = el('main', { 'aria-busy': 'true' }, el('p', { class: 'contexto' }, 'Carregando…'));
    // Seletor abaixo do cabeçalho: entra e sai com a seção sem deslocar o menu
    app.replaceChildren(cabecalho(secao, municipio), secao === 'ajuda' ? '' : seletor(indice, municipio, secao), conteudo,
      el('footer', {}, 'Trabalho acadêmico (PI-IV, UNIVESP). Previsões experimentais: não usar para decisões oficiais. ' +
        'Dados: InfoDengue e Open-Meteo.'));
    if (secao === 'ajuda') renderAjuda(conteudo);
    else {
      const [m, av] = await Promise.all([carregarMunicipio(municipio), carregarAvaliacao()]);
      if (secao === 'indicadores') renderIndicadores(conteudo, m, indice);
      else renderAvaliacao(conteudo, m, av);
    }
    conteudo.setAttribute('aria-busy', 'false');
    document.title = `Dengue Insight · ${SECOES.find(([k]) => k === secao)![1]}`;
  } catch (erro) {
    app.replaceChildren(el('p', { class: 'erro' }, `Não foi possível carregar os dados. ${(erro as Error).message}`));
  }
}

// Aviso de entrada: aceito uma vez por navegador
function avisoAceito(): boolean {
  try { return localStorage.getItem(CHAVE_AVISO) === '1'; } catch { return false; }
}

function mostrarAviso(depois: () => void): void {
  const campo = el('input', { type: 'text', autocomplete: 'off', 'aria-label': `Digite ${PALAVRA_ACEITE}` });
  const erro = el('p', { class: 'erro', role: 'alert' });
  const form = el('form', { class: 'aviso' },
    el('h1', {}, 'Dengue Insight'),
    el('p', {}, 'Este painel é resultado de um trabalho acadêmico (Projeto Integrador IV, UNIVESP). As previsões são ' +
      'experimentais e não devem ser usadas como base para decisões oficiais de vigilância ou de saúde pública.'),
    el('label', {}, `Para continuar, digite "${PALAVRA_ACEITE}": `, campo), erro,
    el('button', { type: 'submit' }, 'Continuar'));
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (campo.value.trim().toLowerCase() !== PALAVRA_ACEITE) {
      erro.textContent = `Digite "${PALAVRA_ACEITE}" para continuar.`;
      return;
    }
    try { localStorage.setItem(CHAVE_AVISO, '1'); } catch { /* sem armazenamento: pergunta de novo na próxima visita */ }
    depois();
  });
  document.getElementById('app')!.replaceChildren(form);
  campo.focus();
}

function iniciar(): void {
  window.addEventListener('hashchange', mostrar);
  // Gráficos com a largura da tela: redesenha depois de redimensionar
  let espera: number | undefined;
  let larguraAnterior = window.innerWidth;
  window.addEventListener('resize', () => {
    clearTimeout(espera);
    espera = window.setTimeout(() => {
      if (window.innerWidth !== larguraAnterior) { larguraAnterior = window.innerWidth; void mostrar(); }
    }, 250);
  });
  void mostrar();
}

if (avisoAceito()) iniciar();
else mostrarAviso(iniciar);
