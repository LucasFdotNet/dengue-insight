"""
Configuração central dos municípios do Dengue Insight.

Cada município tem:
  - geocode:  código IBGE (usado nas APIs do InfoDengue e Mosqlimate)
  - nome:     nome de exibição no dashboard
  - uf:       sigla do estado
  - lat, lon: coordenadas da sede (para fontes climáticas por ponto, ex.: Open-Meteo)
  - papel:    'treino'    -> entra no treino e na avaliação temporal (walk-forward)
              'validacao' -> NUNCA entra no treino nem em nenhum ajuste; usado apenas
                             para testar a generalização espacial do modelo
  - criterio: motivo da inclusão (documentação para o relatório)

Critérios de inclusão:
  - São Paulo (19): municípios com mais de 100 mil habitantes, exceto Cosmópolis,
    mantida por ser polo de integrante do grupo.
  - Brasil (55), para dar ao modelo climas e padrões de epidemia diferentes dos de SP.
    Treino (50): em cada UF fora de SP, a capital e o maior município não capital com
    mais de 100 mil habitantes a mais de 50 km da capital (fora da região metropolitana);
    AC, AP, DF e RR não têm esse segundo município, e os 2 lugares restantes vão para os
    maiores municípios restantes do país pelo mesmo critério. Validação (5): o maior
    município restante de cada macrorregião, pelo mesmo critério.
    População: Censo 2022 (IBGE, tabela 4709).
"""

POLO = "Polo UNIVESP de integrante do grupo"
REGIAO = "Região de Campinas/Piracicaba, entre os polos (>100 mil hab.)"
NAC_CAPITAL = "Treino nacional: capital da UF"
NAC_SEGUNDA = "Treino nacional: maior município não capital da UF com >100 mil hab. a >50 km da capital"
NAC_EXTRA = "Treino nacional: maior município restante do país pelo mesmo critério (completa 50 cidades)"
NAC_VALIDACAO = "Validação espacial nacional: maior município restante da macrorregião pelo mesmo critério"

CIDADES = {
    # ---------- Treino: polos dos integrantes ----------
    "campinas":      {"geocode": 3509502, "nome": "Campinas", "uf": "SP",              "lat": -22.9053, "lon": -47.0659, "papel": "treino", "criterio": POLO},
    "cosmopolis":    {"geocode": 3512803, "nome": "Cosmópolis", "uf": "SP",            "lat": -22.6419, "lon": -47.1926, "papel": "treino", "criterio": POLO + " (município pequeno; métricas reportadas à parte)"},
    "limeira":       {"geocode": 3526902, "nome": "Limeira", "uf": "SP",               "lat": -22.5660, "lon": -47.3970, "papel": "treino", "criterio": POLO},
    "piracicaba":    {"geocode": 3538709, "nome": "Piracicaba", "uf": "SP",            "lat": -22.7338, "lon": -47.6476, "papel": "treino", "criterio": POLO},
    "rio_claro":     {"geocode": 3543907, "nome": "Rio Claro", "uf": "SP",             "lat": -22.3984, "lon": -47.5546, "papel": "treino", "criterio": POLO},

    # ---------- Treino: região entre os polos ----------
    "americana":     {"geocode": 3501608, "nome": "Americana", "uf": "SP",             "lat": -22.7374, "lon": -47.3331, "papel": "treino", "criterio": REGIAO},
    "sumare":        {"geocode": 3552403, "nome": "Sumaré", "uf": "SP",                "lat": -22.8204, "lon": -47.2728, "papel": "treino", "criterio": REGIAO},
    "hortolandia":   {"geocode": 3519071, "nome": "Hortolândia", "uf": "SP",           "lat": -22.8529, "lon": -47.2143, "papel": "treino", "criterio": REGIAO},
    "indaiatuba":    {"geocode": 3520509, "nome": "Indaiatuba", "uf": "SP",            "lat": -23.0816, "lon": -47.2101, "papel": "treino", "criterio": REGIAO},
    "santa_barbara": {"geocode": 3545803, "nome": "Santa Bárbara d'Oeste", "uf": "SP", "lat": -22.7553, "lon": -47.4143, "papel": "treino", "criterio": REGIAO},
    "paulinia":      {"geocode": 3536505, "nome": "Paulínia", "uf": "SP",              "lat": -22.7542, "lon": -47.1488, "papel": "treino", "criterio": REGIAO},
    "valinhos":      {"geocode": 3556206, "nome": "Valinhos", "uf": "SP",              "lat": -22.9698, "lon": -46.9974, "papel": "treino", "criterio": REGIAO},
    "araras":        {"geocode": 3503307, "nome": "Araras", "uf": "SP",                "lat": -22.3572, "lon": -47.3842, "papel": "treino", "criterio": REGIAO},

    # ---------- Validação espacial: outras regiões de SP, climas contrastantes ----------
    "sao_jose_rio_preto":  {"geocode": 3549805, "nome": "São José do Rio Preto", "uf": "SP", "lat": -20.8113, "lon": -49.3758, "papel": "validacao", "criterio": "Validação espacial: noroeste paulista, clima mais quente"},
    "ribeirao_preto":      {"geocode": 3543402, "nome": "Ribeirão Preto", "uf": "SP",        "lat": -21.1699, "lon": -47.8099, "papel": "validacao", "criterio": "Validação espacial: norte paulista, inverno mais seco"},
    "sorocaba":            {"geocode": 3552205, "nome": "Sorocaba", "uf": "SP",              "lat": -23.4969, "lon": -47.4451, "papel": "validacao", "criterio": "Validação espacial: sul do interior, clima mais ameno"},
    "presidente_prudente": {"geocode": 3541406, "nome": "Presidente Prudente", "uf": "SP",   "lat": -22.1207, "lon": -51.3925, "papel": "validacao", "criterio": "Validação espacial: extremo oeste, mais distante da região de treino"},
    "bauru":               {"geocode": 3506003, "nome": "Bauru", "uf": "SP",                 "lat": -22.3246, "lon": -49.0871, "papel": "validacao", "criterio": "Validação espacial: centro-oeste paulista, distância intermediária"},
    "santos":              {"geocode": 3548500, "nome": "Santos", "uf": "SP",                "lat": -23.9535, "lon": -46.3350, "papel": "validacao", "criterio": "Validação espacial: litoral paulista, clima marítimo úmido"},

    # ---------- Treino nacional: capitais das UFs fora de SP ----------
    "brasilia":                {"geocode": 5300108, "nome": "Brasília", "uf": "DF", "lat": -15.7795, "lon": -47.9297, "papel": "treino", "criterio": NAC_CAPITAL},
    "goiania":                 {"geocode": 5208707, "nome": "Goiânia", "uf": "GO", "lat": -16.6864, "lon": -49.2643, "papel": "treino", "criterio": NAC_CAPITAL},
    "campo_grande":            {"geocode": 5002704, "nome": "Campo Grande", "uf": "MS", "lat": -20.4486, "lon": -54.6295, "papel": "treino", "criterio": NAC_CAPITAL},
    "cuiaba":                  {"geocode": 5103403, "nome": "Cuiabá", "uf": "MT", "lat": -15.6010, "lon": -56.0974, "papel": "treino", "criterio": NAC_CAPITAL},
    "maceio":                  {"geocode": 2704302, "nome": "Maceió", "uf": "AL", "lat": -9.6660, "lon": -35.7350, "papel": "treino", "criterio": NAC_CAPITAL},
    "salvador":                {"geocode": 2927408, "nome": "Salvador", "uf": "BA", "lat": -12.9718, "lon": -38.5011, "papel": "treino", "criterio": NAC_CAPITAL},
    "fortaleza":               {"geocode": 2304400, "nome": "Fortaleza", "uf": "CE", "lat": -3.7166, "lon": -38.5423, "papel": "treino", "criterio": NAC_CAPITAL},
    "sao_luis":                {"geocode": 2111300, "nome": "São Luís", "uf": "MA", "lat": -2.5387, "lon": -44.2825, "papel": "treino", "criterio": NAC_CAPITAL},
    "joao_pessoa":             {"geocode": 2507507, "nome": "João Pessoa", "uf": "PB", "lat": -7.1151, "lon": -34.8641, "papel": "treino", "criterio": NAC_CAPITAL},
    "recife":                  {"geocode": 2611606, "nome": "Recife", "uf": "PE", "lat": -8.0467, "lon": -34.8771, "papel": "treino", "criterio": NAC_CAPITAL},
    "teresina":                {"geocode": 2211001, "nome": "Teresina", "uf": "PI", "lat": -5.0919, "lon": -42.8034, "papel": "treino", "criterio": NAC_CAPITAL},
    "natal":                   {"geocode": 2408102, "nome": "Natal", "uf": "RN", "lat": -5.7936, "lon": -35.1986, "papel": "treino", "criterio": NAC_CAPITAL},
    "aracaju":                 {"geocode": 2800308, "nome": "Aracaju", "uf": "SE", "lat": -10.9091, "lon": -37.0677, "papel": "treino", "criterio": NAC_CAPITAL},
    "rio_branco":              {"geocode": 1200401, "nome": "Rio Branco", "uf": "AC", "lat": -9.9750, "lon": -67.8243, "papel": "treino", "criterio": NAC_CAPITAL},
    "manaus":                  {"geocode": 1302603, "nome": "Manaus", "uf": "AM", "lat": -3.1187, "lon": -60.0212, "papel": "treino", "criterio": NAC_CAPITAL},
    "macapa":                  {"geocode": 1600303, "nome": "Macapá", "uf": "AP", "lat": 0.0349, "lon": -51.0694, "papel": "treino", "criterio": NAC_CAPITAL},
    "belem":                   {"geocode": 1501402, "nome": "Belém", "uf": "PA", "lat": -1.4554, "lon": -48.4898, "papel": "treino", "criterio": NAC_CAPITAL},
    "porto_velho":             {"geocode": 1100205, "nome": "Porto Velho", "uf": "RO", "lat": -8.7608, "lon": -63.8999, "papel": "treino", "criterio": NAC_CAPITAL},
    "boa_vista":               {"geocode": 1400100, "nome": "Boa Vista", "uf": "RR", "lat": 2.8238, "lon": -60.6753, "papel": "treino", "criterio": NAC_CAPITAL},
    "palmas":                  {"geocode": 1721000, "nome": "Palmas", "uf": "TO", "lat": -10.2400, "lon": -48.3558, "papel": "treino", "criterio": NAC_CAPITAL},
    "vitoria":                 {"geocode": 3205309, "nome": "Vitória", "uf": "ES", "lat": -20.3155, "lon": -40.3128, "papel": "treino", "criterio": NAC_CAPITAL},
    "belo_horizonte":          {"geocode": 3106200, "nome": "Belo Horizonte", "uf": "MG", "lat": -19.9102, "lon": -43.9266, "papel": "treino", "criterio": NAC_CAPITAL},
    "rio_de_janeiro":          {"geocode": 3304557, "nome": "Rio de Janeiro", "uf": "RJ", "lat": -22.9129, "lon": -43.2003, "papel": "treino", "criterio": NAC_CAPITAL},
    "curitiba":                {"geocode": 4106902, "nome": "Curitiba", "uf": "PR", "lat": -25.4195, "lon": -49.2646, "papel": "treino", "criterio": NAC_CAPITAL},
    "porto_alegre":            {"geocode": 4314902, "nome": "Porto Alegre", "uf": "RS", "lat": -30.0318, "lon": -51.2065, "papel": "treino", "criterio": NAC_CAPITAL},
    "florianopolis":           {"geocode": 4205407, "nome": "Florianópolis", "uf": "SC", "lat": -27.5945, "lon": -48.5477, "papel": "treino", "criterio": NAC_CAPITAL},

    # ---------- Treino nacional: maior município não capital de cada UF (>100 mil hab., >50 km da capital) ----------
    "anapolis":                {"geocode": 5201108, "nome": "Anápolis", "uf": "GO", "lat": -16.3281, "lon": -48.9530, "papel": "treino", "criterio": NAC_SEGUNDA},
    "dourados":                {"geocode": 5003702, "nome": "Dourados", "uf": "MS", "lat": -22.2231, "lon": -54.8120, "papel": "treino", "criterio": NAC_SEGUNDA},
    "rondonopolis":            {"geocode": 5107602, "nome": "Rondonópolis", "uf": "MT", "lat": -16.4673, "lon": -54.6372, "papel": "treino", "criterio": NAC_SEGUNDA},
    "arapiraca":               {"geocode": 2700300, "nome": "Arapiraca", "uf": "AL", "lat": -9.7549, "lon": -36.6615, "papel": "treino", "criterio": NAC_SEGUNDA},
    "feira_de_santana":        {"geocode": 2910800, "nome": "Feira de Santana", "uf": "BA", "lat": -12.2664, "lon": -38.9663, "papel": "treino", "criterio": NAC_SEGUNDA},
    "juazeiro_do_norte":       {"geocode": 2307304, "nome": "Juazeiro do Norte", "uf": "CE", "lat": -7.1962, "lon": -39.3076, "papel": "treino", "criterio": NAC_SEGUNDA},
    "imperatriz":              {"geocode": 2105302, "nome": "Imperatriz", "uf": "MA", "lat": -5.5185, "lon": -47.4777, "papel": "treino", "criterio": NAC_SEGUNDA},
    "campina_grande":          {"geocode": 2504009, "nome": "Campina Grande", "uf": "PB", "lat": -7.2220, "lon": -35.8731, "papel": "treino", "criterio": NAC_SEGUNDA},
    "petrolina":               {"geocode": 2611101, "nome": "Petrolina", "uf": "PE", "lat": -9.3887, "lon": -40.5027, "papel": "treino", "criterio": NAC_SEGUNDA},
    "parnaiba":                {"geocode": 2207702, "nome": "Parnaíba", "uf": "PI", "lat": -2.9059, "lon": -41.7754, "papel": "treino", "criterio": NAC_SEGUNDA},
    "mossoro":                 {"geocode": 2408003, "nome": "Mossoró", "uf": "RN", "lat": -5.1837, "lon": -37.3474, "papel": "treino", "criterio": NAC_SEGUNDA},
    "lagarto":                 {"geocode": 2803500, "nome": "Lagarto", "uf": "SE", "lat": -10.9136, "lon": -37.6689, "papel": "treino", "criterio": NAC_SEGUNDA},
    "itacoatiara":             {"geocode": 1301902, "nome": "Itacoatiara", "uf": "AM", "lat": -3.1386, "lon": -58.4449, "papel": "treino", "criterio": NAC_SEGUNDA},
    "santarem":                {"geocode": 1506807, "nome": "Santarém", "uf": "PA", "lat": -2.4385, "lon": -54.6996, "papel": "treino", "criterio": NAC_SEGUNDA},
    "ji_parana":               {"geocode": 1100122, "nome": "Ji-Paraná", "uf": "RO", "lat": -10.8777, "lon": -61.9322, "papel": "treino", "criterio": NAC_SEGUNDA},
    "araguaina":               {"geocode": 1702109, "nome": "Araguaína", "uf": "TO", "lat": -7.1924, "lon": -48.2044, "papel": "treino", "criterio": NAC_SEGUNDA},
    "cachoeiro_de_itapemirim": {"geocode": 3201209, "nome": "Cachoeiro de Itapemirim", "uf": "ES", "lat": -20.8462, "lon": -41.1198, "papel": "treino", "criterio": NAC_SEGUNDA},
    "uberlandia":              {"geocode": 3170206, "nome": "Uberlândia", "uf": "MG", "lat": -18.9141, "lon": -48.2749, "papel": "treino", "criterio": NAC_SEGUNDA},
    "campos_dos_goytacazes":   {"geocode": 3301009, "nome": "Campos dos Goytacazes", "uf": "RJ", "lat": -21.7622, "lon": -41.3181, "papel": "treino", "criterio": NAC_SEGUNDA},
    "londrina":                {"geocode": 4113700, "nome": "Londrina", "uf": "PR", "lat": -23.3040, "lon": -51.1691, "papel": "treino", "criterio": NAC_SEGUNDA},
    "caxias_do_sul":           {"geocode": 4305108, "nome": "Caxias do Sul", "uf": "RS", "lat": -29.1629, "lon": -51.1792, "papel": "treino", "criterio": NAC_SEGUNDA},
    "joinville":               {"geocode": 4209102, "nome": "Joinville", "uf": "SC", "lat": -26.3045, "lon": -48.8487, "papel": "treino", "criterio": NAC_SEGUNDA},

    # ---------- Treino nacional: maiores municípios restantes do país, para completar 50 ----------
    "juiz_de_fora":            {"geocode": 3136702, "nome": "Juiz de Fora", "uf": "MG", "lat": -21.7595, "lon": -43.3398, "papel": "treino", "criterio": NAC_EXTRA},
    "montes_claros":           {"geocode": 3143302, "nome": "Montes Claros", "uf": "MG", "lat": -16.7282, "lon": -43.8578, "papel": "treino", "criterio": NAC_EXTRA},

    # ---------- Validação espacial nacional: maior município restante de cada macrorregião ----------
    "rio_verde":               {"geocode": 5218805, "nome": "Rio Verde", "uf": "GO", "lat": -17.7923, "lon": -50.9192, "papel": "validacao", "criterio": NAC_VALIDACAO},
    "caruaru":                 {"geocode": 2604106, "nome": "Caruaru", "uf": "PE", "lat": -8.2845, "lon": -35.9699, "papel": "validacao", "criterio": NAC_VALIDACAO},
    "parauapebas":             {"geocode": 1505536, "nome": "Parauapebas", "uf": "PA", "lat": -6.0678, "lon": -49.9037, "papel": "validacao", "criterio": NAC_VALIDACAO},
    "uberaba":                 {"geocode": 3170107, "nome": "Uberaba", "uf": "MG", "lat": -19.7472, "lon": -47.9381, "papel": "validacao", "criterio": NAC_VALIDACAO},
    "maringa":                 {"geocode": 4115200, "nome": "Maringá", "uf": "PR", "lat": -23.4205, "lon": -51.9333, "papel": "validacao", "criterio": NAC_VALIDACAO},
}


def cidades_por_papel(papel: str) -> dict:
    """Retorna apenas os municípios com o papel indicado ('treino' ou 'validacao')."""
    return {k: v for k, v in CIDADES.items() if v["papel"] == papel}


# Verificação de consistência ao importar: falha cedo se a configuração estiver errada
assert all(v["papel"] in ("treino", "validacao") for v in CIDADES.values()), "papel inválido"
assert len({v["geocode"] for v in CIDADES.values()}) == len(CIDADES), "geocode duplicado"