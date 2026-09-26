"""
Configuração central dos municípios do Dengue Insight.

A lista fica em data/config/cidades.csv (editável sem mexer no código). Colunas:
  - chave:     identificador usado nos nomes de arquivo (ex.: data/raw/<chave>_raw.csv)
  - geocode:   código IBGE (usado na API do InfoDengue)
  - nome:      nome de exibição no dashboard
  - uf:        sigla do estado
  - lat, lon:  coordenadas da sede (para o clima por ponto, na Open-Meteo)
  - papel:     'treino'    -> entra no treino e na avaliação temporal (walk-forward)
               'validacao' -> NUNCA entra no treino nem em nenhum ajuste; usado apenas
                              para testar a generalização espacial do modelo
  - populacao: população do Censo 2022 (IBGE, tabela 4709)
  - criterio:  motivo da inclusão (documentação para o relatório)

Os critérios de seleção estão em "Decisões de Projeto", no README.
"""
import csv
import os

ARQUIVO_CIDADES = os.path.join(os.path.dirname(__file__), '..', 'data', 'config', 'cidades.csv')
COLUNAS = ['chave', 'geocode', 'nome', 'uf', 'lat', 'lon', 'papel', 'populacao', 'criterio']
PAPEIS = ('treino', 'validacao')


def carregar_cidades(caminho=ARQUIVO_CIDADES) -> dict:
    """Lê a lista de municípios e verifica a consistência (falha cedo se houver erro)."""
    with open(caminho, encoding='utf-8', newline='') as arquivo:
        leitor = csv.DictReader(arquivo)
        faltando = [c for c in COLUNAS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ValueError(f"{caminho}: colunas ausentes {faltando}")
        cidades = {}
        for linha in leitor:
            chave = linha['chave']
            if chave in cidades:
                raise ValueError(f"{caminho}: chave duplicada '{chave}'")
            if linha['papel'] not in PAPEIS:
                raise ValueError(f"{caminho}: papel inválido '{linha['papel']}' em '{chave}'")
            cidades[chave] = {
                'geocode': int(linha['geocode']),
                'nome': linha['nome'],
                'uf': linha['uf'],
                'lat': float(linha['lat']),
                'lon': float(linha['lon']),
                'papel': linha['papel'],
                'populacao': int(linha['populacao']),
                'criterio': linha['criterio'],
            }
    if len({v['geocode'] for v in cidades.values()}) != len(cidades):
        raise ValueError(f"{caminho}: geocode duplicado")
    return cidades


CIDADES = carregar_cidades()


def cidades_por_papel(papel: str) -> dict:
    """Retorna apenas os municípios com o papel indicado ('treino' ou 'validacao')."""
    return {k: v for k, v in CIDADES.items() if v["papel"] == papel}
