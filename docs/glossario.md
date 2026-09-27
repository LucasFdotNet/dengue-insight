## Glossário

**Acerto balanceado.** Média do acerto em cada uma das três situações (subiu, ficou estável, caiu), calculado separadamente. Vai de 0 a 1; quanto maior, melhor. Dizer sempre "estável" tira 0,333. É a métrica principal do projeto porque não se deixa enganar pela maioria de semanas estáveis.

**Alarmes de subida corretos.** Das vezes em que o modelo previu subida, em quantas os casos realmente subiram. Mede a confiabilidade dos alertas.

**Alvo relativo.** O que o modelo de casos aprende a prever: a variação dos casos em escala logarítmica, `log(1 + casos daqui a H semanas) − log(1 + casos hoje)`, e não o número de casos. Deixa municípios de tamanhos diferentes na mesma escala e permite prever valores maiores que os já vistos.

**Antecedência (horizonte).** Quantas semanas à frente a previsão olha: de 1 a 4 semanas. Há um modelo para cada antecedência.

**Baseline de persistência.** A previsão mais simples possível: "daqui a H semanas haverá o mesmo número de casos de hoje". Na tendência, equivale a dizer sempre "estável". Um modelo só é útil se for melhor que isso.

**Bootstrap e intervalo de confiança de 95%.** Para saber se um resultado pode ser efeito do acaso, sorteamos municípios com reposição 2.000 vezes e recalculamos a métrica. O intervalo de confiança de 95% é a faixa em que ficam 95% desses resultados. Se o intervalo de uma diferença entre dois modelos não inclui zero, a diferença é considerada estatisticamente significativa.

**Casos estimados.** Estimativa do InfoDengue de quantos casos uma semana terá quando todas as notificações chegarem (ver *nowcast*). É o número usado pelo projeto. Nas semanas antigas, é igual aos casos notificados.

**Casos notificados.** Casos de dengue já registrados no sistema de vigilância para uma semana. Nas semanas recentes, estão incompletos, porque as notificações chegam com atraso.

**Classificador.** Modelo que prevê uma categoria (aqui: sobe, estável ou cai) em vez de um número. O LightGBM classificador é o modelo de tendência do painel.

**ERA5.** Reanálise climática do Copernicus (serviço europeu): uma reconstrução do clima passado, hora a hora, em uma grade de 0,25° (cerca de 28 km) que cobre todo o planeta, a partir de observações e modelos meteorológicos. O projeto usa temperatura, chuva e umidade do ERA5, obtidas pela API Open-Meteo.

**Faixa de 80% (intervalo de previsão).** Faixa "entre X e Y casos" do modelo por quantis. Se o modelo estiver bem calibrado, o valor real cai dentro dela em cerca de 80% das semanas; na avaliação, isso aconteceu em 78% a 82% das semanas.

**Incidência.** Casos por 100 mil habitantes. Permite comparar municípios de tamanhos diferentes. O Ministério da Saúde considera alta uma incidência anual de 300 ou mais.

**InfoDengue.** Sistema de alerta de arboviroses da Fiocruz e da FGV, que publica, por município e por semana, os casos de dengue, o *nowcast*, o Rt e níveis de alerta. É a fonte dos dados de casos do projeto.

**LightGBM.** Algoritmo de aprendizado de máquina que combina muitas árvores de decisão pequenas, cada uma corrigindo os erros das anteriores (*gradient boosting*). Funciona bem com dados em tabela e capta relações não lineares.

**Município de treino.** Um dos 100 municípios cujos dados são usados para treinar os modelos.

**Município de validação.** Um dos 15 municípios que nunca entram no treino nem em nenhuma escolha do projeto. Servem para medir se o modelo funciona em municípios que não viu.

**Nowcast.** Técnica que estima o **presente** corrigindo o atraso das notificações. Um caso de dengue desta semana pode só entrar no sistema duas ou três semanas depois; por isso, os casos notificados das semanas recentes parecem menores do que são. O *nowcast* do InfoDengue estima quantos casos cada semana recente terá quando todas as notificações chegarem, com uma margem de incerteza (o intervalo do nowcast). Não é uma previsão do futuro: o futuro é o papel do modelo do projeto. Em 39 dos 115 municípios o InfoDengue não publica o nowcast nas semanas recentes; nesses, o painel parte da última semana completa.

**p_rt1.** Probabilidade, calculada pelo InfoDengue, de o Rt ser maior que 1, ou seja, de a epidemia estar crescendo.

**Quantis (modelo por quantis).** Modelo que, em vez de prever um único valor, prevê pontos da distribuição dos resultados possíveis: aqui, o quantil de 10% (limite inferior da faixa), de 50% (mediana, o valor mostrado) e de 90% (limite superior).

**Rt (número de reprodução).** Estimativa, feita pelo InfoDengue, de quantas pessoas cada infectado está contaminando na semana. Acima de 1, a epidemia cresce; abaixo de 1, diminui. Não é usado nos modelos do projeto, só como comparação.

**Semana epidemiológica.** Semana de domingo a sábado, a unidade de tempo em que a vigilância epidemiológica e o InfoDengue trabalham. Cada ponto dos gráficos é uma semana, identificada pela data do domingo em que começa.

**Semanas instáveis.** As 10 semanas mais recentes de cada município, cujos casos ainda estão sendo revisados. Ficam fora do treino e da avaliação.

**Sentido oposto.** Semanas em que o modelo previu subida e os casos caíram, ou o contrário. Quanto menor, melhor.

**Subidas detectadas.** Das semanas em que os casos realmente subiram, em quantas o modelo previu subida. Mede quantos surtos o modelo consegue antecipar.

**Tendência.** Classificação da variação dos casos entre a semana atual e H semanas depois: **subida** ou **queda** quando a variação passa de 20% e de 5 casos; senão, **estável**.

**Validação cruzada por município.** Forma de avaliar o modelo em municípios que ele não viu: os 100 municípios de treino são divididos em 5 grupos, e cada grupo é previsto por modelos treinados só com os outros 4.

**Viés de seleção.** Distorção causada pela forma de escolher os dados. Aqui: 37 municípios de treino foram escolhidos pelo histórico de surtos, o que pode deixar o modelo mais propenso a prever subidas.

**Walk-forward.** Forma de avaliar que simula o uso real: a cada mês, o modelo é treinado só com o que já era conhecido e prevê as semanas seguintes. Nenhuma informação do futuro entra no modelo que o previu.

## Dicionário de dados

### Dados de casos (InfoDengue, `data/raw/<município>_raw.csv`)

| Campo | Descrição |
|---|---|
| `data_iniSE` | Data de início (domingo) da semana epidemiológica |
| `SE` | Semana epidemiológica no formato AAAASS (por exemplo, 202637) |
| `casos` | Casos notificados na semana |
| `casos_est` | Casos estimados (*nowcast*): notificados mais a estimativa dos que ainda vão chegar. **É o número usado pelo projeto** |
| `casos_est_min`, `casos_est_max` | Limites do intervalo do nowcast. Iguais a `casos_est` quando não há nowcast |
| `p_inc100k` | Incidência na semana (casos estimados por 100 mil habitantes) |
| `Rt` (`rt` depois do pré-processamento) | Número de reprodução estimado pelo InfoDengue |
| `p_rt1` | Probabilidade de o Rt ser maior que 1 |
| `nivel` | Nível de alerta do InfoDengue: 1 verde, 2 amarelo, 3 laranja, 4 vermelho |
| `pop` | População usada pelo InfoDengue |
| `receptivo`, `transmissao`, `nivel_inc` | Indicadores do InfoDengue sobre clima favorável ao mosquito, transmissão sustentada e nível de incidência (não usados) |
| `casprov`, `casconf`, `casprov_est*` | Casos prováveis e confirmados, e o nowcast dos prováveis (não usados) |
| `tempmin`, `tempmed`, `tempmax`, `umidmin`, `umidmed`, `umidmax` | Clima do próprio InfoDengue; **descartado** no pré-processamento e substituído pelo ERA5 |
| `Localidade_id`, `id`, `versao_modelo`, `municipio_nome`, `notif_accum_year` | Identificadores e controle do InfoDengue (não usados) |

### Dados de clima (ERA5 via Open-Meteo, `data/raw/clima/<município>_clima.csv`)

Valores diários agregados por semana epidemiológica; só entram semanas com os 7 dias.

| Campo | Descrição |
|---|---|
| `tmin`, `tmed`, `tmax` | Médias semanais das temperaturas mínima, média e máxima diárias (°C) |
| `precipitacao` | Chuva total da semana (mm) |
| `umidade` | Umidade relativa média da semana (%) |

### Variáveis calculadas (`data/processed/<município>_processed.csv`)

| Campo | Descrição | Usado por |
|---|---|---|
| `log_casos` | `log(1 + casos_est)` da semana atual | Os dois modelos |
| `var_log_1` a `var_log_4` | Variação dos casos em relação a 1, 2, 3 e 4 semanas atrás, em escala log (positivo: os casos cresceram) | Os dois modelos |
| `semana_ano` | Semana do ano (1 a 53), para a sazonalidade | Os dois modelos |
| `tmed_s1` a `tmed_s4`, `precipitacao_s1` a `precipitacao_s4`, `umidade_s1` a `umidade_s4` | Clima de cada uma das 4 semanas anteriores à semana atual (S-1 a S-4) | Classificador de tendência |
| `target_h1` a `target_h4` | Casos estimados 1 a 4 semanas depois: o que o modelo tenta prever | Treino e avaliação |
| `casos_est_lag_*`, `tmin_lag_*`, `rt_lag_*`, `casos_est_roll_4`, `tmin_roll_4` | Defasagens e médias móveis da versão anterior do modelo (não usadas hoje) | Nenhum |

### Configuração (`data/config/cidades.csv`)

| Campo | Descrição |
|---|---|
| `chave` | Identificador usado nos nomes de arquivo |
| `geocode` | Código IBGE do município |
| `nome`, `uf` | Nome e estado |
| `lat`, `lon` | Coordenadas da sede, usadas para buscar o clima |
| `papel` | `treino` ou `validacao` |
| `populacao` | População do Censo 2022 (IBGE) |
| `criterio` | Motivo da inclusão do município |

### Resultados (`reports/`)

| Arquivo | Conteúdo |
|---|---|
| `previsoes_walkforward.csv` | Previsões passadas semana a semana (casos, faixa e tendência), usadas pelo painel |
| `metricas_gerais.csv`, `metricas_por_ano.csv`, `metricas_modelos.csv` | Erro do modelo de casos contra o baseline, geral, por ano e por município |
| `metricas_tendencia.csv` | Acerto de tendência do classificador |
| `comparacao_modelos*.csv`, `comparacao_rt*.csv`, `comparacao_clima_classificador*.csv` | Comparação de modelos, com o Rt e do clima no classificador |
| `generalizacao_*.csv`, `experimento_*.csv` | Demais experimentos (ver README) |
