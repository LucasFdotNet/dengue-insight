# 🦟 Dengue Insight: Análise Preditiva para Monitoramento de Surtos de Dengue

Solução analítica e preditiva desenvolvida para o **Projeto Integrador em Computação IV (DRP04)** da **Universidade Virtual do Estado de São Paulo (UNIVESP)**.

---

## 📌 Sobre o Projeto

O **Dengue Insight** integra dados epidemiológicos e ambientais provenientes de fontes públicas para identificar padrões históricos e antecipar tendências de evolução dos casos de dengue com antecedência de 1 a 4 semanas.

O objetivo é fornecer uma ferramenta acessível para suporte à tomada de decisão de órgãos públicos e conhecimento da sociedade, permitindo direcionar ações preventivas e alocação de recursos em localidades vulneráveis.

### Municípios Monitorados

São 19 municípios de SP, configurados em [`src/cidades.py`](src/cidades.py) (critérios em [Decisões de Projeto](#-decisões-de-projeto)).

* **Treino (13):** Campinas, Cosmópolis, Limeira, Piracicaba, Rio Claro, Americana, Sumaré, Hortolândia, Indaiatuba, Santa Bárbara d'Oeste, Paulínia, Valinhos e Araras.
* **Validação espacial (6):** São José do Rio Preto, Ribeirão Preto, Sorocaba, Presidente Prudente, Bauru e Santos.

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

O sistema opera em um pipeline desacoplado em 5 etapas modulares:

1. **Ingestão:**
   * **Casos (`src/ingestion.py`):** Conecta à API pública do InfoDengue (Fiocruz/FGV) via requisições HTTP REST e extrai as séries temporais consolidadas das semanas epidemiológicas.
   * **Clima (`src/ingestion_clima.py`):** Obtém temperatura, precipitação e umidade diárias da reanálise ERA5 pela Open-Meteo e agrega por semana epidemiológica.
2. **Pré-processamento (`src/preprocessing.py`):** Une casos e clima por semana, realiza limpeza, tratamento de valores faltantes por interpolação e gera defasagens temporais (*lag features* de 1 a 4 semanas) e médias móveis.
3. **Treinamento e Validação (`src/train.py`):** Treina um modelo único de Gradient Boosting (**LightGBM**) com todos os municípios de treino, um por horizonte (H+1 a H+4 semanas). Avalia com validação *walk-forward* anual por MAE, RMSE e R², sempre comparando com um baseline de persistência, e salva o modelo de produção usado pelo dashboard.
4. **Análise Exploratória (`src/eda.py`):** Processa dados e gera matrizes de correlação de Pearson e gráficos comparativos de casos versus variáveis climáticas/ambientais.
5. **Dashboard Interativo (`app.py`):** Interface web moderna para visualização em tempo real dos indicadores atuais, curvas históricas e projeções com intervalos das próximas 4 semanas.

---

## 📦 Tecnologias e Pacotes Utilizados

* **Linguagem:** Python 3
* **Manipulação e Engenharia de Dados:** `pandas`, `numpy`
* **Comunicação com API:** `requests`
* **Modelagem e Machine Learning:** `scikit-learn`, `lightgbm`, `joblib`
* **Interface Web e Visualização Interativa:** `streamlit`, `plotly`
* **Visualização Estatística (EDA):** `matplotlib`, `seaborn`

---

## 🚀 Como Executar o Projeto Localmente

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/LucasFdotNet/dengue-insight.git](https://github.com/LucasFdotNet/dengue-insight.git)
   cd dengue-insight
   ```

2. **Opcional: crie e ative o seu ambiente virtual**
   ```bash
   python venv venv
   venv/scripts/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute o pipeline** (a partir da raiz do projeto)
   ```bash
   python -m src.ingestion
   python -m src.ingestion_clima
   python -m src.preprocessing
   python -m src.train
   python -m src.eda
   streamlit run app.py
   ```

---

## 🧭 Decisões de Projeto

Registro das decisões que afetam os dados, o modelo ou a avaliação, com o motivo de cada uma. Quando uma decisão mudar, atualize o item em vez de apagá-lo.

### 1. Municípios e papéis (treino × validação)

* **Decisão:** 19 municípios de SP, configurados em [`src/cidades.py`](src/cidades.py). São 13 de **treino** (os polos UNIVESP dos integrantes e a região entre eles) e 6 de **validação espacial** (outras regiões do estado, com climas contrastantes).
* **Critério de inclusão:** municípios com mais de 100 mil habitantes. A exceção é Cosmópolis, mantida por ser polo de integrante do grupo; suas métricas são reportadas à parte.
* **Regra:** os municípios de validação **nunca** entram no treino, na seleção de features, no ajuste de hiperparâmetros nem na escolha de parâmetros como `SEMANAS_INSTAVEIS`. Eles servem apenas para medir se o modelo generaliza para outras regiões.

### 2. Período dos dados

* **Decisão:** séries semanais de 2010 até o ano corrente.
* **Motivo:** a API do InfoDengue disponibiliza a série desde 2010 para todos os municípios escolhidos. Mais anos significam mais epidemias no treino, o que ajuda o modelo a lidar com picos altos.

### 3. Descarte das semanas finais instáveis

* **Decisão:** as últimas 10 semanas de cada município (`SEMANAS_INSTAVEIS` em `src/train.py`) ficam fora do treino e da avaliação.
* **Motivo:** o número de casos das semanas mais recentes ainda é uma estimativa (*nowcast*): o InfoDengue revisa esses valores à medida que chegam notificações atrasadas. Treinar com eles ensinaria o modelo com números que ainda vão mudar.
* **Como chegamos a 10:** o InfoDengue informa, para cada semana, um intervalo de incerteza do nowcast. Olhando os dados de 09/2026, as cidades de treino tinham de 7 a 10 semanas finais com esse intervalo ainda aberto. **Cosmópolis e Indaiatuba tinham 10**, o maior valor, e adotamos esse máximo. Campinas, Piracicaba e Hortolândia não publicam intervalo, mas a última semana delas também está visivelmente incompleta (em Campinas, 68 casos contra cerca de 130 nas semanas anteriores).
* **Detalhe técnico:** o corte é feito depois de descartar as semanas sem alvo, para que também saiam as semanas cujo alvo (H semanas à frente) cai dentro do período instável. O corte fica no treino, e não no pré-processamento, porque o dashboard precisa mostrar as semanas recentes.

### 4. Fonte dos dados climáticos: Open-Meteo (ERA5)

* **Decisão:** substituir o clima do InfoDengue pela reanálise **ERA5** (Copernicus/ECMWF), obtida pela [Open-Meteo Historical API](https://open-meteo.com/en/docs/historical-weather-api) com `models=era5`, a partir da latitude e longitude de cada município. O `Rt` continua vindo do InfoDengue.
* **Motivo:**
  * o clima do InfoDengue não tem precipitação;
  * de 2010 a 2022 vários municípios compartilham a mesma estação meteorológica (temperatura idêntica em Campinas, Cosmópolis e Piracicaba em 100% das semanas; 47% em 2023 e nenhuma a partir de 2024);
  * a diferença entre a temperatura do InfoDengue e a do ERA5 muda ao longo dos anos (de cerca de −1 °C em 2010–2013 a cerca de +0,9 °C em 2021–2023, em Campinas), o que indica troca de fonte no meio da série.
* **Alternativas descartadas:**
  * **ERA5-Land:** tem resolução melhor (0,1°), mas não fornece precipitação;
  * **Mosqlimate:** agrega o ERA5 por município, mas exige chave de API; fica como opção futura.
* **Limitações conhecidas:**
  * a grade do ERA5 tem 0,25°, então municípios vizinhos caem no mesmo ponto (os 19 municípios ocupam 13 pontos; por exemplo, Cosmópolis, Americana, Sumaré, Hortolândia e Paulínia compartilham o mesmo);
  * os dados chegam com cerca de 6 dias de atraso, então a semana epidemiológica mais recente pode ficar sem clima.
* **Agregação:** dados diários agrupados por semana epidemiológica (domingo a sábado, alinhada a `data_iniSE`).
* **Atribuição:** dados ERA5 de Copernicus Climate Change Service, sob licença CC BY 4.0; acesso via Open-Meteo.
* **Uso:** o clima aparece no dashboard e na análise exploratória, mas **não entra no modelo** de previsão. Ver a decisão 7.

### 5. Modelo único com alvo relativo

* **Decisão:** um único modelo, treinado com os 13 municípios de treino juntos (um modelo para cada horizonte, de 1 a 4 semanas), em vez de um modelo separado por município. O modelo prevê a **variação** dos casos, e não o número de casos.
* **O que é o alvo relativo:** em vez de "quantos casos haverá daqui a H semanas", o modelo responde "quanto os casos vão crescer ou cair em relação a hoje", em escala logarítmica: `log(1 + casos daqui a H semanas) − log(1 + casos hoje)`. O número de casos é reconstruído a partir da previsão. Assim, uma cidade com 20 casos e outra com 2.000 que estejam dobrando têm o mesmo alvo, e o modelo aprende o comportamento da epidemia, não o tamanho da cidade.
* **Motivos:**
  * **Picos maiores que os do passado.** Modelos de árvore, como o LightGBM, não conseguem prever valores acima do maior valor visto no treino. Com o alvo absoluto, isso era grave: em Campinas, o treino chegava a no máximo 7.074 casos semanais e a epidemia de 2024 chegou a 11.789. Prevendo a variação, o modelo pode chegar a valores nunca vistos (por exemplo, "dobrar" a partir de um valor já alto).
  * **Mais epidemias para aprender.** Juntando os 13 municípios, o modelo vê muito mais surtos (inícios, picos e quedas) do que veria em um único município.
  * **Previsão para qualquer município.** Como não depende de um histórico próprio para treinar, o modelo único pode prever os municípios de validação, o que permite testar se ele generaliza para outras regiões. O nome do município não entra como informação no modelo; se entrasse, não seria possível aplicá-lo a municípios novos.
* **Resultado que motivou a escolha** (validação *walk-forward*, 2015 a 2026, municípios de treino; os números são o erro médio do modelo dividido pelo erro médio do baseline, e **abaixo de 1 significa que o modelo erra menos que o baseline**):

  | Abordagem | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | Um modelo por município, alvo absoluto (versão anterior) | 2,07 | 1,40 | 1,16 | 1,00 |
  | Um modelo por município, alvo relativo | 0,89 | 0,83 | 0,76 | 0,76 |
  | **Modelo único, alvo relativo (adotado)** | **0,87** | **0,79** | **0,75** | **0,72** |

* **Variáveis usadas pelo modelo:** casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás, `Rt` da semana anterior e semana do ano (sazonalidade). A variável `p_inc100k` (incidência por 100 mil habitantes) foi retirada porque é apenas `casos / população`, redundante com os casos.
* **Hiperparâmetros:** fixos (300 árvores, taxa de aprendizado 0,05), sem ajuste fino. Testamos 150 e 600 árvores e a diferença foi desprezível.

### 6. Validação *walk-forward* anual e baseline

* **Decisão:** avaliar o modelo ano a ano. Para cada ano de teste, de 2015 em diante, o modelo é treinado **só com as semanas anteriores** a esse ano e testado no ano inteiro. Isso simula o uso real: prever o futuro sabendo apenas o passado.
* **Por que não o corte único 80/20:** um único corte testava apenas um período (de 2023 em diante), dominado pela epidemia de 2024, e o resultado dependia muito de onde caía o corte. Com janelas anuais, cada ano é testado, e cada teste cobre um ano completo, com todas as estações.
* **Baseline de persistência:** a referência de comparação é a previsão mais simples possível, "daqui a H semanas haverá o mesmo número de casos de hoje". Um modelo só é útil se errar menos que isso.
* **Pandemia (2020–2021):** testamos treinar o modelo sem esses dois anos. O resultado praticamente não mudou (razão de 0,86 a 0,74 sem a pandemia, contra 0,87 a 0,72 com ela), então mantivemos todos os anos. Na avaliação, 2020 foi um ano em que o modelo empatou com o baseline (razão de 1,00 a 1,13).
* **Anos em que o modelo perde para o baseline:** 2016 a 2018 e 2020. Em 2016–2018 o treino ainda tinha poucos anos de histórico, e 2017 foi um ano de poucos casos após as grandes epidemias de 2015–2016, quando repetir o valor atual é difícil de superar. 2026 também aparece acima de 1, mas é um ano incompleto (só até meados do ano).
* **Relatórios gerados** em `reports/`: `metricas_gerais.csv` (por grupo e horizonte), `metricas_por_ano.csv` (por ano, com 2024 separado) e `metricas_modelos.csv` (por município, permitindo ver Cosmópolis à parte).
* **Resultado atual** (razão modelo/baseline; abaixo de 1, o modelo é melhor):

  | Grupo | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | Municípios de treino (13) | 0,87 | 0,79 | 0,76 | 0,73 |
  | Municípios de validação espacial (6) | 0,98 | 0,87 | 0,86 | 0,83 |

  O modelo é mais útil nos horizontes mais longos. Para a semana seguinte (H+1), fica próximo do baseline, principalmente nos municípios de validação. São José do Rio Preto, o município mais quente e mais distante do perfil de treino, é o único em que o modelo empata com o baseline.

### 7. Clima fora do modelo de previsão

* **Decisão:** as variáveis climáticas (temperatura, chuva e umidade) **não entram** no modelo. Continuam disponíveis no dashboard e na análise exploratória.
* **Motivo:** na validação *walk-forward*, todas as combinações de clima testadas **pioraram** a previsão nos municípios de treino:

  | Variáveis testadas | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | **Sem clima (adotado)** | **0,87** | **0,79** | **0,75** | **0,72** |
  | Chuva acumulada de 4 e 8 semanas e temperatura média de 8 semanas | 0,90 | 0,83 | 0,80 | 0,76 |
  | Chuva de 4 e 12 semanas e temperatura de 8 semanas | 0,91 | 0,82 | 0,78 | 0,73 |
  | 5 variáveis agregadas de chuva, temperatura e umidade | 0,94 | 0,85 | 0,85 | 0,79 |
  | 22 variáveis (defasagens semanais de 1 a 8 semanas) | 0,94 | 0,82 | 0,83 | 0,77 |

* **Interpretação:** o clima influencia a dengue, mas com semanas de atraso, e esse efeito já está refletido na tendência recente dos casos e no `Rt`, que o modelo usa. A semana do ano já captura a sazonalidade. Para horizontes curtos (1 a 4 semanas), o clima acrescentou mais ruído do que informação. Além disso, os municípios de treino são vizinhos e têm clima muito parecido (vários caem no mesmo ponto da grade do ERA5), o que limita o que o modelo pode aprender com ele.
* **Observação:** um primeiro teste com o corte único 80/20 sugeria que o clima ajudava em H+3 e H+4. A validação *walk-forward* não confirmou isso, o que mostra por que avaliar em vários anos é importante.

### 8. Número de municípios de treino

* **Pergunta:** vale a pena incluir mais municípios no treino?
* **Teste:** treinamos o modelo com 4, 7, 10 e 13 municípios de treino, sorteados, e medimos o resultado nos municípios de validação espacial:

  | Municípios no treino | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | 4 | 1,04 | 0,96 | 0,93 | 0,91 |
  | 7 | 1,00 | 0,92 | 0,87 | 0,86 |
  | 10 | 0,97 | 0,89 | 0,85 | 0,83 |
  | 13 | 0,97 | 0,87 | 0,85 | 0,83 |

* **Conclusão:** mais municípios ajudam, mas o ganho diminui: de 10 para 13 a melhora já é pequena. Incluir mais municípios poderia trazer algum ganho, principalmente se forem de regiões com clima diferente, mas não é prioritário.

### Nota sobre os testes exploratórios

As tabelas das decisões 5, 7 e 8 vêm de testes exploratórios feitos com a mesma validação *walk-forward*, antes de um ajuste no corte das semanas instáveis (decisão 3). Por isso podem diferir na segunda casa decimal dos números de `reports/` e da tabela da decisão 6, que são os resultados finais.

### Nota sobre os municípios de validação

Todas as escolhas acima (tipo de modelo, alvo, variáveis, pandemia, hiperparâmetros) foram feitas com base nos resultados dos **municípios de treino**. Os municípios de validação foram usados para medir a generalização. Nos testes exploratórios, os resultados deles eram exibidos junto com os de treino e sempre apontaram na mesma direção, mas não foram usados como critério de escolha.
