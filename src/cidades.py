"""
Configuração central dos municípios do Dengue Insight.

Cada município tem:
  - geocode:  código IBGE (usado nas APIs do InfoDengue e Mosqlimate)
  - nome:     nome de exibição no dashboard
  - lat, lon: coordenadas da sede (para fontes climáticas por ponto, ex.: Open-Meteo)
  - papel:    'treino'    -> entra no treino e na avaliação temporal (walk-forward)
              'validacao' -> NUNCA entra no treino nem em nenhum ajuste; usado apenas
                             para testar a generalização espacial do modelo
  - criterio: motivo da inclusão (documentação para o relatório)

Critério geral de inclusão: municípios com mais de 100 mil habitantes, exceto
Cosmópolis, mantida por ser polo de integrante do grupo.
"""

POLO = "Polo UNIVESP de integrante do grupo"
REGIAO = "Região de Campinas/Piracicaba, entre os polos (>100 mil hab.)"

CIDADES = {
    # ---------- Treino: polos dos integrantes ----------
    "campinas":      {"geocode": 3509502, "nome": "Campinas",              "lat": -22.9053, "lon": -47.0659, "papel": "treino", "criterio": POLO},
    "cosmopolis":    {"geocode": 3512803, "nome": "Cosmópolis",            "lat": -22.6419, "lon": -47.1926, "papel": "treino", "criterio": POLO + " (município pequeno; métricas reportadas à parte)"},
    "limeira":       {"geocode": 3526902, "nome": "Limeira",               "lat": -22.5660, "lon": -47.3970, "papel": "treino", "criterio": POLO},
    "piracicaba":    {"geocode": 3538709, "nome": "Piracicaba",            "lat": -22.7338, "lon": -47.6476, "papel": "treino", "criterio": POLO},
    "rio_claro":     {"geocode": 3543907, "nome": "Rio Claro",             "lat": -22.3984, "lon": -47.5546, "papel": "treino", "criterio": POLO},

    # ---------- Treino: região entre os polos ----------
    "americana":     {"geocode": 3501608, "nome": "Americana",             "lat": -22.7374, "lon": -47.3331, "papel": "treino", "criterio": REGIAO},
    "sumare":        {"geocode": 3552403, "nome": "Sumaré",                "lat": -22.8204, "lon": -47.2728, "papel": "treino", "criterio": REGIAO},
    "hortolandia":   {"geocode": 3519071, "nome": "Hortolândia",           "lat": -22.8529, "lon": -47.2143, "papel": "treino", "criterio": REGIAO},
    "indaiatuba":    {"geocode": 3520509, "nome": "Indaiatuba",            "lat": -23.0816, "lon": -47.2101, "papel": "treino", "criterio": REGIAO},
    "santa_barbara": {"geocode": 3545803, "nome": "Santa Bárbara d'Oeste", "lat": -22.7553, "lon": -47.4143, "papel": "treino", "criterio": REGIAO},
    "paulinia":      {"geocode": 3536505, "nome": "Paulínia",              "lat": -22.7542, "lon": -47.1488, "papel": "treino", "criterio": REGIAO},
    "valinhos":      {"geocode": 3556206, "nome": "Valinhos",              "lat": -22.9698, "lon": -46.9974, "papel": "treino", "criterio": REGIAO},
    "araras":        {"geocode": 3503307, "nome": "Araras",                "lat": -22.3572, "lon": -47.3842, "papel": "treino", "criterio": REGIAO},

    # ---------- Validação espacial: outras regiões de SP, climas contrastantes ----------
    "sao_jose_rio_preto":  {"geocode": 3549805, "nome": "São José do Rio Preto", "lat": -20.8113, "lon": -49.3758, "papel": "validacao", "criterio": "Validação espacial: noroeste paulista, clima mais quente"},
    "ribeirao_preto":      {"geocode": 3543402, "nome": "Ribeirão Preto",        "lat": -21.1699, "lon": -47.8099, "papel": "validacao", "criterio": "Validação espacial: norte paulista, inverno mais seco"},
    "sorocaba":            {"geocode": 3552205, "nome": "Sorocaba",              "lat": -23.4969, "lon": -47.4451, "papel": "validacao", "criterio": "Validação espacial: sul do interior, clima mais ameno"},
    "presidente_prudente": {"geocode": 3541406, "nome": "Presidente Prudente",   "lat": -22.1207, "lon": -51.3925, "papel": "validacao", "criterio": "Validação espacial: extremo oeste, mais distante da região de treino"},
    "bauru":               {"geocode": 3506003, "nome": "Bauru",                 "lat": -22.3246, "lon": -49.0871, "papel": "validacao", "criterio": "Validação espacial: centro-oeste paulista, distância intermediária"},
    "santos":              {"geocode": 3548500, "nome": "Santos",                "lat": -23.9535, "lon": -46.3350, "papel": "validacao", "criterio": "Validação espacial: litoral, clima marítimo úmido (único costeiro)"},
}


def cidades_por_papel(papel: str) -> dict:
    """Retorna apenas os municípios com o papel indicado ('treino' ou 'validacao')."""
    return {k: v for k, v in CIDADES.items() if v["papel"] == papel}


# Verificação de consistência ao importar: falha cedo se a configuração estiver errada
assert all(v["papel"] in ("treino", "validacao") for v in CIDADES.values()), "papel inválido"
assert len({v["geocode"] for v in CIDADES.values()}) == len(CIDADES), "geocode duplicado"