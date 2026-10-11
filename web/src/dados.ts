// Leitura dos JSON gerados por src/exportar_painel.py (um por município, carregado só quando escolhido)

export type Nivel = 0 | 1 | 2;
export type EstadoAlerta = 'alerta' | 'sem_alerta' | 'epidemia_continua' | 'fim_indicado';

export interface ItemIndice {
  id: string;
  nome: string;
  uf: string;
  papel: 'treino' | 'validacao';
  nivel_confirmado: Nivel | null;
  alerta: EstadoAlerta;
}

export interface Indice {
  gerado_em: string;
  versao_dados: string;
  semana_atual: string;
  semana_confirmada: string;
  lacuna: number;
  corte_alerta: number;
  trimestre_corte: string;
  municipios: ItemIndice[];
}

export interface Previsao {
  semana: string;
  antecedencia: number;
  p_verde: number;
  p_amarelo: number;
  p_vermelho: number;
  nivel: Nivel;
  casos: number;
  casos_inf: number;
  casos_sup: number;
  limiar_amarelo: number;
  limiar_vermelho: number;
}

export interface Limiares {
  temporada: string;
  inicio_se: number;
  pre_epidemico: number;
  epidemico: number;
}

export interface SemanaRecente {
  semana: string;
  se: number;
  notificados: number | null;
  estimados: number | null;
  estimados_min: number | null;
  estimados_max: number | null;
}

export interface Municipio {
  id: string;
  nome: string;
  uf: string;
  papel: 'treino' | 'validacao';
  populacao: number;
  semana_atual: string;
  se_atual: number;
  confirmada: { semana: string; se: number; casos: number; notificados: number; nivel: Nivel | null };
  recentes: SemanaRecente[];
  previsoes: Previsao[];
  alerta: { estado: EstadoAlerta; p_vermelho_max: number; corte: number };
  limiares: Limiares[];
  serie: {
    semana: string[];
    se: number[];
    casos: (number | null)[];
    notificados: (number | null)[];
    nivel: (Nivel | null)[];
    limiar_amarelo: (number | null)[];
    limiar_vermelho: (number | null)[];
  };
  avaliacao: {
    niveis: Record<string, (Nivel | null)[]>;
    casos: Record<string, { previsto: (number | null)[]; inferior: (number | null)[]; superior: (number | null)[] }>;
  };
}

export interface LinhaRobustez {
  teste: string;
  conjunto: 'validacao_cruzada' | 'validacao_final';
  lacuna: number;
  metodo: string;
  metrica: string;
  valor: number | null;
  ic95_inf: number | null;
  ic95_sup: number | null;
  dif_vs_comparacao: number | null;
  dif_ic95_inf: number | null;
  dif_ic95_sup: number | null;
}

export interface LinhaCasos {
  conjunto: string;
  antecedencia: number;
  metrica: 'razao_erro' | 'cobertura_80';
  valor: number;
  ic95_inf: number;
  ic95_sup: number;
}

export interface LinhaAlertaH {
  conjunto: string;
  h: number;
  semanas_com_alerta: number;
  veio_vermelho: number;
  veio_amarelo: number;
  veio_verde: number;
}

export interface AvaliacaoGeral {
  niveis_robustez: LinhaRobustez[];
  casos_atraso: LinhaCasos[];
  alertas_por_antecedencia: LinhaAlertaH[];
}

const BASE = `${import.meta.env.BASE_URL}dados/`;
let indice: Promise<Indice> | null = null;
let avaliacao: Promise<AvaliacaoGeral> | null = null;
const municipios = new Map<string, Promise<Municipio>>();

async function json<T>(caminho: string): Promise<T> {
  const r = await fetch(caminho);
  if (!r.ok) throw new Error(`Não foi possível carregar ${caminho} (${r.status})`);
  return r.json() as Promise<T>;
}

export function carregarIndice(): Promise<Indice> {
  indice ??= json<Indice>(`${BASE}indice.json?t=${Date.now()}`);
  return indice;
}

// A versão dos dados vai na URL: depois de uma atualização, o navegador não reaproveita o arquivo antigo
export async function carregarMunicipio(id: string): Promise<Municipio> {
  const { versao_dados } = await carregarIndice();
  if (!municipios.has(id)) municipios.set(id, json<Municipio>(`${BASE}municipios/${id}.json?v=${versao_dados}`));
  return municipios.get(id)!;
}

export async function carregarAvaliacao(): Promise<AvaliacaoGeral> {
  const { versao_dados } = await carregarIndice();
  avaliacao ??= json<AvaliacaoGeral>(`${BASE}avaliacao.json?v=${versao_dados}`);
  return avaliacao;
}
