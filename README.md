# 🦟 Dengue Insight: Análise Preditiva para Monitoramento de Surtos de Dengue

Solução analítica e preditiva desenvolvida para o **Projeto Integrador em Computação IV (DRP04)** da **Universidade Virtual do Estado de São Paulo (UNIVESP)**.

---

## 📌 Sobre o Projeto

O **Dengue Insight** usa dados públicos de casos de dengue e de clima para prever a **tendência** dos casos nas próximas 1 a 4 semanas: se vão **subir, ficar estáveis ou cair**. O modelo é treinado com municípios de todo o Brasil e avaliado principalmente pela capacidade de **generalizar** para municípios que ele nunca viu.

O objetivo é oferecer uma ferramenta acessível de apoio à vigilância epidemiológica, para antecipar surtos e direcionar ações preventivas.

A história completa das decisões técnicas, com todos os experimentos e números, está em [`docs/historia_decisoes.md`](docs/historia_decisoes.md). Este README resume o **estado atual** do projeto.

### Municípios Monitorados

São 115 municípios, listados em [`data/config/cidades.csv`](data/config/cidades.csv) (critérios em [Decisões de Projeto](#-decisões-de-projeto)): 100 de treino e 15 de validação espacial, que nunca entram no modelo.

* **Treino, SP (13):** Campinas (SP), Cosmópolis (SP), Limeira (SP), Piracicaba (SP), Rio Claro (SP), Americana (SP), Sumaré (SP), Hortolândia (SP), Indaiatuba (SP), Santa Bárbara d'Oeste (SP), Paulínia (SP), Valinhos (SP), Araras (SP).
* **Treino, capitais e segundas cidades das outras UFs (50):** Brasília (DF), Goiânia (GO), Campo Grande (MS), Cuiabá (MT), Maceió (AL), Salvador (BA), Fortaleza (CE), São Luís (MA), João Pessoa (PB), Recife (PE), Teresina (PI), Natal (RN), Aracaju (SE), Rio Branco (AC), Manaus (AM), Macapá (AP), Belém (PA), Porto Velho (RO), Boa Vista (RR), Palmas (TO), Vitória (ES), Belo Horizonte (MG), Rio de Janeiro (RJ), Curitiba (PR), Porto Alegre (RS), Florianópolis (SC), Anápolis (GO), Dourados (MS), Rondonópolis (MT), Arapiraca (AL), Feira de Santana (BA), Juazeiro do Norte (CE), Imperatriz (MA), Campina Grande (PB), Petrolina (PE), Parnaíba (PI), Mossoró (RN), Lagarto (SE), Itacoatiara (AM), Santarém (PA), Ji-Paraná (RO), Araguaína (TO), Cachoeiro de Itapemirim (ES), Uberlândia (MG), Campos dos Goytacazes (RJ), Londrina (PR), Caxias do Sul (RS), Joinville (SC), Juiz de Fora (MG), Montes Claros (MG).
* **Treino, municípios com histórico de surtos (37):** Itabuna (BA), Luís Eduardo Magalhães (BA), Teixeira de Freitas (BA), Barreiras (BA), Sobral (CE), Itapipoca (CE), Jataí (GO), Balsas (MA), Varginha (MG), Itabira (MG), Passos (MG), Conselheiro Lafaiete (MG), Araxá (MG), Patos de Minas (MG), Altamira (PA), Itaituba (PA), Garanhuns (PE), Foz do Iguaçu (PR), Umuarama (PR), Cascavel (PR), Resende (RJ), Angra dos Reis (RJ), Itaperuna (RJ), Nova Friburgo (RJ), Rio das Ostras (RJ), Santa Cruz do Sul (RS), Erechim (RS), Santa Maria (RS), Chapecó (SC), Caraguatatuba (SP), Catanduva (SP), Araçatuba (SP), Marília (SP), Araraquara (SP), Barretos (SP), São José dos Campos (SP), Assis (SP).
* **Validação espacial (15):** São José do Rio Preto (SP), Ribeirão Preto (SP), Sorocaba (SP), Presidente Prudente (SP), Bauru (SP), Santos (SP), Rio Verde (GO), Caruaru (PE), Parauapebas (PA), Uberaba (MG), Maringá (PR), Vitória da Conquista (BA), Blumenau (SC), Sinop (MT), Manacapuru (AM).

---

## 👥 Integrantes do Grupo (Grupo 17)

* **Ana Carolina Freitas Amaral** — RA: 24215589
* **Fernanda Gabbai Amorim** — RA: 2208156
* **João Victor Araujo Galvão** — RA: 23216888
* **Lucas Rodrigues Furini** — RA: 23202046
* **Oscar Enrique Perea Santillan Donato** — RA: 2201460
* **Rafael Figueiredo Cotta** — RA: 24205472
* **Yan Rafael Areias Belchior** — RA: 23205037

**Orientador do Projeto:** Daniel Correia dos Santos

---

## ⚙️ Arquitetura e Funcionamento da Solução

1. **Ingestão**
   * **Casos (`src/ingestion.py`):** baixa da API do InfoDengue (Fiocruz/FGV) a série semanal de cada município, desde 2010.
   * **Clima (`src/ingestion_clima.py`):** baixa temperatura, chuva e umidade diárias da reanálise ERA5 (Open-Meteo) e agrega por semana epidemiológica.
2. **Pré-processamento (`src/preprocessing.py`):** une casos e clima por semana, interpola valores faltantes apenas entre valores conhecidos e calcula as variáveis do modelo.
3. **Treinamento e avaliação (`src/train.py`):** treina os dois modelos de produção, cada um único para todos os municípios de treino e com uma versão por antecedência (1 a 4 semanas): o **LightGBM classificador com clima**, para a tendência, e o **LightGBM por quantis**, para o número de casos com intervalo de 80%. Avalia os dois com validação *walk-forward* com retreino mensal contra o baseline de persistência e salva os modelos usados pelo painel (cerca de 20 minutos).
4. **Análise exploratória (`src/eda.py`):** gera matrizes de correlação e gráficos de casos contra clima.
5. **Painel (`app.py` e `painel/`):** aviso de uso acadêmico na entrada; seção **Indicadores**, com a tendência e os casos previstos para as próximas 4 semanas e o gráfico de projeções; seção **Detalhes do Modelo**, com a explicação dos modelos, a comparação com as alternativas, o mapa dos municípios e os dados de cada município.

**Experimentos** (cada um grava seus resultados em `reports/`; detalhes na seção "Decisões de Projeto"):

| Script | Pergunta |
|---|---|
| `src/experimento_modelos.py` | Qual modelo prevê melhor a tendência? (8 modelos, um arquivo cada em `src/modelos/`) |
| `src/experimento_rt.py` | O melhor modelo é mais útil que o Rt do InfoDengue? |
| `src/experimento_generalizacao.py` | O modelo generaliza para municípios não vistos? Mais municípios ajudam? O clima ajuda? |
| `src/experimento_atraso.py` | Quanto o modelo piora se os dados recentes ainda não estiverem disponíveis? |
| `src/experimento_clima_semanal.py` | Treino só com SP contra treino nacional; clima de semanas específicas |
| `src/experimento_variaveis.py` | Rt e clima no modelo (teste feito com a base de SP; histórico) |

---

## 📦 Tecnologias e Pacotes Utilizados

* **Linguagem:** Python 3 (testado com 3.14; o Streamlit Community Cloud aceita 3.12 ou mais recente)
* **Dados:** `pandas`, `numpy`, `requests`
* **Modelagem:** `lightgbm`, `scikit-learn`, `statsmodels`, `scipy`, `joblib`
* **Painel e gráficos:** `streamlit`, `plotly`, `matplotlib`, `seaborn`

As versões estão fixadas em `requirements.txt`.

---

## 🚀 Como Executar o Projeto Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/LucasFdotNet/dengue-insight.git
   cd dengue-insight
   ```

2. **Opcional: crie e ative um ambiente virtual**
   ```bash
   python -m venv venv
   venv/Scripts/activate        # Windows
   source venv/bin/activate     # Linux ou macOS
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute o pipeline** (sempre a partir da raiz do projeto)
   ```bash
   python -m src.ingestion
   python -m src.ingestion_clima
   python -m src.preprocessing
   python -m src.train
   python -m src.eda
   streamlit run app.py
   ```

   Os experimentos são opcionais e rodam da mesma forma, por exemplo `python -m src.experimento_modelos` (cerca de 45 minutos).

   **Sobre a ingestão de clima:** a Open-Meteo limita o uso gratuito por minuto, por hora e por dia, e a série de 16 anos de cada município consome boa parte desses limites. O script espera sozinho nos limites por minuto e por hora, então a primeira execução completa (115 municípios) leva algumas horas e pode atingir o limite diário. Nesse caso, ele para, mantém o que já foi salvo e avisa para rodar de novo mais tarde; a nova execução continua de onde parou. Nas execuções seguintes, só as últimas 12 semanas de cada município são baixadas. Para baixar tudo de novo: `python -m src.ingestion_clima --completo`.

   **Sem os dados de clima:** `python -m src.preprocessing --sem-clima` processa sem clima, o suficiente para treinar o modelo (que não usa clima); o painel e a análise exploratória precisam do processamento completo.

---

## 📏 Como Ler as Métricas

Os resultados usam três tipos de número. Cada tabela abaixo indica qual está usando.

| Métrica | O que é | Como ler |
|---|---|---|
| **Razão de erro** | Erro médio do modelo, em casos por semana, dividido pelo erro médio do baseline | **Menor é melhor.** Abaixo de 1, o modelo erra menos que o baseline (0,75 = erro 25% menor) |
| **Acerto de tendência** | Fração das semanas em que o modelo acertou se os casos iriam subir, ficar estáveis ou cair | **Maior é melhor.** Comparar com o "sempre estável", que já acerta muito porque a maioria das semanas é estável |
| **Acerto balanceado** | Média do acerto em cada uma das três situações (subiu, ficou estável, caiu), calculado separadamente | **Maior é melhor**, de 0 a 1. O baseline tira 0,333. **Não** é uma divisão pelo baseline |

**Exemplo de acerto balanceado** (LightGBM atual, 4 semanas de antecedência, semanas de 100 municípios somadas): o modelo acertou 41,6% das semanas em que os casos subiram, 75,3% das estáveis e 60,7% das que caíram. O acerto balanceado é a média: (41,6% + 75,3% + 60,7%) / 3 = **0,592**. O baseline, que sempre diz "estável", acerta 0%, 100% e 0%: média de **0,333**.

**Baseline de persistência:** a previsão mais simples possível, "daqui a H semanas haverá o mesmo número de casos de hoje". Na tendência, equivale a dizer sempre "estável". Um modelo só é útil se for melhor que isso.

Outras métricas de tendência: **subidas detectadas** (das semanas em que os casos subiram, em quantas o modelo previu subida), **alarmes de subida corretos** (das vezes em que o modelo previu subida, em quantas os casos subiram) e **sentido oposto** (semanas em que o modelo previu subida e os casos caíram, ou o contrário; menor é melhor).

---

## 🧭 Decisões de Projeto

Estado atual das decisões, com os números da base atual (115 municípios). Quando um resultado vem de uma etapa anterior do projeto, isso é indicado. A evolução de cada decisão, os testes intermediários e as conclusões que mudaram ao longo do caminho estão em [`docs/historia_decisoes.md`](docs/historia_decisoes.md).

### 1. Municípios e papéis (treino × validação)

* **Decisão:** 115 municípios, listados em [`data/config/cidades.csv`](data/config/cidades.csv): 100 de **treino** e 15 de **validação espacial**. O arquivo guarda chave, geocode IBGE, nome, UF, coordenadas, papel, população (Censo 2022) e o critério de inclusão de cada município. Fica em `data/config/` porque é uma configuração criada por nós, e não um dado baixado (`data/raw/`) nem gerado pelo pipeline (`data/processed/`).
* **Regra:** os municípios de validação **nunca** entram no treino, na seleção de features, no ajuste de hiperparâmetros nem na escolha de parâmetros como `SEMANAS_INSTAVEIS`. Eles servem apenas para medir se o modelo generaliza para outras regiões.
* **Foco:** SP é a área de interesse, mas o objetivo principal passou a ser mostrar que o modelo **generaliza** para municípios que não viu no treino. Por isso a base foi ampliada para todo o Brasil em três etapas.

**Etapa 1: São Paulo (19)**
* 13 de treino (os polos UNIVESP dos integrantes e a região entre eles) e 6 de validação (outras regiões do estado, com climas contrastantes).
* Critério: mais de 100 mil habitantes. A exceção é Cosmópolis, mantida por ser polo de integrante do grupo, com métricas reportadas à parte.

**Etapa 2: capitais e segundas cidades (55)**, para trazer climas e padrões de epidemia diferentes dos de SP (os 13 municípios de treino de SP são vizinhos e têm clima muito parecido):
* **Treino (50):** em cada uma das 26 UFs fora de SP, a capital e o maior município não capital com mais de 100 mil habitantes a mais de 50 km da capital. A distância evita municípios da mesma região metropolitana, que teriam o mesmo clima. AC, AP, DF e RR não têm esse segundo município; os 2 lugares restantes ficaram com os maiores municípios restantes do país pelo mesmo critério (Juiz de Fora e Montes Claros, MG).
* **Validação (5):** o maior município restante de cada macrorregião, pelo mesmo critério: Parauapebas (PA), Caruaru (PE), Rio Verde (GO), Uberaba (MG) e Maringá (PR).

**Etapa 3: municípios com histórico de surtos (37 de treino) e mais validação (4)**
* **Quantos por UF:** as 100 vagas de treino foram distribuídas entre as UFs em proporção à população (Censo 2022), pelo método dos maiores restos. Os municípios que já estavam no treino contam como piso: nenhuma UF perde município. Como as UFs pequenas já estavam acima da cota (capital e segunda cidade), as vagas novas foram para as mais populosas: SP 8, MG 6, RJ 5, BA 4, PR 3, RS 3, CE 2, PA 2, PE 1, SC 1, GO 1 e MA 1. A segunda vaga de PE não teve candidato que cumprisse a distância mínima e foi para a UF mais abaixo da cota que tinha candidato (PA).
* **Quais municípios:** em cada UF, entre os municípios com mais de 100 mil habitantes, os de **maior incidência média anual de dengue entre 2010 e 2025** (casos por 100 mil habitantes, com os dados do InfoDengue), a mais de 50 km de qualquer município já incluído. A incidência média resume, num único número, o peso das epidemias ao longo dos 16 anos. Um critério alternativo, contar os anos com incidência alta (300 ou mais casos por 100 mil, pela classificação do Ministério da Saúde), não diferenciava os candidatos: vários passam desse limite todos os anos.
* **Por que municípios com surtos:** o modelo precisa aprender como as epidemias começam, atingem o pico e terminam, e esses eventos são raros na série de cada município. Municípios com muitos surtos trazem mais exemplos desse comportamento.
* **Viés de seleção (limitação):** escolher municípios pelo histórico de surtos faz o treino ter mais epidemias do que um município típico teria, e o modelo pode ficar mais propenso a prever subidas. Os municípios de validação foram escolhidos por outros critérios (tamanho e região), sem olhar os surtos, e continuam sendo o teste sem esse viés. Avaliações feitas dentro do conjunto de treino (como a validação cruzada por município) refletem esse conjunto com mais surtos que o normal.
* **Validação (4 novos):** para chegar a 15, o maior município restante de cada macrorregião fora do Sudeste, numa UF que ainda não tinha município de validação, pelo mesmo critério da etapa 2: Manacapuru (AM), Vitória da Conquista (BA), Sinop (MT) e Blumenau (SC). Foram escolhidos antes dos municípios de treino da etapa 3, para que a seleção por surtos não interferisse neles.

### 2. Período dos dados

* **Decisão:** séries semanais de 2010 até a semana mais recente.
* **Motivo:** o InfoDengue disponibiliza a série desde 2010 para todos os municípios escolhidos. Mais anos significam mais epidemias para o modelo aprender.

### 3. Descarte das semanas finais instáveis

* **Decisão:** as últimas 10 semanas de cada município (`SEMANAS_INSTAVEIS`, em `src/train.py`) ficam fora do treino e da avaliação.
* **Motivo:** o número de casos das semanas mais recentes ainda é uma estimativa (*nowcast*), revisada pelo InfoDengue à medida que chegam notificações atrasadas.
* **Como chegamos a 10:** o InfoDengue informa um intervalo de incerteza do nowcast para cada semana. Contamos, em cada município de treino, quantas semanas finais ainda têm esse intervalo aberto, e adotamos o máximo. Foram 10 semanas nas três bases (SP, 74 e 115 municípios), em municípios como Cosmópolis, Indaiatuba, Manaus, Teresina, Varginha e Sobral. Municípios sem nowcast publicado, como Campinas, também têm a última semana visivelmente incompleta.
* **Limitação:** o critério mede onde o InfoDengue ainda aplica o nowcast, e não o quanto os números mudam depois.
* **Ponto de partida das previsões:** 39 dos 115 municípios (entre eles Campinas, Belo Horizonte, Rio de Janeiro e Salvador) não têm nowcast publicado nas semanas recentes, então essas semanas têm só os casos já notificados e estão incompletas. Em 09/2026, em relação ao nível das semanas anteriores, a última semana desses municípios tinha 23% dos casos, a penúltima 63% e a antepenúltima 76%, contra 84%, 82% e 87% nos municípios com nowcast. Partir de uma semana incompleta fazia o modelo "ver" uma subida que era só o número voltando ao normal. Por isso, nesses municípios, as previsões do painel partem da **última semana completa** (a 4ª mais recente; `SEMANAS_INCOMPLETAS_SEM_NOWCAST` em `src/predict.py`), e o painel avisa isso. Os municípios não foram descartados: o treino usa só semanas antigas, já completas.
* **Detalhe técnico:** o corte é feito depois de descartar as semanas sem alvo, para que também saiam as semanas cujo alvo (H semanas à frente) cai no período instável. Ele fica no treino, e não no pré-processamento, porque o painel precisa mostrar as semanas recentes.

### 4. Fonte dos dados climáticos: Open-Meteo (ERA5)

* **Decisão:** usar a reanálise **ERA5** (Copernicus/ECMWF), pela [Open-Meteo Historical API](https://open-meteo.com/en/docs/historical-weather-api) (`models=era5`), a partir da latitude e longitude de cada município, no lugar do clima do InfoDengue.
* **Motivos:** o clima do InfoDengue não tem chuva; de 2010 a 2022, vários municípios compartilhavam a mesma estação meteorológica (temperatura idêntica em Campinas, Cosmópolis e Piracicaba em todas as semanas); e a série mudou de fonte no meio do período.
* **Alternativas descartadas:** ERA5-Land (resolução melhor, mas sem chuva) e Mosqlimate (exige chave de API).
* **Limitações:** a grade do ERA5 tem 0,25°, então municípios muito próximos caem no mesmo ponto (os 115 municípios ocupam 109 pontos); e os dados chegam com cerca de 6 dias de atraso.
* **Agregação:** semana epidemiológica (domingo a sábado); só entram semanas com os 7 dias.
* **Atribuição:** dados ERA5 do Copernicus Climate Change Service, licença CC BY 4.0; acesso via Open-Meteo.
* **Uso:** o clima aparece no painel e na análise exploratória. **No modelo, está em aberto** (decisão 9).

### 5. Modelo único com alvo relativo

* **Decisão:** um único modelo treinado com todos os municípios de treino juntos (um para cada antecedência, de 1 a 4 semanas), prevendo a **variação** dos casos, e não o número de casos.
* **Alvo relativo:** o modelo responde "quanto os casos vão crescer ou cair em relação a hoje", em escala logarítmica: `log(1 + casos daqui a H semanas) − log(1 + casos hoje)`. Assim, municípios de tamanhos muito diferentes ficam na mesma escala, e o modelo aprende o comportamento da epidemia, não o tamanho do município.
* **Motivos:**
  * **Picos maiores que os do passado:** modelos de árvore, como o LightGBM, não preveem valores acima dos vistos no treino. Com o alvo absoluto, o modelo original ficava preso abaixo das epidemias novas (em Campinas, o treino chegava a 7.074 casos semanais e a epidemia de 2024 chegou a 11.789). Prevendo a variação, ele pode chegar a valores nunca vistos.
  * **Mais epidemias para aprender:** juntando os municípios, o modelo vê muito mais surtos do que veria em um só.
  * **Previsão para qualquer município:** o modelo não usa o nome do município, então pode prever municípios que nunca viu.
* **Resultado que motivou a escolha** (base de SP, 13 municípios de treino; razão de erro, **menor é melhor**):

  | Abordagem | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | Um modelo por município, alvo absoluto (original) | 2,07 | 1,40 | 1,16 | 1,00 |
  | Um modelo por município, alvo relativo | 0,89 | 0,83 | 0,76 | 0,76 |
  | **Modelo único, alvo relativo** | **0,87** | **0,79** | **0,75** | **0,72** |

* **Variáveis do modelo:** casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás e semana do ano. **Não usa o Rt** (decisão 8) **nem o clima** (decisão 9). A incidência por 100 mil habitantes foi retirada por ser redundante com os casos.
* **Modelos em produção** (decisão 11): LightGBM **classificador** com clima das semanas S-1 a S-4, para a tendência, e LightGBM **por quantis**, para o número de casos com intervalo de 80%. Os dois usam hiperparâmetros fixos (300 árvores, taxa de aprendizado 0,05).

### 6. Avaliação: walk-forward, validação cruzada por município e baseline

* **Walk-forward com retreino mensal:** para cada mês desde 2015, um modelo é treinado **só com o que já era conhecido** no início do mês e prevê as semanas daquele mês. Simula o uso real e garante que nenhuma informação do período previsto entre no modelo que o previu.
* **Validação espacial:** os 15 municípios de validação nunca entram no treino. Para os experimentos de generalização e de modelos, os 100 municípios de treino também são avaliados como desconhecidos, por **validação cruzada por município** (5 grupos de 20; cada grupo é previsto por modelos treinados com os outros 80).
* **Intervalos de confiança de 95%** por *bootstrap* sobre municípios: sorteamos municípios com reposição 2.000 vezes. A unidade de sorteio é o município, e não a semana, porque as semanas de um mesmo município são muito parecidas entre si.
* **Resultado atual do modelo de quantis (número de casos)** (`reports/metricas_gerais.csv`; razão de erro, **menor é melhor**, abaixo de 1 o modelo supera o baseline):

  | Grupo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | Municípios de treino (100) | 0,83 | 0,77 | 0,73 | 0,71 |
  | Municípios de validação (15) | 0,79 | 0,71 | 0,68 | 0,67 |

* **Por ano** (`reports/metricas_por_ano.csv`): nos municípios de treino, a razão fica abaixo de 1 em todos os anos de 2015 a 2026. Os anos mais difíceis são os de transmissão baixa ou estável (2017, 2018 e o parcial de 2026, de 0,88 a 0,97), e os melhores, os de epidemia (2024, de 0,64 a 0,76). Nos municípios de validação, só 2017 fica acima de 1 (até 1,11 em 4 semanas).
* **Por município de validação** (`reports/metricas_modelos.csv`): o modelo supera o baseline com folga em Blumenau, Sorocaba, Vitória da Conquista e Bauru (0,56 a 0,64 em 4 semanas), mas empata em Parauapebas e Manacapuru (Norte), Caruaru e Sinop (0,94 a 1,03). A generalização é mais fraca nas regiões com menos municípios parecidos no treino.
* **Pandemia (2020–2021):** num teste com a base de SP, treinar sem esses anos não mudou o resultado; todos os anos foram mantidos.
* **Limitação: dados revisados.** A simulação usa os casos na versão revisada de hoje; em tempo real, as semanas recentes estariam incompletas. Por isso ela é otimista nesse ponto. O InfoDengue não guarda os dados como eram conhecidos em cada data, então isso não pode ser corrigido para o passado (avaliação pseudoprospectiva). A decisão 12 mede o tamanho desse efeito.

### 7. Foco na tendência (sobe, estável ou cai)

* **Decisão:** o objetivo principal do modelo é acertar a **tendência** das próximas 1 a 4 semanas, e não o número exato de casos. Para a vigilância, saber que os casos vão subir é mais útil que o número exato.
* **Definição:** comparando os casos daqui a H semanas com os de hoje, a semana é de **subida** ou **queda** quando a variação passa de **20% e de 5 casos**; senão, **estável**. O mínimo de 5 casos evita que oscilações pequenas em municípios com poucos casos (de 2 para 3, por exemplo) contem como subida. Valores em `LIMIAR_TENDENCIA` e `MIN_CASOS_TENDENCIA` (`src/train.py`).
* **Métrica principal:** acerto balanceado (ver "Como Ler as Métricas").
* **Resultado do classificador em produção** (`reports/metricas_tendencia.csv`, retreino mensal desde 2015; municípios de treino; acerto balanceado de 0 a 1 e porcentagens, **maior é melhor**, exceto sentido oposto):

  | Antecedência | Acerto balanceado | Acerto | Acerto do "sempre estável" | Subidas detectadas | Alarmes de subida corretos | Sentido oposto |
  |---|---|---|---|---|---|---|
  | 1 semana | 0,43 | 68% | 67% | 17% | 50% | 1% |
  | 2 semanas | 0,56 | 64% | 57% | 40% | 53% | 4% |
  | 3 semanas | 0,62 | 65% | 52% | 51% | 55% | 6% |
  | 4 semanas | 0,64 | 65% | 48% | 56% | 56% | 8% |

  Em 1 semana, os casos raramente mudam mais de 20%, e o ganho sobre o "sempre estável" é pequeno. De 2 a 4 semanas, o classificador acerta de 7 a 18 pontos a mais e detecta de 40% a 56% das subidas. Nos municípios de validação, o resultado é parecido (acerto balanceado de 0,43 a 0,62).

### 8. Rt fora dos modelos, usado só para comparação

* **Decisão:** o Rt do InfoDengue **não é usado em nenhum modelo** do projeto. Ele aparece no painel como indicador e serve de referência de comparação.
* **Motivos:** o Rt é o resultado de outro modelo (do InfoDengue), com premissas que não controlamos; é redundante com a variação dos casos, que o modelo já usa (retirá-lo mudou a razão de erro em no máximo 0,01, no teste com a base de SP); e, fora do modelo, permite comparar as duas abordagens de forma independente.
* **Comparação com o melhor modelo** (`src/experimento_rt.py`, `reports/comparacao_rt.csv`; validação cruzada por município, 2019 em diante). Três formas de usar o Rt: a regra "Rt acima de 1,1 é subida, abaixo de 0,9 é queda", a mesma regra com o `p_rt1` (probabilidade de o Rt ser maior que 1; acima de 0,9 e abaixo de 0,1) e um classificador treinado só com o Rt, que aprende a melhor forma de usá-lo e evita que a comparação dependa de limiares arbitrários. Acerto balanceado, **de 0 a 1, maior é melhor, o baseline tira 0,333**:

  | Modelo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | **LightGBM classificador (melhor modelo)** | **0,419** | **0,554** | **0,605** | **0,623** |
  | Classificador só com o Rt | 0,362 | 0,464 | 0,517 | 0,539 |
  | Regra do `p_rt1` | 0,388 | 0,428 | 0,440 | 0,441 |
  | Regra do Rt | 0,347 | 0,376 | 0,386 | 0,382 |

* **Conclusões:** o nosso modelo é melhor que qualquer uso do Rt, em todos os horizontes, com intervalos de confiança de 95% que excluem zero; nos 15 municípios de validação o resultado se repete. Mesmo o classificador treinado só com o Rt perde de 6 a 9 pontos, então os casos recentes contêm mais informação sobre a tendência do que o Rt. As regras diretas pouco superam o "sempre estável" e dão muitos alarmes falsos (só 21% a 36% dos alarmes da regra do Rt se confirmam). **Ressalva:** o Rt mede a transmissão atual e não foi criado para prever a variação dos casos com o nosso critério; a conclusão vale para essa pergunta específica.

### 9. Clima no modelo

* **Decisão:** o clima das semanas S-1 a S-4 entra no **classificador de tendência**, nos quatro horizontes: o grupo decidiu incluí-lo em 4 semanas, e o teste com o classificador mostrou ganho também em 1 a 3 semanas. O modelo de quantis (número de casos) continua sem clima.
* **Clima usado:** temperatura média, chuva total e umidade média de cada uma das 4 semanas anteriores à semana atual S (o clima de S ainda não está disponível no momento da previsão, por causa do atraso do ERA5).
* **Evidências:**
  * **Base de SP (13 municípios vizinhos, clima parecido):** todas as combinações de clima testadas pioraram a previsão.
  * **Base nacional, LightGBM de regressão** (`reports/generalizacao_configuracoes.csv`; razão de erro, **menor é melhor**): o clima **piora** a previsão de 1 semana, não faz diferença em 2 e 3 semanas e **melhora** a de 4 semanas (−0,014 na razão, cerca de 2%).
  * **Base nacional, LightGBM classificador** (`src/experimento_clima_classificador.py`, `reports/comparacao_clima_classificador.csv`; validação cruzada, 100 municípios; acerto balanceado, **de 0 a 1, maior é melhor, o baseline tira 0,333**):

    | Modelo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
    |---|---|---|---|---|
    | Classificador sem clima | 0,419 | 0,554 | 0,605 | 0,623 |
    | **Classificador com clima S-1 a S-4** | **0,430** | **0,560** | **0,611** | **0,633** |
    | Classificador com clima S-1 a S-5 | 0,427 | 0,560 | 0,611 | 0,632 |

    O clima de S-1 a S-4 melhora o acerto balanceado em todos os horizontes (de +0,006 a +0,010, com intervalos de confiança de 95% que excluem zero). Com 4 semanas, detecta mais subidas (57,2% contra 54,8%), tem mais alarmes corretos (58,1% contra 56,9%) e erra menos o sentido (8,2% contra 8,9%). Nos 15 municípios de validação, as diferenças vão na mesma direção (+0,002 a +0,009), mas só são significativas em 1 e 2 semanas.
* **Interpretação:** o ganho é pequeno (cerca de 1 ponto). O efeito do clima sobre os casos leva semanas para aparecer (desenvolvimento do mosquito, incubação e notificação). O classificador aproveita o clima também nos horizontes curtos porque prevê diretamente a mudança de tendência, onde o clima recente ajuda a distinguir uma subida real de uma oscilação.

### 10. Base nacional e generalização

* **Decisão:** avaliar o projeto principalmente pela **generalização** para municípios não vistos, com uma base de todo o Brasil (decisão 1).
* **Treino nacional melhora SP:** com a base de 74 municípios, treinar com todo o Brasil em vez de só SP reduziu o erro nos municípios de SP de 7% a 10% (treino) e de 18% a 23% (validação).
* **O modelo generaliza** (`src/experimento_generalizacao.py`; validação cruzada, 100 municípios avaliados como desconhecidos; razão de erro, **menor é melhor**): 0,84 em 1 semana, 0,77 em 2, 0,74 em 3 e 0,73 em 4, com intervalos de confiança de 95% inteiramente abaixo de 1. O modelo erra de 16% a 27% menos que o baseline em municípios que não viu.
* **Mais municípios ajudam cada vez menos** (curva de aprendizado; razão de erro com 4 semanas de antecedência): 0,81 com 10 municípios no treino, 0,77 com 20, 0,75 com 40, 0,73 com 60 e 80. De 10 para 40 municípios, o erro cai de 5% a 8%; de 40 para 80, de 2% a 3%. Pela curva ajustada (`erro = a + b·n^(-c)`), dobrar a base para 200 municípios reduziria o erro em cerca de 1%. Com 100 municípios, a quantidade de dados deixou de ser o principal limite. A curva usa 5 pontos e 3 sorteios por ponto, e o limite estimado é uma extrapolação.

### 11. Comparação de modelos para a tendência

* **Pergunta:** o LightGBM é o melhor modelo para prever a tendência em municípios não vistos?
* **Teste** (`src/experimento_modelos.py`; modelos em `src/modelos/`, um arquivo cada; resultados em `reports/comparacao_modelos.csv` e `reports/comparacao_modelos_por_municipio.csv`): 8 modelos com as mesmas informações de entrada, avaliados por validação cruzada por município de 2019 em diante (os anos de 2015 a 2018 serviram para ajustar os hiperparâmetros). A escolha é feita pela validação cruzada; os 15 municípios de validação só confirmam. Acerto balanceado, **de 0 a 1, maior é melhor, o baseline tira 0,333**:

  | Modelo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | Baseline de persistência | 0,333 | 0,333 | 0,333 | 0,333 |
  | Regressão linear | 0,367 | 0,428 | 0,496 | 0,536 |
  | Binomial negativa | 0,368 | 0,443 | 0,520 | 0,565 |
  | Ensemble (média de linear, binomial negativa e LightGBM) | 0,363 | 0,462 | 0,545 | 0,586 |
  | LightGBM por quantis | 0,374 | 0,499 | 0,554 | 0,586 |
  | LightGBM atual (em produção) | 0,387 | 0,509 | 0,562 | 0,592 |
  | LightGBM ajustado | 0,398 | 0,507 | 0,562 | 0,589 |
  | **LightGBM classificador** | **0,419** | **0,554** | **0,605** | **0,623** |

* **Conclusões:**
  * As relações não lineares fazem diferença: regressão linear e binomial negativa (o modelo clássico da epidemiologia para contagens) ficaram bem abaixo. Combinar modelos e ajustar hiperparâmetros não trouxe ganho.
  * O **classificador**, que prevê a tendência diretamente, é o único significativamente melhor que o LightGBM em produção (3 a 4 pontos a mais). Ele detecta mais subidas (55% contra 42% em 4 semanas), mas com mais alarmes falsos (57% dos alarmes corretos, contra 65%) e não produz número de casos.
  * O **LightGBM por quantis** tem o menor erro em número de casos e um intervalo de previsão de 80% bem calibrado (o valor real caiu dentro dele em 78% a 82% das semanas).
* **Decisão:** usar os dois modelos, cada um no que faz melhor. O **classificador com clima** (decisão 9) dá a tendência: no contexto do projeto, o mais importante é alertar uma subida, e ele detecta mais subidas que as alternativas. O **LightGBM por quantis** dá o número de casos, com uma faixa de 80% ("entre X e Y casos"). Os dois são independentes e podem divergir; o painel mostra os dois como são e avisa isso. Tabelas completas e limitações nas seções 16 a 19 de [`docs/historia_decisoes.md`](docs/historia_decisoes.md).

### 12. Previsão com dados atrasados

* **Pergunta:** a avaliação usa os dados já revisados. Quanto pior o modelo seria sem os dados das semanas mais recentes, como acontece em tempo real?
* **Simulação (pior caso)** (`src/experimento_atraso.py`, `reports/experimento_atraso.csv`): na semana X, as semanas X a X-3 não podem ser usadas; o último dado disponível é o de X-4. Para prever X+N, o modelo olha N+4 semanas à frente a partir de X-4, e o baseline repete o valor de X-4. Rodamos também com lacuna de 5 semanas. Na prática existe o nowcast do InfoDengue para as semanas recentes, então o desempenho real fica entre os dois cenários.
* **Resultado** (municípios de treino; erro médio em casos por semana e razão de erro, **menor é melhor**):

  | Antecedência | Modelo sem lacuna | Modelo com lacuna de 4 semanas | Baseline com lacuna de 4 semanas | Razão de erro com lacuna |
  |---|---|---|---|---|
  | 1 semana | 25 | 70 (2,8×) | 99 | 0,70 |
  | 2 semanas | 37 | 78 (2,1×) | 113 | 0,69 |
  | 3 semanas | 48 | 87 (1,8×) | 127 | 0,68 |
  | 4 semanas | 59 | 94 (1,6×) | 140 | 0,67 |

  Nos municípios de validação, o erro do modelo cresce de 1,6 a 2,9 vezes com lacuna de 4 semanas, e a razão de erro fica entre 0,63 e 0,64. Com lacuna de 5 semanas, os erros crescem um pouco mais (de 1,7 a 3,3 vezes), com as mesmas conclusões.
* **Conclusões:** o atraso dos dados custa caro: sem as 4 semanas mais recentes, o erro do modelo aumenta de 1,6 a 2,8 vezes, mais nas antecedências curtas. Mas o modelo continua útil, e sua vantagem sobre o baseline aumenta (erra de 30% a 33% menos, contra 16% a 29% sem lacuna): quanto mais incerta a situação, mais vale um modelo que antecipa a tendência. Em uso real, as previsões devem ser lidas como estimativas de tendência, com margem de erro maior do que a validação sugere.

### 13. Painel

* **Aviso de entrada:** antes de usar o painel, a pessoa lê que ele é resultado de um trabalho acadêmico e que as previsões não devem ser usadas como base para decisões oficiais de vigilância ou de saúde pública, e precisa digitar "entendo". A verificação é feita só no navegador; o aceite fica guardado num cookie por 1 ano, para não perguntar a cada visita.
* **Menu e município:** menu lateral com as seções Indicadores e Detalhes do Modelo; o município é escolhido dentro de cada seção, num seletor agrupado por papel ("Treino · …", "Validação · …") e em ordem alfabética. A escolha é mantida ao trocar de seção.
* **Indicadores** (seção padrão): para o município escolhido, quatro cards com a semana, a **tendência em destaque** (seta e "subida", "estável" ou "queda", do classificador) e os **casos previstos** com a faixa de 80% (do modelo de quantis); abaixo, o gráfico com os casos reais, a previsão passada (com seletores de antecedência e de período) e, nos últimos 12 meses, a previsão das próximas semanas com a faixa.
* **Detalhes do Modelo**, em cinco abas: o modelo atual (o que é, o que usa, desempenho, importância das variáveis e limitações); a comparação com os 11 modelos alternativos (acerto balanceado com intervalos de confiança, evolução por antecedência, tabela completa e matrizes de confusão, com gráficos e tabelas para baixar); os municípios (mapa, contagem por região e por UF, lista com critérios); os dados do município selecionado (indicadores da última semana, histórico completo desde 2010 e acerto de tendência); e o glossário e o dicionário de dados (`docs/glossario.md`).
* **Granularidade semanal:** todos os dados e previsões são por **semana epidemiológica**, a unidade em que o InfoDengue publica os casos e em que a vigilância trabalha.
* **Previsões passadas:** vêm da validação *walk-forward* (decisão 6), em que cada semana foi prevista por modelos retreinados a cada mês só com os dados disponíveis até então; nunca do modelo em produção, que já viu essas semanas. As 10 semanas mais recentes não têm previsão passada (decisão 3).
* **Código:** `app.py` (aviso de entrada e menu) e `painel/` (`indicadores.py`, `detalhes.py`, `dados.py`).

### 14. Robustez da ingestão e reprodutibilidade

* **Falhar cedo:** coluna ou arquivo ausente gera erro explícito, e não valores inventados.
* **Ingestão resistente a falhas:** novas tentativas automáticas em limite de requisições (erro 429), erros temporários do servidor, tempo esgotado e falha de conexão (`src/http_utils.py`).
* **Clima incremental:** só as últimas 12 semanas são baixadas de novo, o que também cobre a revisão do ERA5 preliminar pelo definitivo.
* **Configuração editável:** a lista de municípios fica em `data/config/cidades.csv`, e não no código.
* **Experimentos versionados:** todo resultado citado aqui vem de um script em `src/` e de um arquivo em `reports/`, e pode ser reproduzido.

### Nota sobre os municípios de validação

Todas as escolhas (tipo de modelo, alvo, variáveis, hiperparâmetros, `SEMANAS_INSTAVEIS`) foram feitas com base nos **municípios de treino**. Os 15 municípios de validação só medem a generalização e nunca foram usados como critério de escolha.
