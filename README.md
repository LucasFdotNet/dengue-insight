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
   * **Fotos dos dados (`src/snapshot.py`):** ao fim de cada ingestão, guarda uma cópia compactada dos dados baixados em `data/snapshots/AAAA-MM-DD/`, com um manifesto (linhas, primeira e última semana e SHA-256 de cada município). Os dados do InfoDengue mudam de uma coleta para outra; as fotos permitem reproduzir resultados antigos e medir essas mudanças (`src/revisao_dados.py`, decisão 3).
2. **Pré-processamento (`src/preprocessing.py`):** une casos e clima por semana, interpola valores faltantes apenas entre valores conhecidos e calcula as variáveis do modelo.
3. **Treinamento e avaliação (`src/train.py`):** treina os dois modelos de produção, cada um único para todos os municípios de treino e com uma versão por antecedência (1 a 4 semanas): o **LightGBM classificador com clima**, para a tendência, e o **LightGBM por quantis**, para o número de casos com intervalo de 80%. Avalia os dois com validação *walk-forward* com retreino mensal contra o baseline de persistência (cerca de 20 minutos). Os modelos usados pelo painel são treinados na exportação (item 6).
4. **Análise exploratória (`src/eda.py`):** gera matrizes de correlação e gráficos de casos contra clima.
5. **Pipeline completo (`src/pipeline_completo.py`):** refaz, na ordem, tudo o que depende dos dados (pré-processamento, modelos de produção, análise exploratória, experimentos, comparação entre fotos e os números do relatório em `reports/relatorio/`, por `src/numeros_relatorio.py`). Retoma de onde parou se for interrompido (decisão 14).
6. **Painel estático (`web/`, decisão 17):** site sem servidor de aplicação, publicado no Cloudflare Pages. `src/exportar_painel.py` treina os modelos de produção de níveis e de casos e grava um JSON por município em `web/public/dados/`, carregado só quando o município é escolhido. Seções **Indicadores** (último nível confirmado, alerta, casos notificados até o momento, limiares, próximas semanas e gráfico de casos), **Avaliação** (quadradinhos e casos previstos no passado, e as métricas gerais com intervalos de confiança) e **Ajuda** (em construção).

**Experimentos** (cada um grava seus resultados em `reports/`; detalhes na seção "Decisões de Projeto"):

| Script | Pergunta |
|---|---|
| `src/experimento_modelos.py` | Qual modelo prevê melhor a tendência? (8 modelos, um arquivo cada em `src/modelos/`) |
| `src/experimento_classificadores.py` | Outros classificadores (XGBoost, Random Forest, redes neurais MLP e LSTM) ou outra regra de decisão superam o classificador em produção? (decisão 15) |
| `src/experimento_clima_classificador.py` | O clima melhora o classificador de tendência? |
| `src/experimento_estados.py` | Prevendo o nível (normal ou alto) em vez da tendência, o painel avisaria as epidemias a tempo? (decisão 16) |
| `src/experimento_niveis_robustez.py` | Os níveis e o alerta resistem a dados atrasados? O modelo indica a desmobilização? Intervalos de confiança (decisão 16) |
| `src/experimento_casos_atraso.py` | Quão bons são os casos aproximados que o painel mostra, previstos a partir da última semana confirmada? (decisão 17) |
| `src/experimento_niveis.py` | Três níveis (verde, amarelo, vermelho): qual definição de limiares, e quão bem o modelo prevê e alerta? Gera os gráficos de quadradinhos e os de casos com os limiares e a previsão do modelo de quantis (decisão 16) |
| `src/experimento_rt.py` | O melhor modelo é mais útil que o Rt do InfoDengue? |
| `src/experimento_generalizacao.py` | O modelo generaliza para municípios não vistos? Mais municípios ajudam? O clima ajuda? |
| `src/experimento_atraso.py` | Quanto o modelo piora se os dados recentes ainda não estiverem disponíveis? |
| `src/experimento_clima_semanal.py` | Treino só com SP contra treino nacional; clima de semanas específicas (base de 63 municípios; histórico) |
| `src/experimento_variaveis.py` | Rt e clima no modelo (teste feito com a base de SP; histórico) |

---

## 📦 Tecnologias e Pacotes Utilizados

* **Linguagem:** Python 3 (testado com 3.14) no pipeline; TypeScript no painel
* **Dados:** `pandas`, `numpy`, `requests`
* **Modelagem:** `lightgbm`, `scikit-learn`, `statsmodels`, `scipy`, `joblib`
* **Gráficos dos experimentos:** `matplotlib`, `seaborn`
* **Painel estático (`web/`):** TypeScript, Vite e Observable Plot (Node.js 20 ou mais recente)

As versões estão fixadas em `requirements.txt`. O experimento de classificadores (decisão 15) usa também `xgboost`, `torch` e `pyarrow`, em `requirements-experimentos.txt`; o painel não precisa deles.

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
   ```

   Depois, o painel estático (abaixo).

   Os experimentos são opcionais e rodam da mesma forma, por exemplo `python -m src.experimento_modelos` (cerca de 45 minutos).

   **Tudo de uma vez (para atualizar os números com dados novos):** `python -m src.pipeline_completo --baixar` baixa os dados (com foto), refaz os modelos de produção, a análise exploratória, todos os experimentos e os números do relatório. Leva cerca de 7 horas, a maior parte no experimento de classificadores; precisa de `requirements-experimentos.txt`. Se for interrompido, rodar de novo continua do passo onde parou (sem `--baixar`, para não trocar os dados no meio). No Windows, `powershell -ExecutionPolicy Bypass -File scripts
odar_pipeline.ps1 --baixar` roda o pipeline em segundo plano e impede que o computador suspenda até ele terminar; o andamento fica em `reports/logs/`.

   **Painel estático** (depois dos experimentos de níveis e de casos, ou do pipeline completo):
   ```bash
   python -m src.exportar_painel     # treina os modelos de produção e grava web/public/dados/
   cd web
   npm install
   npm run dev                       # abre o painel em http://localhost:5173
   npm run build                     # gera o site em web/dist/
   ```
   No Cloudflare Pages: diretório raiz `web`, comando de build `npm run build`, diretório de saída `dist`. Os dados já vão no repositório, porque o deploy não roda o pipeline; cada atualização é "rodar o pipeline e publicar de novo".

   **Sobre a ingestão de clima:** a Open-Meteo limita o uso gratuito por minuto, por hora e por dia, e a série de 16 anos de cada município consome boa parte desses limites. O script espera sozinho nos limites por minuto e por hora, então a primeira execução completa (115 municípios) leva algumas horas e pode atingir o limite diário. Nesse caso, ele para, mantém o que já foi salvo e avisa para rodar de novo mais tarde; a nova execução continua de onde parou. Nas execuções seguintes, só as últimas 12 semanas de cada município são baixadas. Para baixar tudo de novo: `python -m src.ingestion_clima --completo`.

   **Sem os dados de clima:** `python -m src.preprocessing --sem-clima` processa com as colunas de clima vazias, o que permite rodar o pipeline enquanto a ingestão de clima não termina. Nesse modo, o classificador de tendência é treinado sem clima e **não reproduz o modelo em produção** (que usa o clima de S-1 a S-4, decisão 9); o modelo de quantis não é afetado. Para os resultados oficiais, o painel e a análise exploratória, rode o processamento completo.

---

## 📏 Como Ler as Métricas

Os resultados usam três tipos de número. Cada tabela abaixo indica qual está usando.

| Métrica | O que é | Como ler |
|---|---|---|
| **Razão de erro** | Erro médio do modelo, em casos por semana, dividido pelo erro médio do baseline | **Menor é melhor.** Abaixo de 1, o modelo erra menos que o baseline (0,75 = erro 25% menor) |
| **Acerto de tendência** | Fração das semanas em que o modelo acertou se os casos iriam subir, ficar estáveis ou cair | **Maior é melhor.** Comparar com o "sempre estável", que já acerta muito porque a maioria das semanas é estável |
| **Acerto balanceado** | Média do acerto em cada uma das três situações (subiu, ficou estável, caiu), calculado separadamente | **Maior é melhor**, de 0 a 1. O baseline tira 0,333. **Não** é uma divisão pelo baseline |

**Exemplo de acerto balanceado** (LightGBM de regressão, 4 semanas de antecedência, semanas de 100 municípios somadas): o modelo acertou 41,6% das semanas em que os casos subiram, 75,3% das estáveis e 60,7% das que caíram. O acerto balanceado é a média: (41,6% + 75,3% + 60,7%) / 3 = **0,592**. O baseline, que sempre diz "estável", acerta 0%, 100% e 0%: média de **0,333**.

**Baseline de persistência:** a previsão mais simples possível, "daqui a H semanas haverá o mesmo número de casos de hoje". Na tendência, equivale a dizer sempre "estável". Um modelo só é útil se for melhor que isso.

Outras métricas de tendência: **log loss** e **Brier**, que avaliam as probabilidades que os classificadores dão a cada tendência, e não só a tendência escolhida (**menor é melhor**; não dependem da regra de decisão, decisão 15); **subidas detectadas** (das semanas em que os casos subiram, em quantas o modelo previu subida), **alarmes de subida corretos** (das vezes em que o modelo previu subida, em quantas os casos subiram) e **sentido oposto** (semanas em que o modelo previu subida e os casos caíram, ou o contrário; menor é melhor).

---

## 🧭 Decisões de Projeto

Estado atual das decisões, com os números da base atual (115 municípios, dados até a semana de 27/09/2026, baixados em 09/10/2026). Quando um resultado vem de uma etapa anterior do projeto, isso é indicado. A evolução de cada decisão, os testes intermediários e as conclusões que mudaram ao longo do caminho estão em [`docs/historia_decisoes.md`](docs/historia_decisoes.md).

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

**Etapa 4: substituição dos municípios sem nowcast (12, em 11/10/2026)**
* **Por quê:** nos municípios em que o InfoDengue não publica o *nowcast* (a estimativa que corrige o atraso das notificações), as semanas recentes têm só os casos já notificados e ficam bem mais incompletas (decisão 3). O painel teria de partir de uma semana mais antiga nesses municípios; para que todos tenham o mesmo tratamento, o grupo decidiu trocá-los. Eram 12, todos de treino: Balsas, Barreiras, Caxias do Sul, Dourados, Imperatriz, Itacoatiara, Itaperuna, Ji-Paraná, Lagarto, Luís Eduardo Magalhães, Rondonópolis e Santarém (sem intervalo de nowcast em nenhuma das últimas 10 semanas).
* **Como:** os critérios por tamanho e por histórico de surtos das etapas 2 e 3 escolhiam, na prática, entre candidatos equivalentes, então os substitutos foram **sorteados** (semente fixa) entre os elegíveis da mesma UF: mais de 100 mil habitantes, não capital, a mais de 50 km da capital e de qualquer município da lista, e com nowcast. Quando a UF não tinha elegível, o sorteio foi na macrorregião: no Maranhão nenhum elegível tem nowcast; no Amazonas, em Rondônia e em Sergipe não há outro município elegível; no Rio de Janeiro, nenhum elegível tem nowcast. Script: `scripts/substituir_sem_nowcast.py`; elegíveis de cada vaga e o sorteado em `reports/substituicao_municipios.csv`.
* **Resultado:** Pelotas (RS, no lugar de Caxias do Sul), Três Lagoas (MS, Dourados), Sorriso (MT, Rondonópolis), Marabá (PA, Santarém), Porto Seguro (BA, Barreiras), Alagoinhas (BA, Luís Eduardo Magalhães), Eunápolis (BA, Imperatriz), Patos (PB, Balsas), Santo Antônio de Jesus (BA, Lagarto), Cametá (PA, Itacoatiara), Abaetetuba (PA, Ji-Paraná) e Itanhaém (SP, Itaperuna). Municípios de treino por UF: Bahia de 6 para 8, Pará de 4 para 6, Paraíba de 2 para 3 e São Paulo de 21 para 22; Maranhão de 3 para 1, Amazonas, Rondônia e Sergipe de 2 para 1 e Rio de Janeiro de 7 para 6. A proporção à população (etapa 3) deixa de valer exatamente.
* **Se um município perder o nowcast:** a exportação do painel avisa no log (`src/exportar_painel.py`), e o script pode ser rodado de novo.

### 2. Período dos dados

* **Decisão:** séries semanais de 2010 até a semana mais recente.
* **Motivo:** o InfoDengue disponibiliza a série desde 2010 para todos os municípios escolhidos. Mais anos significam mais epidemias para o modelo aprender.

### 3. Descarte das semanas finais instáveis

* **Decisão:** as últimas 10 semanas de cada município (`SEMANAS_INSTAVEIS`, em `src/train.py`) ficam fora do treino e da avaliação.
* **Motivo:** o número de casos das semanas mais recentes ainda é uma estimativa (*nowcast*), revisada pelo InfoDengue à medida que chegam notificações atrasadas.
* **Como chegamos a 10:** o InfoDengue informa um intervalo de incerteza do nowcast para cada semana. Contamos, em cada município de treino, quantas semanas finais ainda têm esse intervalo aberto, e adotamos o máximo. Foram 10 semanas nas três bases (SP, 74 e 115 municípios), em municípios como Cosmópolis, Indaiatuba, Manaus, Teresina, Varginha e Sobral. Municípios sem nowcast publicado, como Campinas, também têm a última semana visivelmente incompleta.
* **Quanto os números mudam depois** (`src/revisao_dados.py`, `reports/revisao_dados.csv`): comparando a foto dos dados de 27/09/2026 com a de 09/10/2026, 12 dias depois, a soma dos casos estimados dos 115 municípios na semana mais recente subiu 45%, na anterior 18%, 3 semanas antes 5% e 5 semanas antes 2%; de 8 semanas para trás, menos de 1%. Nenhuma semana com mais de 1 ano mudou. O corte de 10 semanas cobre o período em que os números ainda mudam. Mesmo com o nowcast, a última semana ainda subestimava os casos. **Limitação:** é uma única comparação, de 12 dias; cada nova coleta acrescenta uma comparação ao arquivo.
* **Ponto de partida das previsões:** em 09/2026, 39 dos 115 municípios não tinham nowcast publicado nas semanas recentes, e essas semanas tinham só os casos já notificados (em relação ao nível das semanas anteriores, a última semana desses municípios tinha 23% dos casos, a penúltima 63% e a antepenúltima 76%, contra 84%, 82% e 87% nos municípios com nowcast). O primeiro painel partia, nesses municípios, da última semana completa (a 4ª mais recente). Em 10/2026, só 12 continuavam sem nowcast, e o grupo decidiu substituí-los (decisão 1, etapa 4), para que todos tenham o mesmo tratamento: o painel parte da semana atual menos 2 em todos os municípios (decisão 17).
* **Detalhe técnico:** o corte é feito depois de descartar as semanas sem alvo, para que também saiam as semanas cujo alvo (H semanas à frente) cai no período instável. Ele fica no treino, e não no pré-processamento, porque o painel precisa mostrar as semanas recentes.

### 4. Fonte dos dados climáticos: Open-Meteo (ERA5)

* **Decisão:** usar a reanálise **ERA5** (Copernicus/ECMWF), pela [Open-Meteo Historical API](https://open-meteo.com/en/docs/historical-weather-api) (`models=era5`), a partir da latitude e longitude de cada município, no lugar do clima do InfoDengue.
* **Motivos:** o clima do InfoDengue não tem chuva; de 2010 a 2022, vários municípios compartilhavam a mesma estação meteorológica (temperatura idêntica em Campinas, Cosmópolis e Piracicaba em todas as semanas); e a série mudou de fonte no meio do período.
* **Alternativas descartadas:** ERA5-Land (resolução melhor, mas sem chuva) e Mosqlimate (exige chave de API).
* **Limitações:** a grade do ERA5 tem 0,25°, então municípios muito próximos caem no mesmo ponto (os 115 municípios ocupam 109 pontos); e os dados chegam com cerca de 6 dias de atraso.
* **Agregação:** semana epidemiológica (domingo a sábado); só entram semanas com os 7 dias.
* **Atribuição:** dados ERA5 do Copernicus Climate Change Service, licença CC BY 4.0; acesso via Open-Meteo.
* **Uso:** o clima aparece no painel e na análise exploratória e entra no **classificador de tendência** (temperatura média, chuva e umidade das semanas S-1 a S-4; decisão 9). O modelo de quantis (número de casos) não usa clima.

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

* **Variáveis comuns aos modelos:** casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás e semana do ano (`FEATURES`, em `src/train.py`). O classificador de tendência acrescenta o clima das semanas S-1 a S-4 (decisão 9); o modelo de quantis usa só as variáveis comuns. **Nenhum modelo usa o Rt** (decisão 8). A incidência por 100 mil habitantes foi retirada por ser redundante com os casos.
* **Modelos em produção** (decisão 11): LightGBM **classificador** com clima das semanas S-1 a S-4, para a tendência, e LightGBM **por quantis**, para o número de casos com intervalo de 80%. Os dois usam hiperparâmetros fixos (300 árvores, taxa de aprendizado 0,05); ajustá-los não trouxe ganho (decisões 11 e 15).

### 6. Avaliação: walk-forward, validação cruzada por município e baseline

* **Walk-forward com retreino mensal:** para cada mês desde 2015, um modelo é treinado **só com o que já era conhecido** no início do mês e prevê as semanas daquele mês. Simula o uso real e garante que nenhuma informação do período previsto entre no modelo que o previu.
* **Validação espacial:** os 15 municípios de validação nunca entram no treino. Para os experimentos de generalização e de modelos, os 100 municípios de treino também são avaliados como desconhecidos, por **validação cruzada por município** (5 grupos de 20; cada grupo é previsto por modelos treinados com os outros 80).
* **Intervalos de confiança de 95%** por *bootstrap* sobre municípios: sorteamos municípios com reposição 2.000 vezes. A unidade de sorteio é o município, e não a semana, porque as semanas de um mesmo município são muito parecidas entre si.
* **Resultado atual do modelo de quantis (número de casos)** (`reports/metricas_gerais.csv`; razão de erro, **menor é melhor**, abaixo de 1 o modelo supera o baseline):

  | Grupo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | Municípios de treino (100) | 0,83 | 0,76 | 0,73 | 0,71 |
  | Municípios de validação (15) | 0,79 | 0,71 | 0,68 | 0,67 |

* **Por ano** (`reports/metricas_por_ano.csv`): nos municípios de treino, a razão fica abaixo de 1 em todos os anos de 2015 a 2026. Os anos mais difíceis são os de transmissão baixa ou estável (2017, 2018 e o parcial de 2026, de 0,88 a 0,97), e os melhores, os de epidemia (2024, de 0,64 a 0,76). Nos municípios de validação, só 2017 fica acima de 1 (até 1,11 em 4 semanas).
* **Por município de validação** (`reports/metricas_modelos.csv`): o modelo supera o baseline com folga em Blumenau, Sorocaba, Vitória da Conquista e Bauru (0,56 a 0,64 em 4 semanas), mas empata em Parauapebas e Manacapuru (Norte), Caruaru e Sinop (0,94 a 1,04). A generalização é mais fraca nas regiões com menos municípios parecidos no treino.
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
  | Classificador só com o Rt | 0,362 | 0,464 | 0,516 | 0,538 |
  | Regra do `p_rt1` | 0,388 | 0,428 | 0,440 | 0,440 |
  | Regra do Rt | 0,347 | 0,376 | 0,385 | 0,382 |

* **Conclusões:** o nosso modelo é melhor que qualquer uso do Rt, em todos os horizontes, com intervalos de confiança de 95% que excluem zero; nos 15 municípios de validação o resultado se repete, com uma exceção: em 1 semana, a regra do `p_rt1` empata com o nosso modelo. Mesmo o classificador treinado só com o Rt perde de 6 a 9 pontos, então os casos recentes contêm mais informação sobre a tendência do que o Rt. As regras diretas pouco superam o "sempre estável" e dão muitos alarmes falsos (só 21% a 36% dos alarmes da regra do Rt se confirmam). **Ressalva:** o Rt mede a transmissão atual e não foi criado para prever a variação dos casos com o nosso critério; a conclusão vale para essa pergunta específica.

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
    | Classificador com clima S-1 a S-5 | 0,427 | 0,561 | 0,612 | 0,632 |

    O clima de S-1 a S-4 melhora o acerto balanceado em todos os horizontes (de +0,006 a +0,010, com intervalos de confiança de 95% que excluem zero). Com 4 semanas, detecta mais subidas (57,0% contra 54,7%), tem mais alarmes corretos (58,1% contra 57,0%) e erra menos o sentido (8,2% contra 8,9%). Nos 15 municípios de validação, as diferenças vão na mesma direção (+0,002 a +0,009), mas só são significativas em 2 semanas (em 1 semana, o limite inferior do intervalo fica em zero).
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
  | Regressão linear | 0,367 | 0,429 | 0,496 | 0,536 |
  | Binomial negativa | 0,368 | 0,444 | 0,521 | 0,565 |
  | Ensemble (média de linear, binomial negativa e LightGBM) | 0,363 | 0,463 | 0,546 | 0,586 |
  | LightGBM por quantis | 0,373 | 0,499 | 0,554 | 0,587 |
  | LightGBM de regressão (usado no painel antes desta decisão) | 0,387 | 0,510 | 0,563 | 0,592 |
  | LightGBM ajustado | 0,398 | 0,507 | 0,562 | 0,589 |
  | **LightGBM classificador** | **0,419** | **0,554** | **0,605** | **0,623** |

* **Conclusões:**
  * As relações não lineares fazem diferença: regressão linear e binomial negativa (o modelo clássico da epidemiologia para contagens) ficaram bem abaixo. Combinar modelos e ajustar hiperparâmetros não trouxe ganho.
  * O **classificador**, que prevê a tendência diretamente, é o único significativamente melhor que o LightGBM de regressão (3 a 4 pontos a mais). Ele detecta mais subidas (55% contra 42% em 4 semanas), mas com mais alarmes falsos (57% dos alarmes corretos, contra 65%) e não produz número de casos.
  * O **LightGBM por quantis** tem o menor erro em número de casos e um intervalo de previsão de 80% bem calibrado (o valor real caiu dentro dele em 78% a 82% das semanas).
* **Decisão:** usar os dois modelos, cada um no que faz melhor. O **classificador com clima** (decisão 9) dá a tendência: no contexto do projeto, o mais importante é alertar uma subida, e ele detecta mais subidas que as alternativas. O **LightGBM por quantis** dá o número de casos, com uma faixa de 80% ("entre X e Y casos"). Os dois são independentes e podem divergir; o painel mostra os dois como são e avisa isso. Tabelas completas e limitações nas seções 16 a 19 de [`docs/historia_decisoes.md`](docs/historia_decisoes.md). Outros tipos de modelo (XGBoost, Random Forest e redes neurais) foram comparados depois, na decisão 15.

### 12. Previsão com dados atrasados

* **Pergunta:** a avaliação usa os dados já revisados. Quanto pior o modelo seria sem os dados das semanas mais recentes, como acontece em tempo real?
* **Simulação (pior caso)** (`src/experimento_atraso.py`, `reports/experimento_atraso.csv`): na semana X, as semanas X a X-3 não podem ser usadas; o último dado disponível é o de X-4. Para prever X+N, o modelo olha N+4 semanas à frente a partir de X-4, e o baseline repete o valor de X-4. Rodamos também com lacuna de 5 semanas. O experimento usa o LightGBM de regressão (sem clima), e não os modelos em produção (decisão 11); a conclusão sobre o efeito do atraso deve valer para eles, mas não foi medida diretamente. Na prática existe o nowcast do InfoDengue para as semanas recentes, então o desempenho real fica entre os dois cenários.
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
* **Substituído pela decisão 17** (painel estático, 11/10/2026). O código do painel em Streamlit (`app.py`, `painel/`, `src/predict.py` e os modelos de tendência salvos em `models/`) foi removido; continua no histórico do git.

### 14. Robustez da ingestão e reprodutibilidade

* **Falhar cedo:** coluna ou arquivo ausente gera erro explícito, e não valores inventados.
* **Ingestão resistente a falhas:** novas tentativas automáticas em limite de requisições (erro 429), erros temporários do servidor, tempo esgotado e falha de conexão (`src/http_utils.py`).
* **Clima incremental:** só as últimas 12 semanas são baixadas de novo, o que também cobre a revisão do ERA5 preliminar pelo definitivo.
* **Configuração editável:** a lista de municípios fica em `data/config/cidades.csv`, e não no código.
* **Experimentos versionados:** todo resultado citado aqui vem de um script em `src/` e de um arquivo em `reports/`, e pode ser reproduzido.
* **Fotos dos dados:** cada ingestão guarda os dados baixados em `data/snapshots/AAAA-MM-DD/` (decisão 3). Como o InfoDengue revisa as semanas recentes, é a única forma de saber exatamente com quais dados um resultado foi calculado.
* **Pipeline retomável:** `src/pipeline_completo.py` registra cada passo concluído em `reports/pipeline_estado.json`, com a identificação dos dados processados; se for interrompido, continua do passo onde parou, e se os dados mudarem, refaz tudo. O experimento de classificadores também guarda as previsões de cada treino em `reports/cache/` (fora do git) e retoma dentro do passo. Os experimentos históricos, feitos com bases anteriores (`experimento_variaveis.py` e `experimento_clima_semanal.py`), ficam fora do pipeline: os resultados citados na história das decisões são os dos commits originais.

### 15. Outros modelos e regra de decisão

* **Pergunta:** outros tipos de modelo (XGBoost, Random Forest e redes neurais) ou outra forma de transformar as probabilidades em tendência superam o classificador em produção?
* **Teste** (`src/experimento_classificadores.py`; modelos em `src/modelos/`; resultados em `reports/comparacao_classificadores*.csv` e `reports/ajuste_classificadores*`): todos com as mesmas informações do classificador em produção (casos recentes e clima de S-1 a S-4), na mesma avaliação da decisão 11 (validação cruzada por município, validação final nos 15 municípios, walk-forward de 2019 em diante com retreino trimestral):
  * **LightGBM ajustado**, **XGBoost** (outro boosting de árvores) e **Random Forest** (árvores independentes combinadas por votação);
  * **MLP** (rede neural com as mesmas variáveis) e **LSTM** (rede neural que lê a sequência das últimas 12 semanas de casos e clima e aprende sozinha quais semanas importam), cada uma com 3 sementes;
  * **LightGBM com janela de 12 semanas**, com a mesma informação que a LSTM recebe, para separar o efeito do modelo do efeito de olhar mais semanas para trás;
  * **LightGBM com peso igual para as três tendências** e a **decisão balanceada** (glossário), duas formas de avisar mais subidas.
* **Mesmo orçamento de ajuste para todos:** a configuração padrão de cada modelo e mais 8 alternativas, escolhidas pelo acerto balanceado médio na validação cruzada de 2015 a 2018. Os anos da comparação e os municípios de validação não participam da escolha.
* **Resultado** (validação cruzada, 2019 em diante; acerto balanceado, **de 0 a 1, maior é melhor, o baseline tira 0,333**; * = diferença significativa em relação ao modelo em produção):

  | Modelo | 1 sem. | 2 sem. | 3 sem. | 4 sem. |
  |---|---|---|---|---|
  | **LightGBM classificador com clima (em produção)** | **0,430** | **0,560** | **0,611** | **0,633** |
  | LightGBM ajustado | 0,429 | 0,561 | 0,611 | 0,635 |
  | LightGBM com janela de 12 semanas | 0,433 | 0,565* | 0,615* | 0,635 |
  | XGBoost | 0,427 | 0,562 | 0,612 | 0,634 |
  | Random Forest | 0,418* | 0,554* | 0,607* | 0,631 |
  | MLP | 0,419* | 0,554* | 0,611 | 0,632 |
  | LSTM | 0,419* | 0,557 | 0,609 | 0,630 |
  | LightGBM com peso igual para as três tendências | 0,581* | 0,610* | 0,628* | 0,638 |
  | **Em produção + decisão balanceada** | **0,580*** | **0,612*** | **0,630*** | **0,640** |

* **Conclusões:**
  * **Nenhum modelo supera o de produção de forma relevante.** XGBoost e LightGBM ajustado empatam; a janela de 12 semanas ganha menos de meio ponto; Random Forest e as redes neurais ficam um pouco abaixo nos horizontes curtos e têm probabilidades piores (log loss de 0,790 contra 0,780 em 4 semanas). Nos 15 municípios de validação e de 2022 em diante, o quadro é o mesmo. Com estas variáveis, o limite está na informação disponível, e não no modelo.
  * **Ajustar hiperparâmetros não trouxe ganho** (a não ser para o Random Forest, cujo padrão era ruim), como já tinha acontecido na decisão 11.
  * **O peso por classe não é um modelo melhor, é outra regra de decisão.** Aplicar a decisão balanceada às probabilidades do modelo em produção, sem treinar de novo, dá o mesmo resultado, com probabilidades melhores (log loss de 0,738 contra 0,957 em 1 semana). A troca: em 1 semana, as subidas detectadas passam de 18% para 63%, mas os alarmes de subida corretos caem de 50% para 35% e o acerto simples de 66% para 49%; em 4 semanas, de 57% para 69% das subidas, com 52% dos alarmes corretos contra 58%. Nos 15 municípios de validação, a decisão balanceada piora 3 e 4 semanas (0,590 contra 0,616 em 4 semanas).
  * **Exigir mais confiança nos alarmes não resolve.** Em 2015–2018, nenhum ponto de corte da probabilidade de subida chega a 2 alarmes corretos para cada falso, a não ser avisando menos de 8% das subidas; em 1 semana, nem isso.
* **Ruído numérico:** mudar só o último dígito (10⁻¹⁵) das variações de casos, ao recalculá-las, mudou o acerto balanceado de 1 semana em até 0,004 (o LightGBM escolhe alguns cortes diferentes). Diferenças desse tamanho entre modelos não devem ser interpretadas. O experimento foi refeito com as variáveis exatamente iguais às do pré-processamento.
* **Decisão:** manter o LightGBM classificador com clima, sem ajuste. Estes resultados levaram a rever a pergunta do projeto: a tendência relativa (variação de 20%) não diz se o município precisa mobilizar recursos; ver a decisão 16.

### 16. Níveis de incidência (verde, amarelo, vermelho) e alerta de mobilização

* **Objetivo revisto:** o painel deve ajudar gestores de saúde a se anteciparem: **mobilizar** recursos (ações contra criadouros, equipes de atendimento) quando o município vai entrar numa epidemia, **mantê-los** enquanto ela dura e planejar a **desmobilização** quando ela termina. Alarmes falsos têm custo (a mobilização tira recursos de outras ações) e, se forem frequentes, levam os gestores a ignorar os alarmes.
* **Por que a tendência não basta** (decisões 7 e 15): a tendência relativa (variação de 20% e 5 casos) trata igual ir de 5 para 8 casos e de 500 para 800; não mostra que uma epidemia em platô exige manter as equipes; e não distingue a queda depois do pico (desmobilizar) da queda em período normal (nada a fazer). O gestor decide pelo **nível** em que os casos vão estar.
* **Decisão:** prever o **nível** de cada município nas próximas semanas, em três faixas, e emitir um **alerta de mobilização** quando o município deve entrar no vermelho:
  * **verde:** abaixo do limiar pré-epidêmico;
  * **amarelo:** acima do limiar pré-epidêmico (a temporada de transmissão começou);
  * **vermelho:** acima do limiar epidêmico.
* **Limiares pelo MEM** (*Moving Epidemic Method*; Vega et al., 2013 e 2015), o método que o InfoDengue usa e que o Plano de Contingência do Ministério da Saúde cita como apoio. Reimplementado em Python (`src/mem.py`), seguindo o pacote R `mem` e as configurações do InfoDengue: temporada da semana epidemiológica 41 à 40; até 10 temporadas anteriores; período epidêmico de cada temporada pela curva MAP; limiares como limite superior do intervalo de confiança de 95% da média geométrica das semanas pré-epidêmicas e epidêmicas; segundo passe sem as temporadas que não passaram do limiar pré-epidêmico; mínimos de 5 e 10 casos. Os limiares de cada temporada usam só as anteriores (as temporadas antes de 2014-2015 usam as de 2010-2011 a 2013-2014), sobre a incidência por 100 mil habitantes (população do Censo 2022). Referências e o que tiramos de cada uma: [`docs/referencias.md`](docs/referencias.md).
* **Validação da reimplementação:** com os dados de 2010 a 2022, os limiares do projeto têm correlação de 0,996 (pré-epidêmico) e 0,992 (epidêmico) com os publicados pelo InfoDengue para os mesmos municípios, e ficam em média 5% abaixo (os dados foram revisados desde então). Nenhum indicador calculado pelo InfoDengue entra nos modelos: os limiares são calculados pelo projeto, só a partir dos casos.
* **Alternativas consideradas e por que foram descartadas** (`src/estados.py`, `src/experimento_estados.py`, `src/experimento_niveis.py`):

  | Alternativa | O que é | Por que não, frente ao objetivo |
  |---|---|---|
  | Tendência relativa (decisão 7) | Sobe, estável ou cai, por variação de 20% e 5 casos | Não diz o nível nem quando manter ou desmobilizar |
  | Nível do InfoDengue (`nivel_inc`) | Os limiares MEM calculados pelo InfoDengue | Regra do projeto: nenhum dado calculado pelo InfoDengue nos modelos; usado só para validar |
  | Dois estados (normal e alto, percentil 90 do histórico do município) | Primeira versão por níveis | Funciona (avisa 67% das epidemias com 52% de alarmes corretos), mas não separa "alta que merece atenção" de epidemia |
  | Percentis 75 e 90 (definição A) | Aproximação dos limiares por percentis | Sem base direta na literatura; resultado parecido com o MEM |
  | Percentis 80 e 97 (definição B) | Vermelho só nos 3% de semanas mais altas | O alerta funciona bem (84% das epidemias), mas o vermelho vira um evento raro (7% das semanas), diferente do nível epidêmico usado na vigilância, e a definição não tem base direta na literatura |
  | Canal endêmico do Ministério da Saúde (definição C) | Mediana e Q3 da mesma semana nos 5 anos anteriores (Plano de Contingência, 2025, seção 5) | Mede "acima do esperado para a época". Com o aumento da dengue de 2022 a 2025, municípios ficaram vermelhos por anos seguidos (Campinas e Blumenau, quase 2 anos, inclusive no inverno); 36% das semanas ficam vermelhas; o modelo quase não supera a persistência, e o alerta praticamente nunca acende. Útil para acompanhar a temporada, não para decidir quando mobilizar |

* **Modelo:** LightGBM com as mesmas variáveis do classificador de tendência e a distância da semana atual a cada limiar (`src/modelos/nivel_lightgbm.py`); dá a probabilidade de cada nível em S+2, S+3 e S+4. O nível previsto é o **mais provável**. (Prever vermelho sempre que a chance passa de um corte calibrado prevê vermelho demais semana a semana e perde para a persistência; foi descartado.)
* **Alerta de mobilização:** acende numa semana em que o município não está no vermelho, se a maior probabilidade de vermelho em S+2 a S+4 passa de um corte. O corte é escolhido a cada trimestre só com o passado: o menor em que pelo menos metade dos alarmes anteriores se confirmou (**1 alarme correto para cada falso**; o critério de 2 para 1, testado antes, é inatingível com estas informações, decisão 15). Os cortes ficaram estáveis ao longo do tempo.
* **Avaliação por episódio** (Buehler et al., 2004): um **episódio** é uma sequência de pelo menos 2 semanas no vermelho (juntando interrupções de 1 semana); uma epidemia foi **avisada** se houve alerta nas 4 semanas antes do início; um alarme é **correto** se um episódio começa durante ele ou até 4 semanas depois.
* **Resultado** (de 2019 em diante; os cortes usam só o passado):

  | | Validação cruzada (100 municípios) | Validação (15 municípios nunca vistos) |
  |---|---|---|
  | Epidemias no vermelho (episódios) | 492 | 79 |
  | **Alerta: epidemias avisadas antes de começar** | **74%** (69% a 79%) | **71%** (58% a 84%) |
  | Alerta: antecedência (mediana) | 3 semanas | 3 semanas |
  | Alerta: alarmes que se confirmaram | 52% (49% a 56%) | 54% (44% a 64%) |
  | Alerta: alarmes falsos por município por ano | 0,49 (0,44 a 0,55) | 0,46 (0,32 a 0,61) |
  | Regra simples (casos subindo há 2 semanas e acima de metade do limiar): avisadas / corretos / falsos por ano | 68% / 36% / 0,82 | 71% / 37% / 0,90 |
  | Nível previsto: acerto com 4 semanas (modelo / persistência) | 79% / 76% | 81% / 77% |
  | Nível previsto: ganho sobre a persistência com 4 semanas | +3,4 pontos (2,6 a 4,1) | +3,3 pontos (1,6 a 5,2) |
  | **Desmobilização: fins de epidemia indicados nas 2 semanas antes** | **79%** (75% a 83%) | **81%** (69% a 91%) |
  | Desmobilização: avisos prematuros por epidemia | 1,0 (0,8 a 1,1) | 1,2 (0,8 a 1,7) |
  | Regra simples de queda (casos caindo há 2 semanas): fins indicados / avisos prematuros | 54% / 3,1 | 60% / 3,9 |

  Entre parênteses, os intervalos de confiança de 95% por bootstrap sobre municípios (`src/experimento_niveis_robustez.py`, `reports/niveis_robustez.csv`). As diferenças do modelo para a regra simples são significativas na validação cruzada (epidemias avisadas: +7 pontos, de 2 a 12; alarmes corretos: +16 pontos; alarmes falsos: −0,33 por ano); nos 15 municípios de validação, o modelo empata em epidemias avisadas e é melhor em alarmes corretos e falsos.
  | Nível previsto: mudanças de nível acertadas com 4 semanas (a persistência nunca acerta) | 41% | 46% |

  O modelo avisa mais epidemias que a regra simples, com bem menos alarmes falsos, e o resultado se mantém nos municípios que ele nunca viu. A persistência (o nível de hoje continua) acerta muito semana a semana, porque os níveis mudam pouco, mas nunca antecipa uma epidemia; o valor do modelo está nas mudanças de nível e no alerta.
* **Sem a previsão de 1 semana:** os níveis são previstos com 2, 3 e 4 semanas de antecedência, e o alerta usa só essas três. A previsão de 1 semana é quase uma cópia do nível atual (ganho de 0,7 ponto sobre a persistência, contra 3,3 com 4 semanas) e dá pouco tempo para mobilizar; o nível atual já cumpre esse papel. Sem ela, o alerta ficou praticamente igual (74% das epidemias avisadas, 52% de alarmes corretos, 0,49 alarme falso por ano, contra 74%, 52% e 0,50 com ela) e a antecedência mediana passou de 2 para 3 semanas. O modelo de tendência e o painel atual (decisões 11 e 13) continuam com 1 a 4 semanas.
* **Desmobilização** (manter e desmobilizar): o modelo indica o fim da epidemia quando o nível mais provável em S+2 deixa de ser vermelho, numa semana em que o município está no vermelho. Ele indicou 79% dos fins nas 2 semanas anteriores à saída do vermelho, com 1 aviso prematuro por epidemia (uma semana em que indicou o fim antes da hora); a regra de queda indica 54%, com 3 avisos prematuros.
* **Dados atrasados** (`src/experimento_niveis_robustez.py`): em tempo real, a última semana ainda sobe cerca de 45% nos 12 dias seguintes, a de 2 semanas antes, 8%, e a de 4 semanas antes, 3% (`reports/revisao_dados.csv`). Como na decisão 12, a simulação descarta as últimas 2 semanas (cenário realista) ou 4 (pior caso), inclusive para saber o nível atual. Como o gestor só saberia do início da epidemia quando os dados o mostrassem, um alarme também conta como correto se o vermelho começou nas semanas que os dados ainda não mostravam.

  | Validação cruzada | Sem atraso | Atraso de 2 semanas | Atraso de 4 semanas |
  |---|---|---|---|
  | Alerta: epidemias avisadas antes de começar (regra simples) | 74% (68%) | 57% (36%) | 40% (22%) |
  | Alerta: avisadas antes de os dados mostrarem o início | 74% | 80% | 76% |
  | Alerta: alarmes corretos / falsos por município por ano | 52% / 0,49 | 52% / 0,60 | 54% / 0,59 |
  | Desmobilização: fins indicados nas 2 semanas antes / antes de os dados mostrarem | 79% / 79% | 72% / 90% | 69% / 94% |
  | Nível previsto com 4 semanas: modelo / persistência | 79% / 76% | 75% / 70% | 71% / 65% |

  Com atraso, todos perdem antecedência, mas o modelo perde menos que a regra simples e que a persistência, e a sua vantagem cresce (de +3,4 para +5,7 pontos no nível com 4 semanas). A credibilidade do alerta se mantém (cerca de 1 alarme correto para cada falso). Em 76% a 80% das epidemias, o alerta chega antes de os dados mostrarem o início; em 90% a 94% dos fins, o modelo indica a saída antes de os dados a mostrarem. Nos 15 municípios de validação, o resultado é parecido (62% e 57% das epidemias avisadas antes de começar, com atraso de 2 e 4 semanas).
* **Alertas por antecedência** (`reports/niveis_alertas_antecedencia.csv`): de cada previsão que acendeu o alerta, de 53% a 55% das semanas previstas foram vermelhas, de 43% a 46% amarelas e de 1% a 2% verdes, nas três antecedências. O alarme falso quase sempre cai num amarelo, não numa semana normal.
* **Limitações:** avaliação pseudoprospectiva (dados já revisados; em tempo real as semanas recentes estão incompletas, decisões 3 e 12); o atraso dos dados é simulado descartando semanas, já que não há fotos dos dados de cada semana do passado; as escolhas que o MEM e o InfoDengue deixam em aberto (mínimos de casos, população fixa do Censo 2022) estão registradas em `src/estados.py`.
* **Limitação: municípios onde a dengue chegou ou mudou de patamar.** Como os limiares vêm do histórico do próprio município, quem tinha pouca dengue fica vermelho por muito tempo quando ela chega, até as novas temporadas entrarem no cálculo. De 2015 em diante, 8 dos 115 municípios ficaram um ano ou mais seguidos no vermelho: Blumenau, Florianópolis e Joinville (SC), com a chegada da dengue ao estado (de 2,7 a 3,5 anos; em Joinville, o limiar epidêmico só alcançou o novo patamar depois de 3 a 4 temporadas, indo de 10 para 2.801 casos por semana); Macapá, Altamira, Cosmópolis e Rio das Ostras, que passaram a ter de 5 a 10 vezes mais casos (de 1,3 a 1,8 ano); e Sinop, com uma temporada de fato longa em 2024. Nesses períodos, o vermelho indica "acima de tudo o que o município já viveu", mas não distingue "entrar em epidemia" de "continuar nela", e o alerta de entrada perde o sentido. No Rio Grande do Sul, onde a dengue também chegou, o inverno interrompe a transmissão e os episódios se encerram a cada ano. O comportamento é o esperado de qualquer limiar baseado no histórico (o MEM, os percentis e o canal endêmico) e se corrige em 1 a 4 temporadas; o grupo decidiu registrá-lo, sem mudar o método, e discutir na apresentação do painel uma mensagem de "transmissão sustentada" para esses casos.
* **Em andamento:** o painel ainda mostra a tendência (decisões 11 e 13); a troca pelos níveis e pelo alerta será feita depois de definidos o que ele mostra, se haverá alerta de amarelo e se o número de casos (modelo por quantis) continua. Tabelas e gráficos de cada etapa: seção 22 de [`docs/historia_decisoes.md`](docs/historia_decisoes.md).

### 17. Painel estático: último nível confirmado e próximas semanas

* **Por que estático:** o painel só mostra resultados pré-calculados, então não precisa de servidor de aplicação. Um JSON por município (cerca de 85 KB, 20 KB comprimido), um índice e a avaliação geral são gerados por `src/exportar_painel.py` e servidos como arquivos; o site (`web/`, TypeScript, Vite e Observable Plot) carrega só o município escolhido. A versão dos dados vai no endereço dos arquivos, para o navegador não reaproveitar dados antigos.
* **Último nível confirmado:** as 2 semanas mais recentes ainda estão incompletas (decisão 3), então o painel parte da semana atual menos 2, como no cenário de 2 semanas de atraso da decisão 16. As duas semanas incompletas aparecem à parte, no card "Casos notificados até o momento", com a estimativa do InfoDengue que corrige o atraso das notificações (o *nowcast*) e o aviso de que o número provavelmente está subnotificado.
* **Próximas semanas:** a partir da semana confirmada, o nível mais provável, a chance de nível epidêmico e os casos aproximados (mediana e faixa de 80%) da semana atual e das 4 seguintes, ou seja, de 2 a 6 semanas à frente da semana confirmada. Os modelos de produção são treinados com os 100 municípios de treino, como em `src/train.py`.
* **Alerta e desmobilização:** se o nível confirmado não é vermelho, o alerta acende quando a chance de nível epidêmico de 2 a 4 semanas à frente passa do corte mais recente escolhido com 2 semanas de atraso (`reports/niveis_robustez_cortes.csv`; 37% no 3º trimestre de 2026). Se é vermelho, o painel indica o fim quando o nível mais provável 2 semanas à frente deixa de ser vermelho. O card mostra a confiança medida nos testes ("cerca de 1 em cada 2 alertas se confirma"), lida da avaliação, e não escrita à mão.
* **Limiares em número de casos:** os da temporada atual e, quando as semanas previstas entram na temporada seguinte (semana 41), os da próxima.
* **Casos aproximados com 2 semanas de atraso** (`src/experimento_casos_atraso.py`, `reports/casos_atraso.csv`; validação cruzada, 2019 em diante):

  | Previsão feita | Erro / erro de repetir os casos confirmados | Casos dentro da faixa de 80% | Nos 15 municípios de validação |
  |---|---|---|---|
  | Na própria semana | 0,75 (0,72 a 0,79) | 79% | 0,71; 82% |
  | 2 semanas antes | 0,70 (0,67 a 0,74) | 78% | 0,66; 81% |
  | 4 semanas antes | 0,69 (0,67 a 0,72) | 78% | 0,62; 82% |

  O modelo erra de 25% a 31% menos que repetir os casos da última semana confirmada, e a faixa de 80% contém o valor real em 78% a 82% das semanas.
* **Avaliação no painel:** quadradinhos e casos previstos de cada município, feitos como o painel os faria (2 semanas de atraso, modelos que não viram o município), e as tabelas gerais de mobilização, desmobilização, nível, casos e efeito do atraso, com intervalos de confiança. O acerto de cada município é calculado no navegador a partir das previsões exportadas.
* **Em aberto:** a seção Ajuda, que depende das definições restantes. O painel anterior, em Streamlit, foi removido (decisão 13).

### Nota sobre os municípios de validação

Todas as escolhas (tipo de modelo, alvo, variáveis, hiperparâmetros, `SEMANAS_INSTAVEIS`) foram feitas com base nos **municípios de treino**. Os 15 municípios de validação só medem a generalização e nunca foram usados como critério de escolha.
