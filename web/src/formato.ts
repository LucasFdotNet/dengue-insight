import type { Nivel } from './dados';

export const NOMES_NIVEL: Record<Nivel, string> = { 0: 'Verde', 1: 'Amarelo', 2: 'Vermelho' };
export const DESCRICAO_NIVEL: Record<Nivel, string> = {
  0: 'normal',
  1: 'elevado (acima do limiar pré-epidêmico)',
  2: 'epidêmico (acima do limiar epidêmico)',
};
export const CLASSE_NIVEL: Record<Nivel, string> = { 0: 'verde', 1: 'amarelo', 2: 'vermelho' };
// Ícone junto da cor: o nível nunca depende só da cor
export const ICONE_NIVEL: Record<Nivel, string> = { 0: '●', 1: '▲', 2: '◆' };

const numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const duasCasas = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 });

export const n = (x: number | null | undefined) => (x == null ? '—' : numero.format(x));
export const pct = (x: number | null | undefined) =>
  x == null ? '—' : x > 0 && x < 0.005 ? 'menos de 1%' : `${numero.format(100 * x)}%`;
export const decimal = (x: number | null | undefined, casas = 2) =>
  x == null ? '—' : (casas === 1 ? umaCasa : duasCasas).format(x);

export function data(iso: string): Date {
  const [a, m, d] = iso.split('-').map(Number);
  return new Date(a, m - 1, d);
}

export const diaMes = (iso: string) => data(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
export const diaMesAno = (iso: string) => data(iso).toLocaleDateString('pt-BR');

export function somarSemanas(iso: string, semanas: number): string {
  const d = data(iso);
  d.setDate(d.getDate() + 7 * semanas);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// "13/09 a 19/09": semana epidemiológica de domingo a sábado
export function periodoSemana(iso: string): string {
  const fim = data(iso);
  fim.setDate(fim.getDate() + 6);
  return `${diaMes(iso)} a ${fim.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}`;
}

export const se = (codigo: number) => `SE ${codigo % 100}/${Math.floor(codigo / 100)}`;

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...filhos: (Node | string | null | undefined | false)[]
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  for (const f of filhos) if (f !== null && f !== undefined && f !== false) e.append(f);
  return e;
}

export function seloNivel(nivel: Nivel | null, texto?: string): HTMLElement {
  if (nivel == null) return el('span', { class: 'selo' }, 'sem dado');
  return el('span', { class: `selo ${CLASSE_NIVEL[nivel]}` },
    el('span', { class: 'icone', 'aria-hidden': 'true' }, ICONE_NIVEL[nivel]),
    texto ?? NOMES_NIVEL[nivel]);
}
