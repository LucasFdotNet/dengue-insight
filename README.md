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

   Opcional: `python -m src.experimento_atraso` roda o experimento de dados atrasados (decisão 10).

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

* **Decisão:** substituir o clima do InfoDengue pela reanálise **ERA5** (Copernicus/ECMWF), obtida pela [Open-Meteo Historical API](https://open-meteo.com/en/docs/historical-weather-api) com `models=era5`, a partir da latitude e longitude de cada município. O `Rt` do InfoDengue continua disponível no painel, mas não entra no modelo (decisão 12).
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

* **Variáveis usadas pelo modelo:** casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás e semana do ano (sazonalidade). O `Rt` fazia parte da primeira versão e foi retirado (decisão 12). A variável `p_inc100k` (incidência por 100 mil habitantes) foi retirada porque é apenas `casos / população`, redundante com os casos.
* **Hiperparâmetros:** fixos (300 árvores, taxa de aprendizado 0,05), sem ajuste fino. Testamos 150 e 600 árvores e a diferença foi desprezível.

### 6. Validação *walk-forward* com retreino mensal e baseline

* **Decisão:** simular o uso real do modelo desde 2015. No início de cada mês, um modelo é treinado **só com o que já era conhecido até ali** e usado para prever as semanas daquele mês; no mês seguinte, é retreinado com os dados novos. São 141 retreinos por horizonte (jan/2015 a set/2026).
* **Por que retreino mensal:** é como o modelo seria usado na prática, retreinado periodicamente com os dados mais recentes. Uma primeira versão retreinava uma vez por ano, o que deixava a simulação um pouco pessimista: o modelo de dezembro não conhecia nada do próprio ano. Com o retreino mensal, o erro caiu levemente (por exemplo, de 0,98 para 0,94 em H+1 nos municípios de validação).
* **Cuidado com o futuro:** para prever H semanas à frente, o treino só usa exemplos cujo resultado (H semanas depois) já era conhecido antes do início do mês. Nenhuma informação do período previsto entra no modelo que o previu.
* **Por que não o corte único 80/20:** um único corte testava apenas um período (de 2023 em diante), dominado pela epidemia de 2024, e o resultado dependia muito de onde caía o corte. Com a validação *walk-forward*, todos os anos desde 2015 são testados.
* **Baseline de persistência:** a referência de comparação é a previsão mais simples possível, "daqui a H semanas haverá o mesmo número de casos de hoje". Um modelo só é útil se errar menos que isso.
* **Pandemia (2020–2021):** testamos treinar o modelo sem esses dois anos (teste exploratório, com retreino anual). O resultado praticamente não mudou (razão de 0,86 a 0,74 sem a pandemia, contra 0,87 a 0,72 com ela), então mantivemos todos os anos. Na avaliação, 2020 foi um ano em que o modelo empatou com o baseline (razão de 1,03 a 1,11).
* **Anos em que o modelo perde para o baseline:** 2016 a 2018, 2020 e 2026. São anos de transmissão baixa ou estável, em que repetir o valor atual é difícil de superar e o modelo às vezes antecipa mudanças que não acontecem (por exemplo, a subida típica do verão). 2017 é o caso mais claro: poucos casos após as grandes epidemias de 2015–2016. Em 2016–2018 o treino também ainda tinha poucos anos de histórico. Nos anos com epidemias ou quedas fortes (2019, 2021 a 2025), o modelo erra de 12% a 44% menos que o baseline nos municípios de treino.
* **Relatórios gerados** em `reports/`: `metricas_gerais.csv` (por grupo e horizonte), `metricas_por_ano.csv` (por ano da semana prevista, com 2024 separado), `metricas_modelos.csv` (por município, permitindo ver Cosmópolis à parte) e `previsoes_walkforward.csv` (todas as previsões semana a semana, usadas pelo dashboard).
* **Resultado atual** (razão modelo/baseline; abaixo de 1, o modelo é melhor):

  | Grupo | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | Municípios de treino (13) | 0,86 | 0,79 | 0,75 | 0,74 |
  | Municípios de validação espacial (6) | 0,95 | 0,86 | 0,84 | 0,83 |

  O modelo é mais útil nos horizontes mais longos. Para a semana seguinte (H+1), a vantagem é pequena, principalmente nos municípios de validação. São José do Rio Preto (o município mais quente e mais distante do perfil de treino) e Ribeirão Preto são os únicos em que o modelo praticamente empata com o baseline.
* **Limitação: dados revisados.** A simulação usa os casos na versão revisada de hoje. Em tempo real, os casos das semanas mais recentes ainda estariam incompletos, porque as notificações chegam com atraso. Por isso a simulação é **otimista** nesse ponto: em uso real, o modelo erraria mais. Não é possível corrigir isso para o passado, porque o InfoDengue não disponibiliza os dados como eram conhecidos em cada data (essa avaliação é chamada de pseudoprospectiva). A decisão 10 mede o tamanho desse efeito com uma simulação de pior caso.

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

* **Novo teste sem o Rt:** como o Rt poderia estar "cobrindo" parte do efeito do clima, repetimos o teste depois de retirar o Rt do modelo (decisão 12), já com a validação final (retreino mensal). O clima voltou a piorar a previsão em todas as combinações e horizontes.
* **Teste com o clima de semanas específicas:** o ciclo de ovo a mosquito adulto leva de 7 a 10 dias e depende do clima, então testamos também o clima semana a semana, sem agregar, nas semanas anteriores à semana atual S (o clima de S ainda não está disponível no momento da previsão). Cada combinação foi testada com todas as variáveis (temperatura mínima, média e máxima, chuva e umidade) e com um conjunto essencial (temperatura média, chuva e umidade). Script: `src/experimento_clima_semanal.py`; saída: `reports/experimento_clima_semanal.csv`. Razão modelo/baseline nos municípios de treino (menor é melhor):

  | Clima usado | H+1 | H+2 | H+3 | H+4 |
  |---|---|---|---|---|
  | **Sem clima (adotado)** | **0,865** | **0,787** | **0,754** | **0,739** |
  | S-1 e S-2 (essencial) | 0,915 | 0,818 | 0,790 | 0,781 |
  | S-1 e S-3 (essencial) | 0,933 | 0,842 | 0,801 | 0,751 |
  | S-1, S-2 e S-3 (essencial) | 0,930 | 0,837 | 0,805 | 0,772 |
  | S-1 e S-2 (completo) | 0,932 | 0,832 | 0,811 | 0,783 |
  | S-1 e S-3 (completo) | 0,942 | 0,835 | 0,822 | 0,785 |
  | S-1, S-2 e S-3 (completo) | 0,945 | 0,818 | 0,808 | 0,801 |

  Todas as combinações pioraram a previsão, nos municípios de treino e nos de validação. O acerto de tendência ficou igual ou um pouco pior (com 4 semanas de antecedência: de 65,8% a 67,3%, contra 67,3% sem clima; nos municípios de validação, de 56% a 57%, contra 59%).
* **Interpretação:** o clima influencia a dengue, mas com semanas de atraso, e esse efeito já está refletido na tendência recente dos casos, que o modelo usa. A semana do ano já captura a sazonalidade. Para horizontes curtos (1 a 4 semanas), o clima acrescentou mais ruído do que informação. Além disso, os municípios de treino são vizinhos e têm clima muito parecido (vários caem no mesmo ponto da grade do ERA5), o que limita o que o modelo pode aprender com ele.
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

### 9. Dashboard: granularidade semanal e previsões passadas

* **Granularidade semanal:** todos os dados, previsões e gráficos são por **semana epidemiológica** (domingo a sábado). É a unidade em que o InfoDengue publica os casos e em que a vigilância epidemiológica trabalha. Agregar por mês esconderia a velocidade de crescimento de um surto, que é justamente o que o modelo usa para prever. Os rótulos dos eixos mostram meses apenas para facilitar a leitura; cada ponto é uma semana.
* **Previsões passadas no gráfico de projeções:** o gráfico mostra os casos reais, as previsões que o modelo teria feito na época e o baseline, com um seletor de antecedência (1 a 4 semanas) e um seletor de período: últimos 12 meses (padrão), um ano específico de 2015 em diante ou todo o período avaliado. Abaixo, informa o erro médio do modelo e do baseline no período exibido. A previsão das próximas semanas só aparece quando o período inclui a semana atual.
* **Cuidado metodológico:** as previsões passadas **não** são geradas com o modelo de produção. Ele foi treinado com toda a série e já "viu" essas semanas, então pareceria melhor do que é. Elas vêm da validação *walk-forward* com retreino mensal (decisão 6): cada semana foi prevista por um modelo treinado só com o que era conhecido no início do mês dela. O `train.py` salva essas previsões em `reports/previsoes_walkforward.csv`. Como na decisão 6, elas usam os dados já revisados, e o próprio painel avisa isso.
* **Semanas sem previsão passada:** as 10 semanas mais recentes (decisão 3) não têm previsão passada, porque os casos delas ainda estão sendo revisados e não servem de referência para medir erro.
* **Filtro por tipo de município:** o painel permite filtrar os municípios por papel (treino ou validação espacial), e o tipo aparece ao lado do nome de cada um.

### 10. Experimento: previsão com dados atrasados

* **Pergunta:** a decisão 6 usa os dados já revisados. Quanto pior o modelo seria se os dados recentes não estivessem disponíveis, como acontece em tempo real?
* **Simulação (pior caso):** na semana X, consideramos que as semanas X, X-1, X-2 e X-3 não são confiáveis e não podem ser usadas. O último dado disponível é o da semana X-4. Para prever X+N, o modelo precisa então olhar N+4 semanas à frente a partir de X-4. O baseline, da mesma forma, repete o último valor confiável (X-4). Rodamos também com lacuna de 5 semanas (último dado em X-5). Todo o resto é igual à decisão 6 (retreino mensal, mesmas semanas-alvo em todos os cenários).
* **Por que é pior caso:** na prática, o InfoDengue fornece uma estimativa (*nowcast*) para as semanas recentes. Ela é incerta, mas não inexistente, então o desempenho real deve ficar entre o cenário sem lacuna e o cenário com lacuna.
* **Código e resultados:** `src/experimento_atraso.py`, com saída em `reports/experimento_atraso.csv`.
* **Resultado nos municípios de treino** (erro médio em casos por semana):

  | Antecedência | Modelo sem lacuna | Modelo com lacuna de 4 semanas | Baseline com lacuna de 4 semanas | Razão modelo/baseline com lacuna |
  |---|---|---|---|---|
  | 1 semana | 26 | 76 (2,9×) | 106 | 0,72 |
  | 2 semanas | 39 | 86 (2,2×) | 123 | 0,70 |
  | 3 semanas | 52 | 96 (1,8×) | 139 | 0,69 |
  | 4 semanas | 65 | 104 (1,6×) | 153 | 0,68 |

  Nos municípios de validação, o padrão é o mesmo: o erro do modelo cresce de 1,6 a 3,1 vezes, e a razão modelo/baseline fica entre 0,77 e 0,79. Com lacuna de 5 semanas, os erros crescem um pouco mais (de 1,7 a 3,6 vezes), com as mesmas conclusões.
* **Conclusões:**
  * **O atraso dos dados custa caro:** sem as 4 semanas mais recentes, o erro do modelo aumenta de 1,6 a 3,1 vezes. O efeito é maior nas antecedências curtas, porque prever "a semana que vem" sem saber o que aconteceu nas últimas 4 semanas é, na prática, prever 5 semanas à frente.
  * **O modelo continua útil, e sua vantagem aumenta:** com dados atrasados, repetir o último valor conhecido fica muito pior, e o modelo passa a errar de 21% a 32% menos que o baseline (contra 5% a 26% sem lacuna). Quanto mais incerta a situação, mais vale ter um modelo que antecipa a tendência.
  * **Para o uso real:** as previsões do painel devem ser lidas como estimativas de tendência (subida ou queda), com margem de erro maior nas semanas mais próximas do que a validação da decisão 6 sugere.

### 11. Avaliação da tendência (sobe, estável ou cai)

* **Pergunta:** mesmo errando o número exato de casos, o modelo acerta **a tendência**, isto é, se os casos vão subir, ficar estáveis ou cair nas próximas 1 a 4 semanas? Para a vigilância, essa é muitas vezes a pergunta mais útil.
* **Definição:** comparando o valor previsto (ou o real) com o da semana de partida, a semana é classificada como **subida** ou **queda** quando a variação passa de **20% e de 5 casos**; caso contrário, **estável**. O mínimo de 5 casos evita que oscilações pequenas (por exemplo, de 2 para 3 casos, +50%) contem como subida em municípios com poucos casos. Os valores ficam em `LIMIAR_TENDENCIA` e `MIN_CASOS_TENDENCIA`, em `src/train.py`.
* **Referências de comparação:**
  * **"Sempre estável":** equivale ao baseline de persistência, que sempre diz que nada vai mudar;
  * **"Tendência da última semana":** estende por H semanas a variação observada na última semana (se subiu 10%, continua subindo 10% por semana).
* **Resultado nos municípios de treino** (validação *walk-forward* com retreino mensal, 2015 a 2026; arquivo `reports/metricas_tendencia.csv`):

  | Antecedência | Modelo acerta a tendência | "Sempre estável" acerta | "Tendência da última semana" acerta | Subidas detectadas | Alarmes de subida corretos | Sentido oposto |
  |---|---|---|---|---|---|---|
  | 1 semana | 66% | 65% | 56% | 20% | 49% | 1% |
  | 2 semanas | 65% | 54% | 49% | 44% | 60% | 3% |
  | 3 semanas | 67% | 48% | 48% | 51% | 64% | 4% |
  | 4 semanas | **67%** | **44%** | **49%** | **55%** | **66%** | 5% |

  Nos municípios de validação espacial, o padrão se repete: com 4 semanas de antecedência, o modelo acerta 59% das tendências, contra 34% do "sempre estável", detecta 52% das subidas e acerta 65% dos alarmes de subida. A decisão 12 compara esses resultados com a sinalização de tendência do próprio InfoDengue.
* **Como ler:**
  * **Subidas detectadas:** das semanas em que os casos realmente subiram, em quantas o modelo previu subida.
  * **Alarmes de subida corretos:** das vezes em que o modelo previu subida, em quantas os casos realmente subiram.
  * **Sentido oposto:** semanas em que o modelo previu subida e os casos caíram, ou o contrário.
* **Conclusões:**
  * **Para 1 semana, o modelo não acrescenta:** acerta a tendência tanto quanto dizer "vai ficar igual", porque em uma semana os casos raramente mudam mais de 20%.
  * **De 2 a 4 semanas, o modelo é claramente melhor:** acerta de 11 a 24 pontos percentuais a mais que "sempre estável" e detecta cerca de metade das subidas, com cerca de 2 em cada 3 alarmes corretos.
  * **O modelo quase nunca erra o sentido:** em no máximo 5% das semanas (7% nos municípios de validação) ele aponta subida quando os casos caem, ou o contrário. Quase todos os seus erros são de intensidade, ao prever "estável" quando houve movimento.
* **No dashboard:** as previsões das próximas semanas mostram a variação e a tendência (subida, estável ou queda), e abaixo do gráfico de projeções há um bloco de acerto de tendência para o município, o período e a antecedência escolhidos, com a tabela "o que aconteceu" × "o que o modelo previu".

### 12. Rt fora do modelo e comparação com a sinalização do InfoDengue

* **Decisão:** retirar o `Rt` do modelo. O modelo passa a usar apenas os casos (nowcast do InfoDengue) e a semana do ano.
* **Motivos:**
  * **Coerência com a proposta:** o modelo deve se basear nos casos. O `Rt` não é uma previsão (é uma estimativa da transmissão atual), mas é o resultado de outro modelo, do InfoDengue, com premissas que não controlamos e que podem mudar. O nowcast é diferente: estima uma quantidade observável, os casos, que é a matéria-prima do modelo.
  * **Redundância:** o `Rt` mede, de forma elaborada, se os casos estão crescendo. O modelo já recebe isso diretamente, pelas variações em relação a 1 a 4 semanas atrás.
  * **Comparação independente:** sem o `Rt` dentro do modelo, podemos comparar o modelo com a sinalização de tendência do próprio InfoDengue como duas abordagens independentes.
* **Teste** (`src/experimento_variaveis.py`, saída em `reports/experimento_variaveis.csv`; validação *walk-forward* com retreino mensal, municípios de treino). Razão modelo/baseline, em que menor é melhor, e acerto de tendência com 4 semanas de antecedência:

  | Configuração | H+1 | H+2 | H+3 | H+4 | Acerto de tendência (H+4) |
  |---|---|---|---|---|---|
  | A. Com Rt, sem clima (modelo anterior) | 0,855 | 0,787 | 0,756 | 0,735 | 67,5% |
  | **B. Sem Rt, sem clima (adotado)** | **0,865** | **0,787** | **0,754** | **0,739** | **67,3%** |
  | C. Sem Rt + chuva e temperatura de 8 semanas | 0,898 | 0,834 | 0,802 | 0,780 | 66,3% |
  | D. Sem Rt + chuva, temperatura e umidade (5 variáveis) | 0,951 | 0,890 | 0,845 | 0,805 | 65,8% |
  | E. Sem Rt + chuva de 4 e 12 semanas e temperatura de 8 semanas | 0,897 | 0,881 | 0,836 | 0,797 | 65,9% |

  * **Retirar o Rt praticamente não muda o resultado:** diferença de no máximo 0,01 na razão de erro, e o mesmo acerto de tendência. Isso confirma que o Rt era redundante com as variações de casos.
  * **O clima continua piorando a previsão**, mesmo sem o Rt (decisão 7). Por isso o modelo adotado é o B, sem Rt e sem clima.
* **Comparação com a sinalização do InfoDengue:** o InfoDengue publica o `Rt` e o `p_rt1` (probabilidade de o Rt ser maior que 1), que já indicam se a epidemia está crescendo. Transformamos esses indicadores em regras de tendência, aplicadas à semana de partida:
  * **`p_rt1`:** acima de 0,9 → sobe; abaixo de 0,1 → cai; senão, estável;
  * **`Rt`:** acima de 1,1 → sobe; abaixo de 0,9 → cai; senão, estável.

  Resultado nos municípios de treino, com a mesma definição de tendência da decisão 11:

  | Antecedência | Modelo | Regra `p_rt1` | Regra `Rt` | "Sempre estável" | Alarmes corretos: modelo | Alarmes corretos: `p_rt1` | Sentido oposto: modelo | Sentido oposto: `p_rt1` |
  |---|---|---|---|---|---|---|---|---|
  | 1 semana | 66% | 48% | 28% | 65% | 49% | 29% | 1% | 7% |
  | 2 semanas | 65% | 50% | 33% | 54% | 60% | 42% | 3% | 8% |
  | 3 semanas | 67% | 51% | 36% | 48% | 64% | 47% | 4% | 9% |
  | 4 semanas | 67% | 50% | 37% | 44% | 66% | 50% | 5% | 10% |

  Nos municípios de validação, o padrão é o mesmo: com 4 semanas de antecedência, o modelo acerta 59% das tendências, contra 50% da regra `p_rt1` e 45% da regra `Rt`.
* **Conclusões:**
  * **O modelo acrescenta valor em relação à sinalização do InfoDengue:** acerta de 15 a 18 pontos percentuais a mais que a regra `p_rt1`, seus alarmes de subida são mais confiáveis e ele erra o sentido da tendência com metade ou menos da frequência.
  * **As regras baseadas no Rt dão muitos alarmes falsos:** a regra `Rt` detecta mais subidas (de 50% a 55%), mas só 22% a 39% dos seus alarmes se confirmam. O Rt mede a transmissão atual, que oscila bastante de uma semana para outra.
  * **Ressalva:** o Rt não foi criado para prever o número de casos daqui a 1 a 4 semanas com o nosso critério de 20%. A comparação mostra que, para essa pergunta específica, o modelo é mais útil que uma leitura direta do Rt, e não que o Rt seja um indicador ruim para o que ele se propõe.

### Nota sobre os testes exploratórios

As tabelas das decisões 5, 7 e 8 vêm de testes exploratórios (ainda com o `Rt` no modelo) feitos com a validação *walk-forward* com retreino **anual**, antes do retreino mensal (decisão 6) e de um ajuste no corte das semanas instáveis (decisão 3). Como todas as alternativas de cada tabela foram avaliadas da mesma forma, as comparações continuam válidas, mas os números podem diferir na segunda casa decimal dos de `reports/` e das tabelas das decisões 6 e 10, que são os resultados finais.

### Nota sobre os municípios de validação

Todas as escolhas acima (tipo de modelo, alvo, variáveis, pandemia, hiperparâmetros) foram feitas com base nos resultados dos **municípios de treino**. Os municípios de validação foram usados para medir a generalização. Nos testes exploratórios, os resultados deles eram exibidos junto com os de treino e sempre apontaram na mesma direção, mas não foram usados como critério de escolha.
