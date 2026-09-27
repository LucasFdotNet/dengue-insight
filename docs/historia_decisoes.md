# História das decisões técnicas do Dengue Insight

Este documento reconstrói, em ordem cronológica, as decisões técnicas tomadas durante a revisão do Dengue Insight: o que motivou cada uma, o que foi testado, o que os números mostraram e quais limitações permanecem. Ele complementa a seção "Decisões de Projeto" do `README.md`, que registra o estado atual de cada decisão; aqui o foco é o caminho percorrido, inclusive as conclusões que foram revistas mais tarde.

**Fontes.** Todos os números vêm do `README.md`, dos arquivos em `reports/`, das mensagens e do conteúdo dos commits (`git log`) e das notas de trabalho em `temp/` (`HANDOFF_dengue_insight.md`, que descreve o diagnóstico do código herdado, e `CONTINUAR.md`, que registra resultados intermediários da base de 74 municípios). Quando um número só existe em uma versão anterior de um arquivo, o commit correspondente é indicado.

**Como ler as métricas.** O texto usa três tipos de número, e cada tabela diz qual está usando:

* **Razão de erro (modelo/baseline)**: o erro absoluto médio do modelo (MAE, a média, em casos por semana, da diferença entre o previsto e o que aconteceu) dividido pelo erro absoluto médio do baseline de persistência (explicado na [seção 5](#s5)). **Quanto menor, melhor; abaixo de 1, o modelo erra menos que o baseline.** 0,75, por exemplo, significa um erro 25% menor.
* **Acerto de tendência (%)**: a fração das semanas em que o modelo acertou se os casos iriam subir, ficar estáveis ou cair ([seção 8](#s8)). **Quanto maior, melhor.** Deve ser comparado com o "sempre estável", que já acerta muito porque a maioria das semanas é estável.
* **Acerto balanceado (de 0 a 1)**: a média do acerto em cada uma das três situações (subiu, ficou estável, caiu), calculada separadamente. **Quanto maior, melhor; o baseline tira 0,333.** Não é uma razão em relação ao baseline. Exemplo de cálculo na [seção 16](#s16).

"H+1" a "H+4" indicam a antecedência da previsão, de 1 a 4 semanas.

---

## Tabela-resumo

| # | Tema | Data (commit) | Decisão tomada | Seção |
|---|---|---|---|---|
| 0 | Ponto de partida | 21/09/2026 (`e2eca7e`, `f91945f`) | Código herdado: 3 municípios, um LightGBM por município, corte 80/20; o modelo perdia para o baseline | [0](#s0) |
| 1 | Correções de base | 26/09/2026 (`0a27913` a `7e59b03`) | Corrigir `rename_map`, remover valores inventados ("falhar cedo"), fixar versões, série desde 2010, 19 municípios de SP com papéis de treino e validação | [1](#s1) |
| 2 | Semanas instáveis do nowcast | 26/09/2026 (`68cd5fe`, `0ed9ee6`) | Descartar as 10 últimas semanas de cada município do treino e da avaliação | [2](#s2) |
| 3 | Fonte do clima | 26/09/2026 (`930a04c`, `126a92e`) | Trocar o clima do InfoDengue pela reanálise ERA5, via Open-Meteo | [3](#s3) |
| 4 | Modelo único com alvo relativo | 26/09/2026 (`16dedbf`) | Um LightGBM por horizonte para todos os municípios, prevendo a variação dos casos | [4](#s4) |
| 5 | Validação walk-forward e baseline | 26/09/2026 (`16dedbf`, `c9162b0`) | Avaliar de 2015 em diante, primeiro com retreino anual e depois mensal, sempre contra a persistência | [5](#s5) |
| 6 | Painel: previsões passadas | 26/09/2026 (`dd7be2e`, `06dc4a8`, `1d3eb26`) | Mostrar previsões passadas da validação, nunca do modelo de produção; granularidade semanal | [6](#s6) |
| 7 | Dados atrasados | 26/09/2026 (`8683028`) | Medir o custo de não ter as 4 ou 5 semanas mais recentes; o modelo continua melhor que o baseline | [7](#s7) |
| 8 | Foco na tendência | 26/09/2026 (`8b0b994`, `d0ebb23`) | Avaliar se o modelo acerta "sobe, estável ou cai" (limiar de 20% e 5 casos) | [8](#s8) |
| 9 | Retirada do Rt | 26/09/2026 (`9fa0016`, `ecfb204`) | Tirar o Rt do modelo; comparar o modelo com a sinalização do InfoDengue | [9](#s9) |
| 10 | Clima no modelo (base de SP) | 26/09/2026 (`16dedbf`, `ecfb204`, `51ef662`) | Clima fora do modelo: todas as combinações pioraram a previsão | [10](#s10) |
| 11 | Robustez da ingestão | 26/09/2026 (`1941b65`) | Novas tentativas automáticas, respeito aos limites da Open-Meteo, clima incremental | [11](#s11) |
| 12 | Base nacional (74 municípios) | 26/09/2026 (`f018e11`, `b1e6925`, `179dd03`) | Incluir capitais e segundas cidades; o treino nacional melhorou a previsão de SP | [12](#s12) |
| 13 | Base de 115 municípios | 26/09/2026 (`496bf00`, `5d4fed5`, `26cbcfa`) | Lista em `data/config/cidades.csv`; 37 municípios com histórico de surtos; 15 de validação | [13](#s13) |
| 14 | Generalização para municípios não vistos | 26/09/2026 (`4965f7a`) | Validação cruzada por município com bootstrap e curva de aprendizado; clima ajuda só em 4 semanas; mais municípios quase não ajudam | [14](#s14) |
| 15 | Como as conclusões mudaram | | Síntese das decisões revistas | [15](#s15) |
| 16 | Comparação de modelos | 27/09/2026 | 8 modelos comparados na tendência; o classificador é o melhor no acerto balanceado e o modelo por quantis no número de casos; escolha final em aberto | [16](#s16) |
| 17 | Modelo contra o Rt | 27/09/2026 | O classificador supera a regra do Rt, a do `p_rt1` e um classificador treinado só com o Rt; o Rt segue fora dos modelos | [17](#s17) |

Observação sobre as datas: o código herdado é de 21/09/2026 e quase todo o trabalho de revisão foi registrado em commits de 26/09/2026 (o último, que fixa versões do `scipy` e do `statsmodels`, é de 27/09/2026). A coluna de commits permite reconstruir a ordem exata com `git log --reverse`.

---

<a id="s0"></a>
## 0. Ponto de partida: o código herdado

**Contexto.** O protótipo inicial (commits `e2eca7e` e `f91945f`, 21/09/2026) baixava do InfoDengue os casos de 2018 a 2024 de três municípios (Campinas, Cosmópolis e Piracicaba), treinava um LightGBM separado para cada município e cada horizonte e avaliava com um único **corte 80/20**: os primeiros 80% das semanas para treino e os últimos 20% para teste. As variáveis eram os casos das 4 semanas anteriores, a média móvel de 4 semanas, a temperatura mínima (`tmin_lag_1`, `tmin_roll_4`), o Rt da semana anterior (`rt_lag_1`) e a incidência por 100 mil habitantes (`p_inc100k`).

O **LightGBM** é um algoritmo de *gradient boosting*: combina centenas de árvores de decisão pequenas, cada uma corrigindo os erros das anteriores. O **Rt** (número de reprodução) é uma estimativa, publicada pelo InfoDengue, de quantas pessoas cada caso infecta; acima de 1, a transmissão está crescendo.

**Problemas encontrados** (diagnóstico em `temp/HANDOFF_dengue_insight.md`):

* **Nomes de colunas errados.** A API do InfoDengue devolve `tempmin` e `Rt`, mas o código esperava `temp_min` e `rt`. Como faltava a coluna, o pré-processamento preenchia valores fixos: a temperatura mínima virava a constante 22,0 e o Rt a constante 1,0 em todas as semanas. Na prática, o modelo não usava nem clima nem Rt.
* **Valores inventados quando faltava dado.** Esses preenchimentos (*fallbacks*) aconteciam em silêncio, sem nenhum aviso.
* **Nomes de municípios com "_".** O nome era extraído do arquivo com `split('_')[0]`, o que transformava `rio_claro` em `rio`. O erro aparecia em `preprocessing.py`, `train.py` e `eda.py`.
* **`p_inc100k` redundante.** É apenas casos divididos pela população, com correlação 1,0 com os casos.
* **Modelo salvo incompleto.** O arquivo usado pelo painel era o modelo treinado só com os 80% iniciais e nunca tinha visto 2024.

**Resultado.** O modelo perdia para o baseline de persistência (repetir o valor atual) em todos os municípios e horizontes (`reports/metricas_modelos.csv` no commit `530e998`):

| Município | Horizonte | MAE do baseline | MAE do LightGBM | R² do LightGBM |
|---|---|---|---|---|
| Campinas | H+1 | 426,12 | 1.657,72 | 0,08 |
| Campinas | H+4 | 1.227,86 | 1.912,99 | −0,10 |
| Piracicaba | H+1 | 153,78 | 605,53 | 0,13 |
| Cosmópolis | H+1 | 15,50 | 67,72 | −0,28 |

(O R² mede quanto da variação dos casos o modelo explica; 1 é perfeito e valores negativos indicam desempenho pior que prever sempre a média.)

**Causa principal.** O corte 80/20 separava as fases da série: treino de jan/2018 a jul/2023 e teste de ago/2023 a dez/2024, período que inclui a epidemia de 2024. Em Campinas, o máximo semanal no treino era 2.905 casos, o máximo no teste foi 11.789, e 19 das 72 semanas de teste superaram qualquer valor visto no treino. A maior previsão do modelo foi 1.822. Isso é estrutural: modelos de árvore não conseguem prever valores acima dos que viram no treino (ver [seção 4](#s4)). Corrigir a temperatura e o Rt quase não mudou o resultado (MAE de Campinas em H+1 de 1.658 para 1.648).

**Limitação do diagnóstico.** Estes números vêm de um único corte e de um único período de teste. Servem para mostrar que o problema existia, mas não para quantificar o desempenho do modelo em geral, o que motivou a mudança de validação ([seção 5](#s5)).

---

<a id="s1"></a>
## 1. Correções de base

**Contexto.** Antes de mudar o modelo, era preciso garantir que os dados estivessem corretos e que o pipeline fosse reproduzível. O princípio adotado foi **falhar cedo**: se falta um dado obrigatório, o programa para com um erro explícito, em vez de preencher um valor inventado que contamina o resultado sem aviso.

**O que foi feito:**

* **`rename_map` corrigido** (`0a27913`) e depois limpo (`2279a71`): ficaram apenas os nomes que a API realmente devolve (`temp_min`, `temp_med`, `temp_max`, `inc` e `data_ini` não existem na resposta).
* **Remoção dos fallbacks** (`2279a71`): colunas obrigatórias ausentes passam a gerar `ValueError`, em vez de `tmin = 22,0` e `rt = 1,0`. A interpolação de valores faltantes passou a ser feita apenas entre valores conhecidos (`interpolate(limit_area='inside')`), sem inventar valores nas pontas da série.
* **Versões fixas das dependências** (`7e59b03`): o `requirements.txt` passou a indicar a versão exata de cada pacote (por exemplo, `lightgbm==4.7.0`, `pandas==3.0.6`), para que o mesmo código produza os mesmos resultados em outra máquina. O `scipy` e o `statsmodels` foram fixados depois (`8c98967`).
* **Série desde 2010** (`05e6200`): o período 2018 a 2024 era apenas o valor padrão escrito no código; a API não tem esse limite. A ingestão passou a buscar de 2010 até o ano corrente. Mais anos significam mais epidemias no treino.
* **Nomes de municípios** (`05e6200`): o nome passou a ser extraído removendo o sufixo do arquivo (`removesuffix`), o que preserva nomes como `rio_claro`.
* **Configuração central dos municípios** (`05e6200`): `src/cidades.py` passou a definir geocode, nome, coordenadas e **papel** de cada município. A base foi ampliada para 19 municípios de SP: 13 de **treino** (os polos UNIVESP dos integrantes e a região entre eles) e 6 de **validação espacial** (outras regiões do estado, com climas contrastantes). O critério foi ter mais de 100 mil habitantes, com a exceção de Cosmópolis, mantida por ser polo de integrante do grupo e reportada à parte.
* **Municípios de validação fora do treino** (`67cc52a`): foi encontrado um erro em que o `train.py` lia todos os arquivos de `data/processed` e treinava também os municípios de validação. A lista de treino passou a vir de `cidades_por_papel('treino')`.

**Decisão sobre o papel dos municípios de validação.** Os municípios de validação **nunca** entram no treino, na escolha de variáveis, no ajuste de hiperparâmetros nem na escolha de parâmetros como `SEMANAS_INSTAVEIS`. Servem apenas para medir se o modelo funciona em municípios que não viu. Todas as escolhas descritas nas seções seguintes foram feitas olhando os municípios de treino; os resultados da validação eram exibidos junto, mas não serviram de critério.

**Limitação.** A amostra inicial de treino era pequena e concentrada: 13 municípios vizinhos, com clima muito parecido. Essa limitação só foi tratada com a ampliação da base ([seções 12](#s12) e [13](#s13)).

---

<a id="s2"></a>
## 2. Descarte das semanas instáveis do nowcast

**Contexto.** As notificações de dengue chegam com atraso: um caso de hoje pode entrar no sistema semanas depois. Por isso, o InfoDengue publica para as semanas recentes um **nowcast**, uma estimativa do número de casos que ainda vão ser notificados para aquela semana (`casos_est`), acompanhada de um intervalo de incerteza (`casos_est_min` e `casos_est_max`). Esses valores são revisados à medida que as notificações chegam. Treinar o modelo com eles seria ensiná-lo com números que ainda vão mudar.

**O que foi testado.** Um primeiro valor provisório de 8 semanas (`68cd5fe`) foi substituído por uma medição com os dados (`0ed9ee6`): para cada município de treino, contou-se quantas semanas finais ainda tinham o intervalo do nowcast aberto (mínimo diferente do máximo).

**Resultado.** Com os dados de 09/2026, os municípios de treino tinham de 7 a 10 semanas finais em nowcast. Cosmópolis e Indaiatuba tinham 10, o maior valor. Campinas, Piracicaba e Hortolândia não publicam intervalo (ele é sempre zero), mas a última semana delas também estava visivelmente incompleta (em Campinas, 68 casos contra cerca de 130 nas semanas anteriores).

**Decisão.** `SEMANAS_INSTAVEIS = 10` em `src/train.py`: as 10 últimas semanas de cada município ficam fora do treino e da avaliação. Dois detalhes de implementação:

* o corte é feito **depois** de descartar as linhas sem alvo, para que também saiam as semanas cujo alvo (H semanas à frente) cai dentro do período instável;
* o corte fica no treino, e não no pré-processamento, porque o painel precisa mostrar as semanas recentes.

**Revisão posterior.** Com a base nacional ([seção 12](#s12)), a medição foi repetida nos 63 municípios de treino; o máximo continuou sendo 10 semanas (por exemplo, Manaus, Belém, Brasília e Teresina), e o valor foi mantido. Somente municípios de treino foram usados nessa medição.

**Limitação.** O critério mede até onde o InfoDengue ainda aplica o nowcast, e não quanto os números efetivamente mudam depois. Medir a revisão real exigiria guardar as ingestões de semanas diferentes e compará-las (limitação registrada no commit `0ed9ee6`).

---

<a id="s3"></a>
## 3. Troca da fonte de clima: do InfoDengue para o ERA5

**Contexto.** Com o `rename_map` corrigido, a temperatura do InfoDengue passou a entrar de fato nos dados, e a análise dela mostrou três problemas:

* **não há precipitação**, uma das variáveis mais citadas na relação entre clima e dengue;
* **vários municípios compartilham a mesma estação meteorológica** até 2022: a temperatura é idêntica em Campinas, Cosmópolis e Piracicaba em 100% das semanas de 2010 a 2022, em 47% das de 2023 e em nenhuma a partir de 2024;
* **a fonte muda no meio da série**: a diferença entre a temperatura do InfoDengue e a do ERA5 em Campinas vai de cerca de −1 °C em 2010 a 2013 para cerca de +0,9 °C em 2021 a 2023.

**Alternativas avaliadas.**

| Fonte | Situação | Motivo |
|---|---|---|
| Clima do InfoDengue | descartado | sem chuva, estação compartilhada, troca de fonte |
| ERA5-Land | descartado | resolução melhor (0,1°), mas sem precipitação |
| Mosqlimate | adiado | agrega o ERA5 por município, mas exige chave de API |
| **ERA5 via Open-Meteo** | **adotado** | série consistente desde 2010, com chuva, sem chave |

O ERA5 é uma **reanálise**: uma reconstrução do clima passado feita pelo Copernicus/ECMWF, que combina observações e modelos físicos numa grade regular, com o mesmo método para toda a série.

**Decisão** (`930a04c`, `126a92e`). O script `src/ingestion_clima.py` baixa a série diária desde 2010 pela latitude e longitude de cada município (`models=era5`), agrega por semana epidemiológica (domingo a sábado, alinhada à data de início da semana do InfoDengue) e salva em `data/raw/clima/`. Só entram semanas com os 7 dias disponíveis, porque uma semana parcial teria média e chuva acumulada distorcidas. Semanas sem clima ficam vazias, em vez de receber um valor copiado, e o painel mostra "sem dado".

**Limitações.**

* A grade do ERA5 tem 0,25°, então municípios vizinhos caem no mesmo ponto: na base de 19 municípios de SP, eram 13 pontos distintos (Cosmópolis, Americana, Sumaré, Hortolândia e Paulínia compartilham o mesmo).
* Os dados chegam com cerca de 6 dias de atraso, então a semana mais recente pode ficar sem clima.

A troca de fonte resolveu a qualidade dos dados de clima, mas não decidiu se o clima deveria entrar no modelo. Essa questão foi testada várias vezes e teve respostas diferentes conforme a base ([seções 10](#s10), [12](#s12) e [14](#s14)).

---

<a id="s4"></a>
## 4. Modelo único com alvo relativo

**Contexto.** O diagnóstico da [seção 0](#s0) mostrou que o problema principal não eram as variáveis, mas o formato do problema. Uma árvore de decisão prevê, em cada folha, uma média de valores vistos no treino; por isso, um modelo de árvores nunca prevê um número de casos maior do que o maior número visto no treino. Com a série desde 2010, o maior valor semanal de Campinas antes de 2024 era 7.074 casos, e a epidemia de 2024 chegou a 11.789.

**O que é o alvo relativo.** O **alvo** é o que o modelo aprende a prever. Em vez de "quantos casos haverá daqui a H semanas" (alvo absoluto), o modelo passou a prever "quanto os casos vão crescer ou cair em relação a hoje", em escala logarítmica:

`alvo = log(1 + casos daqui a H semanas) − log(1 + casos hoje)`

O número de casos é reconstruído a partir da previsão (em `src/predict.py`). Assim, um município com 20 casos e outro com 2.000 que estejam dobrando têm o mesmo alvo, e o modelo aprende o comportamento da epidemia, não o tamanho do município. Prevendo uma variação, o modelo pode chegar a valores nunca vistos, por exemplo "dobrar" a partir de um valor já alto.

**Por que um único modelo para todos os municípios.**

* **Mais epidemias para aprender:** juntando os municípios, o modelo vê muito mais inícios, picos e quedas de surtos do que veria em um único município.
* **Previsão para municípios sem modelo próprio:** o modelo único pode ser aplicado aos municípios de validação, o que permite testar se ele generaliza. Por isso o nome do município **não** entra como variável; se entrasse, não seria possível aplicá-lo a municípios novos.

**O que foi testado** (validação walk-forward com retreino anual, 2015 a 2026, 13 municípios de treino de SP; teste exploratório, ainda com o Rt no modelo):

| Abordagem | H+1 | H+2 | H+3 | H+4 |
|---|---|---|---|---|
| Um modelo por município, alvo absoluto (versão herdada) | 2,07 | 1,40 | 1,16 | 1,00 |
| Um modelo por município, alvo relativo | 0,89 | 0,83 | 0,76 | 0,76 |
| **Modelo único, alvo relativo (adotado)** | **0,87** | **0,79** | **0,75** | **0,72** |

**Resultado.** A troca do alvo foi a mudança de maior efeito de todo o projeto: o modelo passou de errar até o dobro do baseline para errar menos que ele em todos os horizontes. O modelo único acrescentou uma melhora menor, mas consistente.

**Decisão** (`16dedbf`). Um LightGBM por horizonte (H+1 a H+4), treinado com todos os municípios de treino juntos. As variáveis passaram a ser: casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás, semana do ano (sazonalidade) e, nessa primeira versão, o Rt da semana anterior (retirado depois, [seção 9](#s9)). A `p_inc100k` foi retirada por redundância. Outras decisões da mesma etapa:

* **Hiperparâmetros fixos** (300 árvores, taxa de aprendizado 0,05), sem ajuste fino. Testes com 150 e 600 árvores deram diferença desprezível.
* **Avaliação separada da produção:** a avaliação usa modelos treinados só com o passado ([seção 5](#s5)); o modelo salvo para o painel (`models/trained_models/modelo_unico_h{H}.joblib`) é treinado depois, com toda a série disponível (menos as semanas instáveis).

**Limitações.** Os números da tabela vêm de um teste exploratório com retreino anual e com o Rt; podem diferir na segunda casa decimal dos resultados finais em `reports/`. Como todas as alternativas foram avaliadas da mesma forma, a comparação entre elas continua válida.

---

<a id="s5"></a>
## 5. Validação walk-forward e baseline de persistência

**Contexto.** O corte único 80/20 testava apenas um período (de 2023 em diante), dominado pela epidemia de 2024, e o resultado dependia de onde caía o corte. Além disso, qualquer avaliação precisa de uma referência: um erro de 50 casos por semana é bom ou ruim?

**Baseline de persistência.** A referência adotada é a previsão mais simples possível: "daqui a H semanas haverá o mesmo número de casos de hoje". Um **baseline** é uma previsão de referência, simples, que qualquer modelo precisa superar para ser útil. Em séries que mudam devagar, a persistência é difícil de superar em horizontes curtos.

**Validação walk-forward.** Em vez de um único corte, a avaliação "anda para a frente" no tempo, simulando o uso real: em cada ponto de corte, o modelo é treinado só com o que já era conhecido e prevê o período seguinte; depois, o corte avança e o modelo é retreinado com os dados novos.

**O que foi testado.**

1. **Retreino anual** (`16dedbf`): para cada ano de 2015 em diante, um modelo treinado com os anos anteriores prevê o ano inteiro. O início em 2015 garante pelo menos 5 anos de histórico (2010 a 2014) no primeiro treino.
2. **Retreino mensal** (`c9162b0`): no início de cada mês, um modelo é treinado só com o que já era conhecido e prevê as semanas daquele mês. São 141 retreinos por horizonte (jan/2015 a set/2026). Para prever H semanas à frente, o treino só usa exemplos cujo resultado (H semanas depois) já era conhecido antes do início do mês; nenhuma informação do período previsto entra no modelo que o previu.

**Resultados** (razão modelo/baseline, base de 19 municípios de SP):

| Versão | Grupo | H+1 | H+2 | H+3 | H+4 |
|---|---|---|---|---|---|
| Retreino anual (`a0eda83`) | treino (13) | 0,87 | 0,79 | 0,76 | 0,73 |
| Retreino anual (`a0eda83`) | validação (6) | 0,98 | 0,87 | 0,86 | 0,83 |
| Retreino mensal, com Rt (`experimento_variaveis.csv`, configuração A) | treino (13) | 0,855 | 0,787 | 0,756 | 0,735 |
| Retreino mensal, com Rt (idem) | validação (6) | 0,943 | 0,852 | 0,845 | 0,822 |

**Decisão.** Adotar o retreino mensal. O retreino anual deixava a simulação pessimista (o modelo de dezembro não conhecia nada do próprio ano) e não correspondia ao uso real, em que o modelo seria retreinado periodicamente. O erro caiu levemente, por exemplo de 0,98 para 0,94 em H+1 nos municípios de validação.

**Outras decisões desta etapa:**

* **Pandemia (2020 e 2021) mantida.** Treinar sem esses dois anos (teste exploratório, retreino anual) praticamente não mudou o resultado (razão de 0,86 a 0,74 sem a pandemia, contra 0,87 a 0,72 com ela).
* **Relatórios por ano e por município** (`reports/metricas_por_ano.csv`, `reports/metricas_modelos.csv`), para que 2024 e municípios pequenos como Cosmópolis possam ser vistos à parte.

**Anos difíceis.** Na base de SP, o modelo perdia para o baseline em 2016 a 2018, 2020 e 2026: anos de transmissão baixa ou estável, em que repetir o valor atual é difícil de superar e o modelo às vezes antecipa mudanças que não acontecem (como a subida típica do verão). Com a base atual de 115 municípios (`reports/metricas_por_ano.csv`), os piores anos continuam sendo 2017, 2018 e 2026, mas nos municípios de treino a razão fica abaixo de 1 em todos os anos (máximo de 0,985, em 2026, H+1); nos de validação, 2017 fica acima de 1 de H+2 a H+4 (1,01 a 1,11).

**Resultado atual** (base de 115 municípios, retreino mensal, sem Rt; `reports/metricas_gerais.csv`):

| Grupo | H+1 | H+2 | H+3 | H+4 |
|---|---|---|---|---|
| Treino (100) | 0,836 | 0,768 | 0,731 | 0,713 |
| Validação espacial (15) | 0,793 | 0,713 | 0,687 | 0,661 |

**Limitação importante: dados revisados.** A simulação usa os casos na versão revisada de hoje. Em tempo real, as semanas mais recentes ainda estariam incompletas. Por isso a validação é **otimista** nesse ponto. Não é possível corrigir isso para o passado, porque o InfoDengue não disponibiliza os dados como eram conhecidos em cada data (a avaliação correta seria chamada de pseudoprospectiva). A [seção 7](#s7) estima o tamanho desse efeito.

---

<a id="s6"></a>
## 6. Painel: previsões passadas e granularidade semanal

**Contexto.** Para que o usuário do painel (`app.py`) possa julgar a confiabilidade das previsões, é útil mostrar como o modelo teria se saído no passado. Havia, porém, uma armadilha: o modelo de produção foi treinado com toda a série e já "viu" essas semanas, então pareceria melhor do que é.

**Decisão** (`dd7be2e`, `06dc4a8`, `1d3eb26`).

* As previsões passadas **não** são geradas com o modelo de produção. Vêm da validação walk-forward: cada semana foi prevista por um modelo treinado só com o que era conhecido no início do mês dela. O `train.py` salva essas previsões em `reports/previsoes_walkforward.csv`.
* O gráfico mostra os casos reais, as previsões da época e o baseline, com seletor de antecedência (1 a 4 semanas) e de período (últimos 12 meses, um ano específico ou todo o período), e informa o erro médio do modelo e do baseline no período exibido.
* As 10 semanas mais recentes não têm previsão passada, porque os casos delas ainda estão sendo revisados ([seção 2](#s2)).
* O painel mostra a faixa de incerteza do nowcast no histórico e avisa quando os dados estão desatualizados (`22b4525`).
* Filtro de municípios por papel (treino ou validação), com o tipo ao lado do nome.

**Granularidade semanal.** Todos os dados, previsões e gráficos são por semana epidemiológica. É a unidade em que o InfoDengue publica os casos e em que a vigilância trabalha; agregar por mês esconderia a velocidade de crescimento de um surto, que é justamente o que o modelo usa.

**Limitação.** As previsões passadas usam os dados já revisados (mesma limitação da [seção 5](#s5)), e o próprio painel avisa isso.

---

<a id="s7"></a>
## 7. Experimento: previsão com dados atrasados

**Contexto.** A validação da [seção 5](#s5) é otimista porque usa dados revisados. Quanto pior o modelo seria se os dados recentes não estivessem disponíveis?

**O que foi testado** (`src/experimento_atraso.py`, saída em `reports/experimento_atraso.csv`, commit `8683028`). Uma simulação de **pior caso**: na semana X, as semanas X, X-1, X-2 e X-3 são consideradas não confiáveis, e o último dado disponível é o de X-4 (lacuna de 4 semanas). Para prever X+N, o modelo precisa então olhar N+4 semanas à frente a partir de X-4; o baseline repete o último valor confiável. Também foi rodada uma lacuna de 5 semanas. O resto é igual à validação principal, e cada antecedência é avaliada nas mesmas semanas-alvo em todos os cenários. É pior caso porque, na prática, o InfoDengue fornece um nowcast para as semanas recentes, incerto mas não inexistente.

**Resultado** (municípios de treino da base de SP, erro médio em casos por semana):

| Antecedência | Modelo sem lacuna | Modelo com lacuna de 4 semanas | Baseline com lacuna de 4 semanas | Razão com lacuna de 4 | Razão com lacuna de 5 |
|---|---|---|---|---|---|
| 1 semana | 26,49 | 76,15 (2,9×) | 105,71 | 0,720 | 0,705 |
| 2 semanas | 39,47 | 85,62 (2,2×) | 122,70 | 0,698 | 0,690 |
| 3 semanas | 52,00 | 95,89 (1,8×) | 138,60 | 0,692 | 0,686 |
| 4 semanas | 64,82 | 104,27 (1,6×) | 152,55 | 0,684 | 0,673 |

Nos municípios de validação, o erro do modelo cresce de 1,6 a 3,1 vezes com lacuna de 4 semanas, e a razão modelo/baseline fica entre 0,77 e 0,79.

**Conclusões e decisão.**

* O atraso dos dados custa caro: sem as 4 semanas mais recentes, o erro do modelo aumenta de 1,6 a 3,1 vezes, mais nas antecedências curtas (prever "a semana que vem" sem as últimas 4 semanas é, na prática, prever 5 semanas à frente).
* A vantagem relativa do modelo aumenta: com lacuna, ele erra de 21% a 32% menos que o baseline, contra 5% a 26% sem lacuna (somando treino e validação).
* Decisão: manter o modelo e comunicar no painel que as previsões são estimativas de tendência, com margem de erro maior do que a validação sugere.

**Limitações.** O experimento foi rodado com a base de 19 municípios de SP (o arquivo tem 7.799 semanas de treino por antecedência, o número da base de SP) e não foi repetido com a base atual. O cenário real fica entre "sem lacuna" e "lacuna de 4 semanas", mas não se sabe exatamente onde.

---

<a id="s8"></a>
## 8. Mudança de foco: acertar a tendência

**Contexto.** Mesmo quando erra o número exato de casos, o modelo pode acertar se os casos vão subir, ficar estáveis ou cair. Para a vigilância, essa é muitas vezes a pergunta mais útil: decide se é hora de intensificar ações.

**Definição** (`8b0b994`, constantes `LIMIAR_TENDENCIA` e `MIN_CASOS_TENDENCIA` em `src/train.py`). Comparando o valor previsto (ou o real) com o da semana de partida, a semana é classificada como **subida** ou **queda** quando a variação passa de **20% e de 5 casos**; caso contrário, **estável**. O mínimo de 5 casos evita que oscilações pequenas (de 2 para 3 casos, +50%) contem como subida em municípios com poucos casos.

**Referências de comparação.**

* **"Sempre estável":** equivale ao baseline de persistência;
* **"Tendência da última semana":** estende por H semanas a variação observada na última semana.

**Métricas.** "Acerto" é a proporção de semanas com a tendência certa. "Subidas detectadas" é, das semanas em que os casos subiram, a proporção em que o modelo previu subida. "Alarmes corretos" é, das vezes em que o modelo previu subida, a proporção em que os casos de fato subiram. "Sentido oposto" é a proporção de semanas em que o modelo previu subida e houve queda, ou o contrário.

**Resultado na base de SP** (municípios de treino, retreino mensal; valores do README, decisão 11, registrados antes da ampliação da base):

| Antecedência | Modelo | "Sempre estável" | "Última semana" | Subidas detectadas | Alarmes corretos | Sentido oposto |
|---|---|---|---|---|---|---|
| 1 semana | 66% | 65% | 56% | 20% | 49% | 1% |
| 2 semanas | 65% | 54% | 49% | 44% | 60% | 3% |
| 3 semanas | 67% | 48% | 48% | 51% | 64% | 4% |
| 4 semanas | 67% | 44% | 49% | 55% | 66% | 5% |

**Resultado na base atual de 115 municípios** (`reports/metricas_tendencia.csv`):

| Grupo | Antecedência | Modelo | "Sempre estável" | "Última semana" | Subidas detectadas | Alarmes corretos | Sentido oposto |
|---|---|---|---|---|---|---|---|
| Treino (100) | 1 semana | 67,5% | 66,7% | 56,1% | 7,0% | 55,0% | 0,6% |
| Treino (100) | 4 semanas | 63,4% | 47,5% | 47,0% | 40,8% | 62,0% | 4,8% |
| Validação (15) | 1 semana | 64,3% | 63,3% | 52,3% | 7,0% | 55,3% | 0,7% |
| Validação (15) | 4 semanas | 60,4% | 40,6% | 43,1% | 43,3% | 65,8% | 4,8% |

**Conclusões e decisão.**

* **Em 1 semana, o modelo não acrescenta:** acerta tanto quanto dizer "vai ficar igual", porque em uma semana os casos raramente mudam mais de 20%.
* **De 2 a 4 semanas, o modelo é claramente melhor** que as duas referências. Na base atual, com 4 semanas, acerta 16 pontos percentuais a mais que "sempre estável" no treino e 20 na validação.
* **O modelo quase nunca erra o sentido** (no máximo cerca de 5% das semanas); seus erros são quase todos de intensidade, ao prever "estável" quando houve movimento.
* Decisão (`d0ebb23`): o painel passou a mostrar a variação e a tendência prevista para as próximas semanas e um bloco de acerto de tendência para o município, o período e a antecedência escolhidos.

**Como as conclusões mudaram com a base ampliada.** Na base atual o modelo detecta menos subidas (41% contra 55% em 4 semanas; 7% contra 20% em 1 semana) e o acerto geral é um pouco menor, mas os alarmes de subida continuam corretos em cerca de 2 de cada 3 vezes. Parte da diferença vem da mudança no conjunto de municípios avaliados (a própria referência "sempre estável" mudou de 44% para 47,5% em 4 semanas), então as duas tabelas não são diretamente comparáveis. Na comparação feita nas mesmas cidades de SP com a base de 74 municípios ([seção 12](#s12)), o modelo nacional também ficou mais conservador: detectou menos subidas, mas com alarmes mais corretos.

**Limitações.** O limiar de 20% e 5 casos é uma convenção do projeto, não um padrão epidemiológico; outros limiares mudariam os números. As métricas herdam o otimismo dos dados revisados.

---

<a id="s9"></a>
## 9. Retirada do Rt e comparação com a sinalização do InfoDengue

**Contexto.** O Rt entrava no modelo desde a [seção 4](#s4). Três motivos levaram a questioná-lo:

* **Coerência:** o Rt é o resultado de outro modelo, do InfoDengue, com premissas que o grupo não controla e que podem mudar. O nowcast é diferente: estima uma quantidade observável, os casos, que é a matéria-prima do modelo.
* **Redundância:** o Rt mede, de forma elaborada, se os casos estão crescendo; o modelo já recebe isso pelas variações em relação a 1 a 4 semanas atrás.
* **Comparação independente:** sem o Rt dentro do modelo, é possível comparar o modelo com a sinalização de tendência do próprio InfoDengue como duas abordagens separadas.

**O que foi testado** (`src/experimento_variaveis.py`, saída em `reports/experimento_variaveis.csv`, commit `9fa0016`; retreino mensal, 13 municípios de treino de SP):

| Configuração | H+1 | H+2 | H+3 | H+4 | Acerto de tendência (H+4) |
|---|---|---|---|---|---|
| A. Com Rt, sem clima (modelo anterior) | 0,855 | 0,787 | 0,756 | 0,735 | 67,5% |
| **B. Sem Rt, sem clima (adotado)** | **0,865** | **0,787** | **0,754** | **0,739** | **67,3%** |
| C. Sem Rt + chuva e temperatura de 8 semanas | 0,898 | 0,834 | 0,802 | 0,780 | 66,3% |
| D. Sem Rt + chuva, temperatura e umidade (5 variáveis) | 0,951 | 0,890 | 0,845 | 0,805 | 65,8% |
| E. Sem Rt + chuva de 4 e 12 semanas e temperatura de 8 semanas | 0,897 | 0,881 | 0,836 | 0,797 | 65,9% |

**Comparação com o InfoDengue.** O InfoDengue publica o Rt e o `p_rt1` (probabilidade de o Rt ser maior que 1). Esses indicadores foram transformados em regras de tendência aplicadas à semana de partida: `p_rt1` acima de 0,9 → sobe, abaixo de 0,1 → cai; Rt acima de 1,1 → sobe, abaixo de 0,9 → cai; caso contrário, estável. Resultado nos municípios de treino, com a definição de tendência da [seção 8](#s8):

| Antecedência | Acerto: modelo | Acerto: regra `p_rt1` | Acerto: regra Rt | Alarmes corretos: modelo | Alarmes corretos: `p_rt1` | Sentido oposto: modelo | Sentido oposto: `p_rt1` |
|---|---|---|---|---|---|---|---|
| 1 semana | 66% | 48% | 28% | 49% | 29% | 1% | 7% |
| 2 semanas | 65% | 50% | 33% | 60% | 42% | 3% | 8% |
| 3 semanas | 67% | 51% | 36% | 64% | 47% | 4% | 9% |
| 4 semanas | 67% | 50% | 37% | 66% | 50% | 5% | 10% |

Nos municípios de validação, com 4 semanas: 59% para o modelo, 50% para a regra `p_rt1` e 45% para a regra Rt.

**Resultado e decisão** (`ecfb204`). Retirar o Rt praticamente não mudou nada (diferença de no máximo 0,01 na razão e o mesmo acerto de tendência), o que confirma a redundância. O modelo adotado passou a ser o B: apenas casos e semana do ano. Na comparação, o modelo acerta de 15 a 18 pontos percentuais a mais que a regra `p_rt1`, tem alarmes mais confiáveis e erra o sentido com metade ou menos da frequência. A regra Rt detecta mais subidas (50% a 55%), mas só 22% a 39% dos seus alarmes se confirmam.

**Limitações.** O Rt não foi criado para prever os casos daqui a 1 a 4 semanas com o critério de 20% do projeto; a comparação mostra que, para essa pergunta específica, o modelo é mais útil que uma leitura direta do Rt, e não que o Rt seja um indicador ruim para o que se propõe. As regras e seus limiares foram definidos pelo grupo. O experimento foi feito com a base de SP e não foi repetido com a base atual.

---

<a id="s10"></a>
## 10. Clima no modelo: testes com a base de SP

**Contexto.** A literatura associa a dengue à temperatura e à chuva, e o ERA5 ([seção 3](#s3)) deu uma série de clima consistente. A pergunta era se o clima melhora a previsão de 1 a 4 semanas.

**O que foi testado, em três rodadas:**

1. **Agregados de clima, com Rt** (teste exploratório com retreino anual, junto com a [seção 4](#s4)):

   | Variáveis | H+1 | H+2 | H+3 | H+4 |
   |---|---|---|---|---|
   | **Sem clima** | **0,87** | **0,79** | **0,75** | **0,72** |
   | Chuva acumulada de 4 e 8 semanas e temperatura média de 8 semanas | 0,90 | 0,83 | 0,80 | 0,76 |
   | Chuva de 4 e 12 semanas e temperatura de 8 semanas | 0,91 | 0,82 | 0,78 | 0,73 |
   | 5 variáveis agregadas de chuva, temperatura e umidade | 0,94 | 0,85 | 0,85 | 0,79 |
   | 22 variáveis (defasagens semanais de 1 a 8 semanas) | 0,94 | 0,82 | 0,83 | 0,77 |

2. **Agregados sem Rt**, com retreino mensal (configurações C a E da [seção 9](#s9)), para verificar se o Rt estava "cobrindo" o efeito do clima: o clima continuou piorando em todas as combinações e horizontes.

3. **Clima de semanas específicas** (`src/experimento_clima_semanal.py`, commit `51ef662`). O ciclo de ovo a mosquito adulto leva de 7 a 10 dias e depende do clima, então foi testado o clima semana a semana, sem agregar, nas semanas anteriores à semana atual S (S-1 é a semana anterior, S-2 a de duas semanas antes, e assim por diante). O clima da própria semana S não é usado, porque o ERA5 chega com cerca de 6 dias de atraso. Cada combinação foi testada com todas as variáveis ("completo": temperaturas mínima, média e máxima, chuva e umidade) e com um conjunto essencial (temperatura média, chuva e umidade):

   | Clima usado | H+1 | H+2 | H+3 | H+4 |
   |---|---|---|---|---|
   | **Sem clima** | **0,865** | **0,787** | **0,754** | **0,739** |
   | S-1 e S-2 (essencial) | 0,915 | 0,818 | 0,790 | 0,781 |
   | S-1 e S-3 (essencial) | 0,933 | 0,842 | 0,801 | 0,751 |
   | S-1, S-2 e S-3 (essencial) | 0,930 | 0,837 | 0,805 | 0,772 |
   | S-1 e S-2 (completo) | 0,932 | 0,832 | 0,811 | 0,783 |
   | S-1 e S-3 (completo) | 0,942 | 0,835 | 0,822 | 0,785 |
   | S-1, S-2 e S-3 (completo) | 0,945 | 0,818 | 0,808 | 0,801 |

   O acerto de tendência com 4 semanas ficou igual ou um pouco pior (65,8% a 67,3%, contra 67,3% sem clima; na validação, 56% a 57%, contra 59%).

**Decisão.** Com a base de SP, o clima ficou **fora do modelo**, mantido no painel e na análise exploratória.

**Interpretação da época.** O efeito do clima sobre a dengue aparece com semanas de atraso e já estaria refletido na tendência recente dos casos, que o modelo usa; a semana do ano já captura a sazonalidade. Além disso, os 13 municípios de treino eram vizinhos, com clima muito parecido e vários no mesmo ponto da grade do ERA5, o que limitava o que o modelo poderia aprender.

**Observação metodológica.** Um primeiro teste com o corte único 80/20 sugeria que o clima ajudava em H+3 e H+4. A validação walk-forward não confirmou isso, o que mostra o risco de concluir a partir de um único período de teste.

**Esta decisão foi revista.** A hipótese de que o problema era a pouca variação de clima entre os municípios de treino motivou os testes com a base nacional. Com 100 municípios e validação cruzada por município, o clima passou a melhorar, de forma pequena mas estatisticamente significativa, a previsão de 4 semanas ([seção 14](#s14)).

**Limitação de reprodutibilidade.** A tabela da rodada 3 não pode ser regenerada a partir do arquivo atual: `reports/experimento_clima_semanal.csv` foi sobrescrito pela versão com a base nacional (commit `179dd03`), e o script foi alterado para as novas configurações. Os números acima estão no README e no arquivo do commit `51ef662` (`git show 51ef662:reports/experimento_clima_semanal.csv`).

---

<a id="s11"></a>
## 11. Robustez da ingestão

**Contexto.** Ampliar a base exigia baixar 16 anos de clima diário de dezenas de municípios. A Open-Meteo limita o uso gratuito por minuto, por hora e por dia, e a série completa de um município com 5 variáveis conta como muitas chamadas: pelas notas de trabalho (`temp/CONTINUAR.md`), cerca de 220 chamadas por município, com limite diário de 10 mil, ou seja, cerca de 45 municípios por dia numa coleta do zero. A primeira versão da ingestão já esperava e tentava de novo em caso de erro 429 (limite atingido), mas não distinguia os tipos de limite.

**Decisão** (`1941b65`).

* **`src/http_utils.py`:** requisições com novas tentativas automáticas. Em erro 429, espera o tempo indicado pelo servidor (cabeçalho `Retry-After`) ou o tempo da janela do limite atingido (65 segundos para o limite por minuto, 1 hora para o limite por hora). Em erros temporários (erro 5xx do servidor, tempo esgotado ou falha de conexão), espera um tempo crescente, que dobra a cada tentativa, até 6 tentativas.
* **Limite diário:** não é esperado (seriam horas). A ingestão para com uma mensagem clara, mantém o que já foi salvo e continua de onde parou na próxima execução.
* **Clima incremental:** quando o arquivo de um município já existe, só as últimas 12 semanas são baixadas de novo (o ERA5 preliminar é substituído pelo definitivo em cerca de 2 a 3 meses); `--completo` baixa tudo. Pontos da grade do ERA5 repetidos entre municípios vizinhos são reaproveitados.
* **Ingestão de casos:** usa o mesmo utilitário e termina com erro se algum município falhar (falhar cedo).
* **Opção `--sem-clima`** (`0ccbd76`) no pré-processamento e no experimento de clima, para permitir treinar e avaliar o modelo sem esperar a ingestão de clima terminar.

**Resultado.** A ingestão da base de 74 municípios atingiu o limite diário (65 de 74 municípios na primeira rodada, segundo `temp/CONTINUAR.md`), parou como previsto e foi retomada depois.

**Limitação.** A primeira execução completa com 115 municípios leva algumas horas e pode precisar de mais de um dia. A dependência de um serviço gratuito com limites é um risco operacional para uma atualização automática do painel.

---

<a id="s12"></a>
## 12. Ampliação para a base nacional (74 municípios)

**Contexto.** Duas observações apontavam para a mesma limitação: o ganho com mais municípios de SP estava diminuindo, e o clima podia não estar ajudando porque os 13 municípios de treino eram vizinhos. O teste da época com 4, 7, 10 e 13 municípios de treino, sorteados e avaliados nos municípios de validação (retreino anual, com Rt), mostrava:

| Municípios no treino | H+1 | H+2 | H+3 | H+4 |
|---|---|---|---|---|
| 4 | 1,04 | 0,96 | 0,93 | 0,91 |
| 7 | 1,00 | 0,92 | 0,87 | 0,86 |
| 10 | 0,97 | 0,89 | 0,85 | 0,83 |
| 13 | 0,97 | 0,87 | 0,85 | 0,83 |

A conclusão na época foi que mais municípios ajudavam, mas com ganho decrescente, e que novos municípios só valeriam a pena se trouxessem climas diferentes.

**Decisão** (`f018e11`). Incluir 55 municípios de outras regiões:

* **Treino (50):** em cada uma das 26 UFs fora de SP, a capital e o maior município não capital com mais de 100 mil habitantes a mais de 50 km da capital. A distância evita municípios da mesma região metropolitana, que teriam o mesmo clima. AC, AP, DF e RR não têm esse segundo município; as 2 vagas restantes foram para os maiores municípios restantes do país pelo mesmo critério (Juiz de Fora e Montes Claros, MG).
* **Validação (5):** o maior município restante de cada macrorregião: Parauapebas (PA), Caruaru (PE), Rio Verde (GO), Uberaba (MG) e Maringá (PR).

Total: 74 municípios, 63 de treino e 11 de validação.

**O que foi testado** (`src/experimento_clima_semanal.py` na versão nacional, saída em `reports/experimento_clima_semanal.csv`, commit `179dd03`). Primeiro, um modelo treinado só com os 13 municípios de SP contra um modelo treinado com os 63, ambos sem clima e avaliados nas mesmas semanas dos municípios de SP:

| Municípios avaliados | Treino do modelo | H+1 | H+2 | H+3 | H+4 |
|---|---|---|---|---|---|
| SP, treino | só SP (13) | 0,865 | 0,787 | 0,754 | 0,739 |
| SP, treino | nacional (63) | **0,804** | **0,720** | **0,683** | **0,665** |
| SP, validação | só SP (13) | 0,946 | 0,860 | 0,841 | 0,828 |
| SP, validação | nacional (63) | **0,779** | **0,704** | **0,660** | **0,638** |
| Fora de SP, treino | nacional (63) | 0,842 | 0,777 | 0,739 | 0,717 |
| Fora de SP, validação | nacional (63) | 0,854 | 0,794 | 0,747 | 0,732 |

**Resultado.** O treino nacional **melhorou a previsão de SP**: o erro caiu de 7% a 10% nos municípios de treino de SP e de 18% a 23% nos de validação de SP, que eram o ponto fraco do modelo. No acerto de tendência com 4 semanas nos municípios de treino de SP, o modelo nacional ficou mais conservador: acerto de 66,4% contra 67,3%, subidas detectadas 48,8% contra 54,5%, alarmes corretos 70,6% contra 65,8% e sentido oposto 3,1% contra 4,5%.

Em seguida, o clima foi testado de novo com a base nacional (temperatura média, chuva e umidade, conjunto "essencial"), em janelas de S-1 a S-2, S-1 a S-4, S-1 a S-5 e na média de S-1 a S-8. Os resultados foram mistos: em H+1, fora de SP, o clima piorou em todas as combinações (0,856 a 0,878, contra 0,842 sem clima), e em SP as diferenças foram pequenas nos dois sentidos; em H+4 houve pequenas melhoras em algumas combinações (por exemplo, nos municípios de treino de SP, 0,640 com S-1 a S-4 contra 0,665 sem clima; fora de SP, 0,709 com S-1 a S-5 contra 0,717). Como a avaliação era feita nos próprios municípios de treino e as diferenças eram pequenas, esses números não permitiam separar efeito real de variação do acaso. Isso motivou o método mais rigoroso da [seção 14](#s14).

**Decisão.** Manter a base nacional e o modelo sem clima, e buscar um método de avaliação que medisse a incerteza.

**Limitações.**

* Esses resultados não foram registrados no README; estão apenas no CSV e em `temp/CONTINUAR.md`.
* O modelo usa a semana do ano para a sazonalidade, e o pico da dengue no Norte e no Nordeste não coincide com o de SP. Isso não piorou SP, mas a sazonalidade por região não foi modelada explicitamente.

---

<a id="s13"></a>
## 13. Base de 115 municípios e lista em `data/config/cidades.csv`

**Contexto.** O objetivo do projeto passou a ser mostrar que o modelo **generaliza** para municípios que não viu. Para isso, eram necessários mais municípios de treino (para uma validação cruzada por município, [seção 14](#s14)) e mais municípios de validação.

**Lista como configuração** (`496bf00`). A lista saiu do código e passou a ser um CSV editável, `data/config/cidades.csv`, com chave, geocode IBGE, nome, UF, coordenadas, papel, população (Censo 2022) e critério de inclusão de cada município. `src/cidades.py` lê o arquivo e verifica a consistência (colunas, chaves, geocodes e papéis). Fica em `data/config/` porque é uma configuração criada pelo grupo, e não um dado baixado (`data/raw/`) nem gerado pelo pipeline (`data/processed/`).

**Novos municípios de validação (4).** Para chegar a 15, o maior município restante de cada macrorregião fora do Sudeste, numa UF ainda sem município de validação: Manacapuru (AM), Vitória da Conquista (BA), Sinop (MT) e Blumenau (SC). Foram escolhidos **antes** dos novos municípios de treino, por tamanho e região, sem olhar os surtos.

**Novos municípios de treino (37)** (`5d4fed5`):

* **Quantos por UF:** as 100 vagas de treino foram distribuídas entre as UFs em proporção à população (Censo 2022), pelo método dos maiores restos (cada UF recebe a parte inteira da sua cota, e as vagas que sobram vão para as maiores partes fracionárias). Os municípios que já estavam no treino contam como piso, então nenhuma UF perdeu município. Como as UFs pequenas já estavam acima da cota, as vagas novas foram para as mais populosas: SP 8, MG 6, RJ 5, BA 4, PR 3, RS 3, CE 2, PA 2, PE 1, SC 1, GO 1 e MA 1. A segunda vaga de PE não teve candidato que cumprisse a distância mínima e foi para PA.
* **Quais municípios:** em cada UF, entre os municípios com mais de 100 mil habitantes, os de **maior incidência média anual de dengue entre 2010 e 2025** (casos por 100 mil habitantes), a mais de 50 km de qualquer município já incluído.
* **Por que municípios com surtos:** o modelo precisa aprender como as epidemias começam, atingem o pico e terminam, e esses eventos são raros na série de cada município.

**Critério revisto antes da aplicação.** Uma proposta anterior (`temp/cidades_proposta.md`, marcada como substituída) usava o número de anos com incidência alta (300 ou mais casos por 100 mil habitantes, classificação do Ministério da Saúde), com desempate pelo pico e distância mínima de 25 km. Esse critério não diferenciava os candidatos, porque vários passam do limite todos os anos, e foi trocado pela incidência média anual, com distância mínima de 50 km.

**Viés de seleção.** **Viés de seleção** é a distorção que surge quando a forma de escolher a amostra a torna diferente da população que se quer representar. Escolher municípios pelo histórico de surtos faz o treino ter mais epidemias do que um município típico teria, e o modelo pode ficar mais propenso a prever subidas. Por isso:

* os municípios de validação foram escolhidos por outros critérios (tamanho e região) e antes dos de treino, e continuam sendo o teste sem esse viés;
* avaliações feitas dentro do conjunto de treino, como a validação cruzada por município da [seção 14](#s14), refletem um conjunto com mais surtos que o normal, e isso deve ser dito ao interpretar os resultados.

**Resultado** (`26cbcfa`). Com 100 municípios de treino e 15 de validação, a razão modelo/baseline ficou em 0,836 a 0,713 no treino e 0,793 a 0,661 na validação (tabela da [seção 5](#s5)). Com 74 municípios, os valores já eram muito próximos (0,836 a 0,708 no treino e 0,799 a 0,659 na validação, `reports/metricas_gerais.csv` no commit `b1e6925`).

---

<a id="s14"></a>
## 14. Generalização para municípios não vistos

**Contexto.** Com o novo foco, a avaliação nos 15 municípios de validação era insuficiente: 15 municípios são poucos para separar um efeito pequeno (como o do clima) da sorte na escolha dos municípios. Faltava também saber se valeria a pena ampliar ainda mais a base.

**Método** (`src/experimento_generalizacao.py`, saídas em `reports/generalizacao_configuracoes.csv` e `reports/generalizacao_curva.csv`, commit `4965f7a`). Os 15 municípios de validação não foram usados.

* **Validação cruzada por município:** os 100 municípios de treino foram divididos em 5 grupos de 20. Cada grupo foi previsto por modelos treinados só com os outros 80, com a mesma validação walk-forward (retreino a cada 3 meses, em vez de mensal, para o experimento caber em tempo razoável). Assim, todos os 100 municípios são avaliados como se fossem desconhecidos.
* **Intervalo de confiança de 95% por bootstrap sobre municípios.** O **bootstrap** estima a incerteza de uma métrica refazendo o cálculo muitas vezes com amostras sorteadas, com reposição, a partir dos próprios dados. Aqui foram 2.000 sorteios de municípios. O **intervalo de confiança de 95%** é a faixa em que a métrica ficou em 95% desses sorteios; se o intervalo de uma diferença não inclui zero, a diferença dificilmente é efeito do acaso na escolha dos municípios. A unidade sorteada é o município, e não a semana, porque as semanas de um mesmo município são muito parecidas entre si; tratá-las como independentes daria uma falsa precisão. Nas comparações entre configurações, o sorteio é pareado (os mesmos municípios para as duas).
* **Curva de aprendizado:** o mesmo esquema, treinando com apenas 10, 20, 40, 60 ou 80 municípios sorteados (3 sorteios por tamanho, retreino a cada 6 meses). Foi ajustada a curva `erro(n) = a + b·n^(-c)`, em que `a` é o erro que se alcançaria com infinitos municípios.

**Resultado 1: o modelo generaliza** (sem clima):

| Antecedência | Razão | IC 95% |
|---|---|---|
| 1 semana | 0,840 | 0,811 a 0,872 |
| 2 semanas | 0,774 | 0,742 a 0,810 |
| 3 semanas | 0,742 | 0,713 a 0,777 |
| 4 semanas | 0,728 | 0,702 a 0,759 |

Em todos os horizontes, o intervalo fica inteiramente abaixo de 1: o modelo erra de 16% a 27% menos que o baseline em municípios que não viu.

**Resultado 2: o efeito do clima é pequeno e depende do horizonte.** Diferença na razão em relação ao modelo sem clima (negativo significa que o clima melhora), com IC 95%:

| Clima usado | 1 semana | 2 semanas | 3 semanas | 4 semanas |
|---|---|---|---|---|
| S-1 a S-2 | +0,017 (+0,004 a +0,031) | +0,007 (−0,003 a +0,018) | −0,001 (−0,013 a +0,016) | −0,007 (−0,018 a +0,005) |
| S-1 a S-4 | +0,019 (+0,007 a +0,032) | +0,005 (−0,005 a +0,014) | −0,005 (−0,017 a +0,010) | **−0,014 (−0,023 a −0,004)** |
| S-1 a S-5 | +0,018 (+0,006 a +0,031) | +0,008 (−0,004 a +0,023) | −0,004 (−0,017 a +0,012) | **−0,014 (−0,027 a −0,002)** |
| Média de S-1 a S-8 | +0,011 (+0,001 a +0,020) | +0,007 (−0,003 a +0,016) | 0,000 (−0,010 a +0,012) | −0,004 (−0,014 a +0,007) |

* Em 1 semana, o clima **piora** a previsão em todas as configurações, e a piora é estatisticamente significativa.
* Em 4 semanas, o clima de S-1 a S-4 ou de S-1 a S-5 **melhora** a previsão, de forma significativa, mas pequena (cerca de 2% do erro).
* Em 2 e 3 semanas, não há diferença que se distinga do acaso.
* No acerto de tendência com 4 semanas, o clima de S-1 a S-4 também ajuda um pouco (64,0% contra 63,2%; subidas detectadas 42,7% contra 40,3%).

A interpretação é coerente com a biologia: o efeito do clima sobre os casos leva semanas para aparecer (desenvolvimento do mosquito, incubação no mosquito e na pessoa, notificação). Para a semana seguinte, os casos atuais já dizem quase tudo; para 4 semanas à frente, o clima recente traz alguma informação a mais.

**Resultado 3: mais municípios ajudam cada vez menos** (média dos sorteios):

| Municípios no treino | 1 semana | 2 semanas | 3 semanas | 4 semanas |
|---|---|---|---|---|
| 10 | 0,906 | 0,857 | 0,828 | 0,806 |
| 20 | 0,870 | 0,813 | 0,780 | 0,765 |
| 40 | 0,856 | 0,793 | 0,764 | 0,748 |
| 60 | 0,847 | 0,784 | 0,751 | 0,734 |
| 80 | 0,841 | 0,774 | 0,741 | 0,728 |
| *Limite estimado (infinitos municípios)* | *0,828* | *0,756* | *0,725* | *0,702* |
| *Previsto com 200 municípios* | *0,835* | *0,766* | *0,734* | *0,717* |

De 10 para 40 municípios, o erro cai de 5,5% a 7,7%; de 40 para 80, de 1,8% a 3,0%. Pela curva ajustada, passar de 100 para 200 municípios reduziria o erro em cerca de 1% (0,6% a 1,2%), e mesmo com infinitos municípios o ganho em relação a 100 ficaria entre 1,4% e 3,3%.

**Decisões.**

* A capacidade de generalização passou a ser o principal resultado do projeto, sustentado por intervalos de confiança.
* A conclusão sobre o clima foi **revista**: o clima não ajuda em horizontes curtos, mas ajuda um pouco em 4 semanas. O modelo de produção descrito em `src/train.py` continua sem clima (`FEATURES` sem variáveis climáticas); a forma de incorporar o clima só no horizonte de 4 semanas não está registrada nas fontes consultadas.
* Ampliar a base deixou de ser prioridade: com 100 municípios, a quantidade de dados não é mais o principal limite. Ganhos maiores dependeriam de outras informações ou de outra forma de modelar, o que motiva a comparação de modelos ([seção 16](#s16)).

**Limitações.**

* A validação cruzada usa os municípios de treino, escolhidos em parte pelo histórico de surtos (viés de seleção, [seção 13](#s13)).
* O retreino a cada 3 meses (e a cada 6 na curva) é menos frequente que o mensal usado na validação principal, então os números não são diretamente comparáveis aos de `reports/metricas_gerais.csv`.
* A curva foi ajustada com 5 pontos e 3 sorteios por ponto; o limite estimado é uma extrapolação e deve ser lido como ordem de grandeza.
* Todas as avaliações continuam usando dados revisados ([seção 7](#s7)).

---

<a id="s15"></a>
## 15. Como as conclusões mudaram ao longo do projeto

| Questão | Primeira conclusão | Conclusão revista | Por que mudou |
|---|---|---|---|
| O clima ajuda? | Corte 80/20: parecia ajudar em H+3 e H+4 | Base de SP, walk-forward: piora em todas as combinações ([seção 10](#s10)) | Um único período de teste não era representativo |
| O clima ajuda? | Base de SP: não | Base nacional com validação cruzada: piora em 1 semana, ajuda pouco (cerca de 2%) em 4 semanas ([seção 14](#s14)) | Mais variação de clima entre municípios e um método que mede a incerteza |
| Vale incluir mais municípios? | Base de SP: ganho pequeno de 10 para 13 | Treino nacional melhorou SP em 7% a 23% (treino e validação de SP) ([seção 12](#s12)) | Os novos municípios trouxeram epidemias e climas diferentes, não só mais dados parecidos |
| Vale incluir mais municípios? | Base nacional: sim | Com 100, o ganho esperado de novos municípios é de cerca de 1% ([seção 14](#s14)) | A curva de aprendizado se aproxima do limite |
| O Rt é necessário? | Entrou no primeiro modelo único | Retirado sem perda ([seção 9](#s9)) | Era redundante com as variações de casos |
| Quantas semanas instáveis? | 8 (provisório) | 10, confirmado na base nacional ([seção 2](#s2)) | Medição com os dados |
| Com que frequência retreinar na validação? | Anual | Mensal ([seção 5](#s5)) | O anual era pessimista e não refletia o uso real |
| O que medir? | Erro no número de casos | Também o acerto de tendência ([seção 8](#s8)) | É a pergunta mais útil para a vigilância |

**Limitações que permanecem em todo o projeto.**

* Todas as avaliações usam os dados já revisados; o desempenho em tempo real deve ser pior, e o experimento de atraso dá apenas um pior caso.
* Os experimentos de atraso ([seção 7](#s7)) e de variáveis/Rt ([seção 9](#s9)) foram rodados com a base de SP e não foram repetidos com a base atual.
* A seleção de parte dos municípios de treino por surtos introduz viés nas avaliações internas.
* Os hiperparâmetros não foram ajustados.

**Para reproduzir.** A partir da raiz do projeto, com as dependências de `requirements.txt`:

```bash
python -m src.ingestion
python -m src.ingestion_clima
python -m src.preprocessing
python -m src.train                      # reports/metricas_*.csv e previsoes_walkforward.csv
python -m src.experimento_atraso         # reports/experimento_atraso.csv
python -m src.experimento_variaveis      # reports/experimento_variaveis.csv
python -m src.experimento_clima_semanal  # reports/experimento_clima_semanal.csv
python -m src.experimento_generalizacao  # reports/generalizacao_*.csv
```

Rodar hoje os experimentos de atraso, de variáveis e de clima semanal usa a base atual de 115 municípios e, portanto, produz números diferentes dos registrados nas seções 7, 9, 10 e 12, que foram obtidos com bases menores. As versões originais dos arquivos podem ser consultadas com `git show <commit>:<arquivo>`, usando os commits indicados em cada seção.

---

<a id="s16"></a>
## 16. Comparação de modelos

### Contexto e pergunta

A decisão 4 escolheu o LightGBM, e todas as decisões seguintes mudaram os dados e as variáveis, mas nunca o algoritmo. Os hiperparâmetros também nunca tinham sido ajustados. Além disso, a curva de aprendizado (seção 14) indicou que mais municípios quase não melhoram o modelo, então eventuais ganhos teriam de vir da forma de modelar. A pergunta passou a ser: **o LightGBM é o melhor modelo para dizer se os casos vão subir, ficar estáveis ou cair nas próximas 1 a 4 semanas, em municípios que ele nunca viu?**

### O que foi testado

Oito modelos, cada um em um arquivo de `src/modelos/`, todos com as mesmas informações de entrada (casos atuais, variação em relação a 1 a 4 semanas atrás e semana do ano; sem clima e sem Rt):

| Modelo | Arquivo | Ideia |
|---|---|---|
| Baseline de persistência | `baseline_persistencia.py` | Repete os casos atuais; tendência sempre "estável" |
| Regressão linear (Ridge) | `regressao_linear.py` | Testa se as relações não lineares do LightGBM fazem diferença |
| Binomial negativa | `binomial_negativa.py` | Modelo clássico da epidemiologia para contagens de casos |
| LightGBM atual | `lightgbm_atual.py` | O modelo do projeto, com hiperparâmetros fixos |
| LightGBM ajustado | `lightgbm_ajustado.py` | Hiperparâmetros escolhidos por busca em grade |
| LightGBM por quantis | `lightgbm_quantis.py` | Prevê a mediana e um intervalo de 80% ("entre X e Y casos") |
| LightGBM classificador | `lightgbm_classificador.py` | Prevê a tendência diretamente, em vez do número de casos |
| Ensemble | `ensemble.py` | Média da regressão linear, da binomial negativa e do LightGBM atual |

**Como foram comparados** (`src/experimento_modelos.py`):

* **Validação cruzada por município**, nos mesmos 5 grupos de 20 municípios da seção 14: cada grupo é previsto por modelos treinados só com os outros 80. É por essa avaliação que os modelos são comparados. Os 15 municípios de validação final foram avaliados à parte (treino com os 100) e **não** foram usados para escolher.
* **Walk-forward** com retreino a cada 3 meses, de 2019 em diante. Os anos de 2015 a 2018 foram reservados para escolher os hiperparâmetros do LightGBM ajustado, para que o ajuste não "visse" o período da comparação.
* **Métrica principal: acerto balanceado da tendência.** É a média do acerto em cada uma das três classes (sobe, estável, cai). O acerto simples engana: como a maioria das semanas é estável, dizer sempre "estável" acerta 65% das semanas com 1 semana de antecedência, mas o acerto balanceado dessa estratégia é de apenas 33%, o mesmo que sortear.
* **Métricas secundárias:** acerto simples, subidas detectadas, alarmes de subida corretos, sentido oposto, razão entre o erro em casos do modelo e o do baseline e, no modelo por quantis, a cobertura do intervalo de 80%.
* **Intervalos de confiança de 95%** por bootstrap sobre municípios (2.000 sorteios) e diferença pareada em relação ao LightGBM atual.
* **Resultados:** `reports/comparacao_modelos.csv` (métricas com intervalos de confiança, em formato longo, para tabelas e gráficos) e `reports/comparacao_modelos_por_municipio.csv` (matriz de confusão e erros por município, a partir da qual qualquer métrica pode ser recalculada).

### Resultados

**Como ler a tabela a seguir:** os valores são o próprio acerto balanceado de cada modelo, de 0 a 1. **Quanto maior, melhor**, e o baseline de persistência tira 0,333. Não são uma divisão pelo baseline.

**Exemplo de cálculo** (LightGBM atual, 4 semanas, somando as semanas dos 100 municípios):

| O que aconteceu | Semanas | O modelo acertou | Acerto nessa situação |
|---|---|---|---|
| Subiu | 10.738 | 4.471 | 41,6% |
| Ficou estável | 17.161 | 12.915 | 75,3% |
| Caiu | 10.899 | 6.613 | 60,7% |

Acerto balanceado = (41,6% + 75,3% + 60,7%) / 3 = 0,592. O baseline sempre diz "estável" e acerta 0%, 100% e 0% nessas três situações; a média é 0,333. No acerto simples, o baseline pareceria melhor do que é (17.161 / 38.798 = 44%), porque a maioria das semanas é estável.

**Acerto balanceado da tendência** (validação cruzada, 100 municípios; entre parênteses, a diferença em relação ao LightGBM atual, com o intervalo de confiança de 95%):

| Modelo | 1 semana | 2 semanas | 3 semanas | 4 semanas |
|---|---|---|---|---|
| Baseline de persistência | 0,333 | 0,333 | 0,333 | 0,333 |
| Regressão linear | 0,367 | 0,428 | 0,496 | 0,536 |
| Binomial negativa | 0,368 | 0,443 | 0,520 | 0,565 |
| Ensemble | 0,363 | 0,462 | 0,545 | 0,586 |
| LightGBM por quantis | 0,374 | 0,499 | 0,554 | 0,586 |
| LightGBM atual | 0,387 | 0,509 | 0,562 | 0,592 |
| LightGBM ajustado | 0,398 (+0,011; +0,007 a +0,014) | 0,507 (−0,003; −0,006 a 0,000) | 0,562 (0,000; −0,003 a +0,003) | 0,589 (−0,003; −0,006 a 0,000) |
| **LightGBM classificador** | **0,419 (+0,033; +0,029 a +0,037)** | **0,554 (+0,044; +0,039 a +0,050)** | **0,605 (+0,043; +0,037 a +0,048)** | **0,623 (+0,031; +0,025 a +0,036)** |

Todos os modelos que não são LightGBM ficaram abaixo do LightGBM atual, com intervalos de confiança que excluem zero em todos os horizontes.

**Perfil de cada modelo com 4 semanas de antecedência** (validação cruzada; porcentagens: maior é melhor, exceto "sentido oposto", em que menor é melhor; razão de erro em casos: menor é melhor, abaixo de 1 o modelo supera o baseline):

| Modelo | Acerto | Subidas detectadas | Alarmes de subida corretos | Sentido oposto | Razão de erro em casos |
|---|---|---|---|---|---|
| Baseline de persistência | 44,2% | 0% | não se aplica | 0% | 1,000 |
| Regressão linear | 56,9% | 25,6% | 54,7% | 6,6% | 0,838 |
| Binomial negativa | 57,7% | 59,8% | 49,5% | 8,2% | 0,872 |
| Ensemble | 60,8% | 46,0% | 57,8% | 6,2% | 0,754 |
| LightGBM atual | 61,9% | 41,6% | 65,1% | 5,0% | 0,717 |
| LightGBM ajustado | 61,5% | 41,2% | 64,3% | 5,1% | 0,714 |
| LightGBM por quantis | 61,8% | 41,2% | 65,2% | 4,5% | 0,701 |
| LightGBM classificador | 62,6% | 54,8% | 56,9% | 8,9% | não prevê casos |

**Validação final (15 municípios):** a ordem dos modelos se repete. Com 4 semanas, o acerto balanceado é de 0,611 para o classificador e 0,594 para o LightGBM atual; a razão de erro em casos é de 0,658 para o LightGBM por quantis e 0,662 para o atual.

**Intervalo de 80% do modelo por quantis:** o valor real ficou dentro do intervalo em 78% a 80% das semanas na validação cruzada e em 81% a 82% na validação final, muito perto dos 80% esperados. Ou seja, o intervalo é bem calibrado.

**Ajuste dos hiperparâmetros:** a busca em grade testou 18 combinações (número de folhas, mínimo de exemplos por folha e número de árvores; `reports/lightgbm_ajustado_ajuste.csv`). A melhor (63 folhas, 100 exemplos por folha, 400 árvores) teve acerto balanceado de 0,5095 no período de ajuste, praticamente igual à segunda (0,5092). No período de comparação, o ganho sobre o LightGBM atual foi nulo ou mínimo.

### Leitura dos resultados

* **As relações não lineares fazem diferença.** A regressão linear e a binomial negativa ficaram bem abaixo dos modelos de árvores, tanto na tendência quanto no erro em casos; com 1 semana, as duas erram mais que o próprio baseline em número de casos (razão acima de 1). O modelo clássico da epidemiologia, sozinho, não é o mais adequado para esta tarefa.
* **Combinar modelos não ajudou.** O ensemble ficou abaixo do LightGBM sozinho: os dois modelos mais fracos puxaram a média para baixo.
* **Ajustar os hiperparâmetros não ajudou.** As configurações testadas deram resultados quase iguais, o que indica que o LightGBM não é sensível a esses parâmetros neste problema. Os valores fixos usados desde o início eram adequados.
* **Prever a tendência diretamente é melhor para a tendência.** O classificador é o único modelo significativamente melhor que o LightGBM atual no acerto balanceado (de 3 a 4 pontos percentuais), e detecta muito mais subidas (54,8% contra 41,6% com 4 semanas). Em troca, dá mais alarmes falsos (56,9% dos alarmes de subida se confirmam, contra 65,1%), erra o sentido com mais frequência (8,9% contra 5,0%) e não produz número de casos.
* **O modelo por quantis é o melhor para o número de casos.** Tem o menor erro em casos e o menor sentido oposto, com acerto de tendência pouco abaixo do LightGBM atual (diferença de 0,5 a 1,3 ponto, estatisticamente significativa, mas pequena). Além disso, fornece um intervalo de previsão bem calibrado.
* **Troca entre sensibilidade e precisão.** Não existe um modelo melhor em tudo. O classificador e a binomial negativa são mais "sensíveis" (detectam mais subidas, com mais alarmes falsos); os modelos LightGBM de regressão são mais "precisos" (menos alarmes, mais confiáveis). A escolha depende do custo relativo de deixar passar uma subida e de dar um alarme falso na vigilância.

### Decisão

<!-- DECISAO_MODELO: a definir pelo grupo -->
A escolha do modelo usado no painel está em aberto. Pelo critério definido antes do experimento (acerto balanceado na validação cruzada), o LightGBM classificador é o melhor para a tendência. A opção em discussão é usar o classificador para indicar a tendência e o LightGBM por quantis para mostrar o número de casos com intervalo.

### Limitações

* Todos os modelos usaram as mesmas variáveis, sem clima (seção 14 mostrou que o clima ajuda um pouco só em 4 semanas); o efeito do clima em cada modelo não foi testado.
* O retreino a cada 3 meses (em vez de mensal) deixa todos os modelos um pouco em desvantagem em relação ao uso real, de forma igual para todos.
* A binomial negativa e a regressão linear usaram configurações simples, sem termos de interação nem ajuste; versões mais elaboradas poderiam ter desempenho melhor.
* Modelos mais sofisticados (redes neurais para séries temporais, modelos hierárquicos bayesianos) ficaram fora do escopo.
* O acerto balanceado dá o mesmo peso às três classes. Se a vigilância considerar deixar passar uma subida muito pior que um alarme falso, outra métrica poderia mudar a escolha.

### Como reproduzir

```bash
python -m src.experimento_modelos                  # tudo (cerca de 45 minutos)
python -m src.experimento_modelos --reajustar      # refaz a busca de hiperparâmetros
python -m src.experimento_modelos --modelos lightgbm_classificador,lightgbm_quantis
```


<a id="s17"></a>
## 17. O melhor modelo contra a sinalização do Rt do InfoDengue

### Contexto e pergunta

O Rt foi retirado do modelo na [seção 9](#s9) e, por decisão do grupo, **não é usado em nenhum modelo do projeto**; aparece apenas como referência de comparação. A comparação da seção 9 foi feita com a base de SP e com o modelo de regressão. Depois da comparação de modelos ([seção 16](#s16)), a pergunta foi refeita com o melhor modelo de tendência e a base atual: **para dizer se os casos vão subir, ficar estáveis ou cair nas próximas 1 a 4 semanas, o nosso modelo é mais útil do que a sinalização que o InfoDengue já publica?**

A comparação faz sentido porque o Rt responde a uma pergunta próxima: Rt acima de 1 indica que a epidemia está crescendo. O InfoDengue também publica o `p_rt1`, a probabilidade de o Rt ser maior que 1. Os dois são estimativas da transmissão na semana de partida, disponíveis no mesmo momento que os casos usados pelo modelo.

### O que foi testado

Três formas de transformar o Rt em tendência (`src/modelos/sinal_rt.py`), contra o LightGBM classificador:

| Referência | Regra |
|---|---|
| Regra do Rt | Rt acima de 1,1: sobe; abaixo de 0,9: cai; entre os dois: estável |
| Regra do `p_rt1` | `p_rt1` acima de 0,9: sobe; abaixo de 0,1: cai; entre os dois: estável |
| Classificador só com o Rt | LightGBM classificador treinado só com Rt, `p_rt1` e casos atuais |

As regras usam limiares escolhidos por nós, e o Rt não foi criado para a nossa definição de tendência (20% e 5 casos). Por isso incluímos o classificador treinado só com o Rt: ele aprende, a partir dos dados, a melhor forma de usar o Rt com a mesma técnica do nosso modelo. Ele não é candidato a modelo do projeto, serve só para que a comparação não dependa de limiares arbitrários.

Avaliação idêntica à da seção 16 (validação cruzada por município, 2019 em diante, validação final nos 15 municípios, intervalos de confiança por bootstrap sobre municípios). Script `src/experimento_rt.py`; resultados em `reports/comparacao_rt.csv` e `reports/comparacao_rt_por_municipio.csv`.

### Resultados

**Acerto balanceado da tendência** (de 0 a 1; maior é melhor; o baseline "sempre estável" tira 0,333). Validação cruzada, 100 municípios; entre parênteses, a diferença em relação ao nosso modelo, com o intervalo de confiança de 95%:

| Modelo | 1 semana | 2 semanas | 3 semanas | 4 semanas |
|---|---|---|---|---|
| **LightGBM classificador (nosso modelo)** | **0,419** | **0,554** | **0,605** | **0,623** |
| Classificador só com o Rt | 0,362 (−0,057; −0,062 a −0,052) | 0,464 (−0,090; −0,098 a −0,081) | 0,517 (−0,088; −0,096 a −0,079) | 0,539 (−0,084; −0,092 a −0,076) |
| Regra do `p_rt1` | 0,388 (−0,031; −0,044 a −0,021) | 0,428 (−0,126; −0,139 a −0,113) | 0,440 (−0,165; −0,180 a −0,149) | 0,441 (−0,182; −0,200 a −0,163) |
| Regra do Rt | 0,347 (−0,072; −0,088 a −0,058) | 0,376 (−0,177; −0,192 a −0,161) | 0,386 (−0,219; −0,235 a −0,202) | 0,382 (−0,241; −0,259 a −0,221) |

**Perfil com 4 semanas de antecedência** (validação cruzada; porcentagens: maior é melhor, exceto "sentido oposto", em que menor é melhor):

| Modelo | Acerto | Subidas detectadas | Alarmes de subida corretos | Sentido oposto |
|---|---|---|---|---|
| **LightGBM classificador** | **62,6%** | **54,8%** | **56,9%** | **8,9%** |
| Classificador só com o Rt | 55,6% | 34,5% | 47,0% | 14,2% |
| Regra do `p_rt1` | 46,4% | 35,5% | 44,7% | 10,6% |
| Regra do Rt | 34,9% | 49,9% | 36,3% | 17,8% |

**Validação final (15 municípios):** o resultado se repete. Com 4 semanas, o acerto balanceado é de 0,611 para o nosso modelo, 0,495 para o classificador só com o Rt, 0,449 para a regra do `p_rt1` e 0,403 para a regra do Rt.

### Leitura dos resultados

* **O nosso modelo é melhor que qualquer uso do Rt**, em todos os horizontes, com intervalos de confiança que excluem zero. A vantagem cresce com a antecedência: de 3 a 7 pontos em 1 semana e de 8 a 24 pontos em 4 semanas.
* **Mesmo o melhor uso possível do Rt fica atrás.** O classificador treinado só com o Rt perde de 6 a 9 pontos para o nosso modelo. Isso mostra que a diferença não vem de limiares mal escolhidos nas regras: os casos recentes (nível e variação) contêm mais informação sobre a tendência das próximas semanas do que o Rt.
* **As regras diretas pouco superam o "sempre estável".** A regra do Rt tem acerto balanceado de 0,35 a 0,39, pouco acima de 0,333, e o acerto simples dela (27% a 35%) fica abaixo de dizer sempre "estável". Ela detecta metade das subidas, mas só 21% a 36% dos seus alarmes se confirmam, e aponta o sentido errado em 13% a 18% das semanas. O Rt oscila bastante de uma semana para outra, e cada oscilação vira um alarme.
* **Ressalva:** o Rt mede a transmissão atual e não foi criado para prever a variação dos casos daqui a 1 a 4 semanas com o nosso critério. A conclusão é que, para essa pergunta específica, o nosso modelo é mais útil do que uma leitura direta do Rt, e não que o Rt seja um indicador ruim para o que se propõe.

### Como reproduzir

```bash
python -m src.experimento_modelos     # precisa rodar antes (gera os resultados do classificador)
python -m src.experimento_rt          # cerca de 15 minutos
```
