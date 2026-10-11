## Glossário

**Acerto balanceado.** Média do acerto em cada uma das três situações (subiu, ficou estável, caiu), calculado separadamente. Vai de 0 a 1; quanto maior, melhor. Dizer sempre "estável" tira 0,333. É a métrica principal do projeto porque não se deixa enganar pela maioria de semanas estáveis.

**Alarmes de subida corretos.** Das vezes em que o modelo previu subida, em quantas os casos realmente subiram. Mede a confiabilidade dos alertas.

**Alerta de mobilização.** Aviso de que o município deve entrar no nível vermelho nas próximas semanas. Acende quando a chance de vermelho em alguma das próximas 4 semanas passa de um ponto de corte escolhido com os dados do passado, de forma que pelo menos metade dos alarmes se confirme. Diferente do nível (o estado da semana), o alerta é uma previsão.

**Alvo relativo.** O que o modelo de casos aprende a prever: a variação dos casos em escala logarítmica, `log(1 + casos daqui a H semanas) − log(1 + casos hoje)`, e não o número de casos. Deixa municípios de tamanhos diferentes na mesma escala e permite prever valores maiores que os já vistos.

**Antecedência (horizonte).** Quantas semanas à frente a previsão olha: de 1 a 4 semanas. Há um modelo para cada antecedência.

**Baseline de persistência.** A previsão mais simples possível: "daqui a H semanas haverá o mesmo número de casos de hoje". Na tendência, equivale a dizer sempre "estável". Um modelo só é útil se for melhor que isso.

**Bootstrap e intervalo de confiança de 95%.** Para saber se um resultado pode ser efeito do acaso, sorteamos municípios com reposição 2.000 vezes e recalculamos a métrica. O intervalo de confiança de 95% é a faixa em que ficam 95% desses resultados. Se o intervalo de uma diferença entre dois modelos não inclui zero, a diferença é considerada estatisticamente significativa.

**Canal endêmico (diagrama de controle).** Método do Ministério da Saúde para acompanhar a temporada: para cada semana do ano, a mediana e os quartis dos casos da mesma semana nos 5 anos anteriores. Mostra se a semana está acima do esperado para a época. Foi testado para definir os níveis e descartado, porque, com o aumento da dengue nos últimos anos, muitos municípios ficaram acima do esperado por anos seguidos.

**Casos estimados.** Estimativa do InfoDengue de quantos casos uma semana terá quando todas as notificações chegarem (ver *nowcast*). É o número usado pelo projeto. Nas semanas antigas, é igual aos casos notificados.

**Casos notificados.** Casos de dengue já registrados no sistema de vigilância para uma semana. Nas semanas recentes, estão incompletos, porque as notificações chegam com atraso.

**Classificador.** Modelo que prevê uma categoria (aqui: sobe, estável ou cai) em vez de um número. O LightGBM classificador é o modelo de tendência do painel.

**Decisão balanceada (regra de decisão).** Forma de transformar as probabilidades de um classificador em uma tendência. A regra normal escolhe a tendência mais provável; como a maioria das semanas é estável, ela quase sempre escolhe "estável" com 1 semana de antecedência. A decisão balanceada compara cada probabilidade com a frequência daquela tendência no treino: uma chance de subida de 30%, quando só 17% das semanas sobem, conta mais que 60% de "estável", quando 67% das semanas são estáveis. Detecta muito mais subidas, mas com mais alarmes que não se confirmam. Não muda o modelo, só a regra aplicada às probabilidades.

**Episódio (epidemia).** Sequência de pelo menos 2 semanas seguidas no nível vermelho (interrupções de 1 semana não separam o episódio). É a unidade usada para avaliar o alerta: quantas epidemias foram avisadas antes de começar e com quanta antecedência.

**ERA5.** Reanálise climática do Copernicus (serviço europeu): uma reconstrução do clima passado, hora a hora, em uma grade de 0,25° (cerca de 28 km) que cobre todo o planeta, a partir de observações e modelos meteorológicos. O projeto usa temperatura, chuva e umidade do ERA5, obtidas pela API Open-Meteo.

**Faixa de 80% (intervalo de previsão).** Faixa "entre X e Y casos" do modelo por quantis. Se o modelo estiver bem calibrado, o valor real cai dentro dela em cerca de 80% das semanas; na avaliação, isso aconteceu em 78% a 82% das semanas.

**Foto dos dados (snapshot).** Cópia compactada dos dados baixados numa data, guardada em `data/snapshots/AAAA-MM-DD/`. Como o InfoDengue revisa as semanas recentes, os mesmos dados mudam de uma coleta para outra; as fotos permitem saber com quais dados cada resultado foi calculado e medir essas revisões.

**Hiperparâmetros.** Configurações de um modelo escolhidas antes do treino, e não aprendidas dos dados: por exemplo, quantas árvores o LightGBM usa ou o tamanho de uma rede neural. O ajuste testa algumas configurações num período separado (2015 a 2018) e escolhe a melhor, sem usar os anos em que os modelos são comparados.

**Incidência.** Casos por 100 mil habitantes. Permite comparar municípios de tamanhos diferentes. O Ministério da Saúde considera alta uma incidência anual de 300 ou mais.

**InfoDengue.** Sistema de alerta de arboviroses da Fiocruz e da FGV, que publica, por município e por semana, os casos de dengue, o *nowcast*, o Rt e níveis de alerta. É a fonte dos dados de casos do projeto.

**LightGBM.** Algoritmo de aprendizado de máquina que combina muitas árvores de decisão pequenas, cada uma corrigindo os erros das anteriores (*gradient boosting*). Funciona bem com dados em tabela e capta relações não lineares.

**Limiar pré-epidêmico e limiar epidêmico.** Os dois valores de casos por semana, calculados para cada município pelo MEM, que separam os níveis: abaixo do pré-epidêmico, verde; acima dele, amarelo (a temporada de transmissão começou); acima do epidêmico, vermelho. São recalculados a cada temporada com as temporadas anteriores.

**Log loss e Brier.** Métricas que avaliam as probabilidades que um classificador dá a cada tendência, e não só a tendência escolhida. Um modelo que dá 80% de chance à tendência que de fato aconteceu é melhor que um que dá 40%, mesmo que os dois tenham escolhido a mesma. Quanto menor, melhor. Não dependem da regra de decisão.

**LSTM.** Tipo de rede neural feito para sequências: lê a série semana a semana (aqui, as 12 últimas semanas de casos e clima) e aprende sozinho quais semanas passadas importam. Foi comparado com o LightGBM e não o superou.

**MEM (*Moving Epidemic Method*).** Método estatístico para calcular, com o histórico de cada local, os limiares que indicam o início de uma epidemia e a sua intensidade. Usado pelo InfoDengue e adotado pelo projeto para definir os níveis verde, amarelo e vermelho.

**MLP (perceptron multicamadas).** Rede neural "comum", com camadas de neurônios ligadas em sequência, que recebe as mesmas variáveis do LightGBM. Foi comparada com o LightGBM e não o superou.

**Município de treino.** Um dos 100 municípios cujos dados são usados para treinar os modelos.

**Município de validação.** Um dos 15 municípios que nunca entram no treino nem em nenhuma escolha do projeto. Servem para medir se o modelo funciona em municípios que não viu.

**Níveis (verde, amarelo e vermelho).** Faixas de incidência de cada semana, definidas pelos limiares do MEM do município. O modelo do projeto prevê o nível das próximas semanas; o alerta de mobilização avisa a entrada no vermelho.

**Nowcast.** Técnica que estima o **presente** corrigindo o atraso das notificações. Um caso de dengue desta semana pode só entrar no sistema duas ou três semanas depois; por isso, os casos notificados das semanas recentes parecem menores do que são. O *nowcast* do InfoDengue estima quantos casos cada semana recente terá quando todas as notificações chegarem, com uma margem de incerteza (o intervalo do nowcast). Não é uma previsão do futuro: o futuro é o papel do modelo do projeto. Em 39 dos 115 municípios o InfoDengue não publica o nowcast nas semanas recentes; nesses, o painel parte da última semana completa.

**p_rt1.** Probabilidade, calculada pelo InfoDengue, de o Rt ser maior que 1, ou seja, de a epidemia estar crescendo.

**Quantis (modelo por quantis).** Modelo que, em vez de prever um único valor, prevê pontos da distribuição dos resultados possíveis: aqui, o quantil de 10% (limite inferior da faixa), de 50% (mediana, o valor mostrado) e de 90% (limite superior).

**Random Forest.** Algoritmo que treina muitas árvores de decisão independentes, cada uma com uma amostra diferente dos dados, e combina os votos delas (*bagging*). Diferente do LightGBM, em que cada árvore corrige as anteriores. Foi comparado com o LightGBM e não o superou.

**Rede neural.** Modelo formado por camadas de unidades simples ("neurônios") que transformam as entradas; aprende relações complexas ajustando milhares de pesos. O projeto testou dois tipos, MLP e LSTM.

**Rt (número de reprodução).** Estimativa, feita pelo InfoDengue, de quantas pessoas cada infectado está contaminando na semana. Acima de 1, a epidemia cresce; abaixo de 1, diminui. Não é usado nos modelos do projeto, só como comparação.

**Semana epidemiológica.** Semana de domingo a sábado, a unidade de tempo em que a vigilância epidemiológica e o InfoDengue trabalham. Cada ponto dos gráficos é uma semana, identificada pela data do domingo em que começa.

**Semanas instáveis.** As 10 semanas mais recentes de cada município, cujos casos ainda estão sendo revisados. Ficam fora do treino e da avaliação.

**Semente.** Número que fixa a parte aleatória do treino de um modelo (por exemplo, os pesos iniciais de uma rede neural). Treinar com sementes diferentes mostra quanto o resultado varia só por acaso; as redes neurais foram avaliadas com 3 sementes.

**Sentido oposto.** Semanas em que o modelo previu subida e os casos caíram, ou o contrário. Quanto menor, melhor.

**Subidas detectadas.** Das semanas em que os casos realmente subiram, em quantas o modelo previu subida. Mede quantos surtos o modelo consegue antecipar.

**Tendência.** Classificação da variação dos casos entre a semana atual e H semanas depois: **subida** ou **queda** quando a variação passa de 20% e de 5 casos; senão, **estável**.

**Validação cruzada por município.** Forma de avaliar o modelo em municípios que ele não viu: os 100 municípios de treino são divididos em 5 grupos, e cada grupo é previsto por modelos treinados só com os outros 4.

**Viés de seleção.** Distorção causada pela forma de escolher os dados. Aqui: 37 municípios de treino foram escolhidos pelo histórico de surtos, o que pode deixar o modelo mais propenso a prever subidas.

**Walk-forward.** Forma de avaliar que simula o uso real: a cada mês, o modelo é treinado só com o que já era conhecido e prevê as semanas seguintes. Nenhuma informação do futuro entra no modelo que o previu.

**XGBoost.** Algoritmo de *gradient boosting*, da mesma família do LightGBM, com outra implementação. Foi comparado para verificar se o resultado dependia da biblioteca; empatou com o LightGBM.

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
| `comparacao_classificadores*.csv`, `ajuste_classificadores*` | Comparação de XGBoost, Random Forest, redes neurais e regras de decisão com o classificador em produção, e o ajuste de hiperparâmetros de cada modelo |
| `generalizacao_*.csv`, `experimento_*.csv` | Demais experimentos (ver README) |
| `revisao_dados.csv` | Quanto os casos de cada semana mudaram entre duas fotos dos dados |
| `relatorio/*.csv` | Números do relatório final (base de dados, casos por ano, correlação com o clima, métricas do painel, tabela de comparação de modelos) |
| `pipeline_estado.json` | Passos do pipeline completo já concluídos e com quais dados |

### Fotos dos dados (`data/snapshots/AAAA-MM-DD/`)

| Arquivo | Conteúdo |
|---|---|
| `infodengue.zip`, `clima.zip` | Arquivos brutos de casos e de clima de todos os municípios, como foram baixados naquela data |
| `infodengue.json`, `clima.json` | Manifesto: data da coleta e, por município, número de semanas, primeira e última semana e SHA-256 do arquivo |
