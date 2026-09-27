# Roteiro do capítulo de Metodologia

Tópicos em bullets para expandir depois. Números e detalhes de cada item estão em `docs/historia_decisoes.md` (seção indicada entre colchetes) e no `README.md`.

---

## 1. Fontes de dados

- Casos de dengue: API pública do InfoDengue (Fiocruz/FGV), série semanal por município desde 2010 [s1, s2]
- Usamos os casos estimados (*nowcast*) do InfoDengue, que corrigem o atraso das notificações nas semanas recentes [s2]
- Clima: inicialmente o clima fornecido pelo próprio InfoDengue; problemas encontrados [s3]:
  - não tinha chuva
  - de 2010 a 2022, vários municípios compartilhavam a mesma estação meteorológica (temperatura idêntica em Campinas, Cosmópolis e Piracicaba)
  - troca de fonte no meio da série
- Substituído pela reanálise ERA5 (Copernicus), via API Open-Meteo, por coordenada de cada município, agregado por semana epidemiológica [s3]
- Alternativas avaliadas e descartadas: ERA5-Land (sem chuva) e Mosqlimate (exige chave) [s3]
- População: Censo 2022 (IBGE), usada na seleção dos municípios [s13]

## 2. Preparação e qualidade dos dados

- O código herdado tinha erros que tornavam temperatura e Rt constantes e inventava valores quando faltava dado; corrigido com a regra "falhar cedo": dado ausente gera erro, não valor inventado [s0, s1]
- Interpolação só entre valores conhecidos, sem extrapolar as pontas [s1]
- Semanas instáveis: as últimas 10 semanas de cada município ainda estão em revisão pelo InfoDengue (nowcast) e ficam fora do treino e da avaliação; o valor 10 foi medido nos dados (maior número de semanas com o intervalo do nowcast ainda aberto) [s2]
- Semana epidemiológica (domingo a sábado) como unidade de tempo: é como o InfoDengue publica e como a vigilância trabalha [s6]
- Versões de dependências fixadas e ingestão robusta a falhas e limites das APIs, para que o projeto possa ser reproduzido [s1, s11]

## 3. Seleção dos municípios

- Seleção inicial herdada: 3 municípios (Campinas, Cosmópolis e Piracicaba), um modelo por município [s0]
- Primeira ampliação: 19 municípios de SP com mais de 100 mil habitantes (exceção: Cosmópolis, polo de integrante do grupo); 13 de treino (polos dos integrantes e região entre eles) e 6 de validação (outras regiões do estado) [s12]
- Problema percebido: os 13 municípios de treino eram vizinhos, com clima muito parecido; o clima não ajudava o modelo e havia pouca variedade de epidemias [s10]
- Segunda ampliação: 74 municípios, com capitais e segundas maiores cidades de todas as UFs (a mais de 50 km da capital, para evitar a mesma região metropolitana); 63 de treino e 11 de validação [s12]
  - Resultado: treinar com o Brasil todo melhorou a previsão dos próprios municípios de SP (erro de 7% a 10% menor no treino e de 18% a 23% menor na validação) [s12]
- Terceira ampliação: 115 municípios, sendo 100 de treino e 15 de validação [s13]
  - Vagas de treino distribuídas por UF em proporção à população
  - Novos municípios de treino escolhidos pelo histórico de surtos (maior incidência média anual de 2010 a 2025), porque o modelo precisa de exemplos de epidemias
  - Novos municípios de validação escolhidos só por tamanho e região, antes dos de treino, para não carregar o viés da seleção por surtos
- Regra fixa: os municípios de validação nunca entram no treino nem em nenhuma escolha (variáveis, hiperparâmetros, parâmetros) [s1, s13]
- Curva de aprendizado: com 100 municípios, acrescentar mais quase não melhora o modelo (dobrar para 200 reduziria o erro em cerca de 1%) [s14]
- Limitação: viés de seleção dos municípios com surtos [s13]

## 4. Formulação do problema

- Horizontes de previsão: 1, 2, 3 e 4 semanas à frente
- Primeiro objetivo: prever o número de casos
- Problema: o modelo original (LightGBM, um por município, prevendo o número de casos) perdia para a previsão ingênua de repetir os casos atuais; árvores de decisão não conseguem prever valores acima dos vistos no treino, e as epidemias recentes (2024) foram maiores que as anteriores [s0, s4]
- Solução: prever a **variação** relativa dos casos (alvo relativo, em escala logarítmica), e não o número absoluto; municípios de tamanhos diferentes ficam na mesma escala e o modelo pode chegar a valores nunca vistos [s4]
- Modelo único para todos os municípios, em vez de um por município: mais epidemias para aprender e possibilidade de prever municípios que o modelo nunca viu [s4]
- Mudança de foco: prever o número exato de casos tem efetividade limitada, mas os modelos conseguem prever a **tendência** (subida, estabilidade ou queda); para a vigilância, saber que os casos vão subir é a informação mais útil [s8]
- Definição de tendência: subida ou queda quando a variação passa de 20% e de 5 casos; senão, estável [s8]
- Segunda mudança de foco: além de SP, mostrar que o modelo **generaliza** para municípios que não viu [s14]

## 5. Variáveis do modelo

- Casos atuais (em log), variação dos casos em relação a 1, 2, 3 e 4 semanas atrás, semana do ano (sazonalidade) [s4]
- Rt retirado [s9]:
  - o Rt não é uma previsão, mas uma estimativa da transmissão atual produzida por outro modelo (do InfoDengue), com premissas que não controlamos
  - é redundante com a variação dos casos, que o modelo já usa (retirá-lo não mudou o resultado)
  - fora do modelo, permite comparar o modelo com a sinalização do InfoDengue de forma independente
  - decisão do grupo: o Rt não entra em nenhum modelo, só na comparação
- Incidência por 100 mil habitantes retirada (redundante com os casos) [s4]
- Clima [s10, s14, s18]:
  - com os 13 municípios de SP: todas as combinações testadas pioraram a previsão
  - com a base nacional, no modelo de regressão: piora em 1 semana, neutro em 2 e 3, melhora em 4
  - no classificador: o clima das 4 semanas anteriores (temperatura média, chuva e umidade) melhora todos os horizontes, com ganho pequeno
  - o clima da semana atual não é usado, porque o ERA5 chega com cerca de 6 dias de atraso
  - explicação: o efeito do clima leva semanas para virar casos (desenvolvimento do mosquito, incubação, notificação)

## 6. Escolha do modelo

- Justificativa inicial do LightGBM (gradient boosting, árvores de decisão combinadas) [s16]:
  - desempenho forte em dados tabulares, referência em competições de previsão
  - capta relações não lineares sem precisar especificá-las
  - rápido, o que viabilizou centenas de retreinos na validação
  - lida bem com valores faltantes e com variáveis em escalas diferentes
- Comparação de 8 modelos, com as mesmas variáveis e a mesma avaliação [s16]:
  - baseline de persistência, regressão linear, binomial negativa (clássico da epidemiologia), LightGBM com hiperparâmetros fixos, LightGBM com hiperparâmetros ajustados, LightGBM por quantis, LightGBM classificador e ensemble
- Resultados [s16]:
  - modelos de árvore superam os lineares: as relações não lineares importam
  - ajustar hiperparâmetros e combinar modelos não trouxe ganho
  - o classificador (prevê a tendência diretamente) é o melhor para a tendência
  - o LightGBM por quantis é o melhor para o número de casos e dá um intervalo de previsão bem calibrado
- Comparação com o Rt: o classificador supera a regra do Rt, a regra do `p_rt1` e um classificador treinado só com o Rt, em todos os horizontes [s17]
- No contexto do trabalho, o mais importante é alertar uma tendência de alta, para planejamento de ações
- Escolha: o LightGBM classificador com clima dá os alertas de tendência (detecta mais subidas); o LightGBM por quantis mostra o número de casos esperado, com intervalo (implementação no painel pendente)

## 7. Avaliação

- Baseline de persistência ("daqui a H semanas haverá os mesmos casos de hoje") como referência mínima em todas as comparações [s5]
- Validação walk-forward: a cada mês (ou trimestre, nos experimentos mais pesados), o modelo é treinado só com o que já era conhecido e prevê o período seguinte; substituiu o corte único 80/20, que testava só um período [s5]
- Validação cruzada por município: os 100 municípios de treino em 5 grupos; cada grupo é previsto por modelos treinados com os outros 80 [s14]
- Validação final: 15 municípios que nunca entram no treino [s13]
- Intervalos de confiança de 95% por bootstrap sobre municípios (a unidade é o município, não a semana, porque as semanas de um município são correlacionadas) [s14]
- Métricas [README, "Como Ler as Métricas"]:
  - principal: acerto balanceado da tendência (média do acerto em subida, estável e queda; não se deixa enganar pela maioria de semanas estáveis)
  - de apoio: subidas detectadas, alarmes de subida corretos, sentido oposto
  - número de casos: razão entre o erro do modelo e o do baseline
- Separação entre avaliação e produção: o modelo do painel é treinado com toda a série; as previsões passadas mostradas no painel vêm da validação, nunca do modelo de produção [s5, s6]

## 8. Limitações e riscos

- Avaliação pseudoprospectiva: usa os casos já revisados; em tempo real, as semanas recentes estariam incompletas [s5]
- Experimento com dados atrasados (pior caso, sem as 4 semanas mais recentes): o erro aumenta de 1,6 a 2,8 vezes, mas o modelo continua melhor que o baseline [s7]
- Viés de seleção dos municípios com surtos [s13]
- Generalização mais fraca em regiões com poucos municípios parecidos no treino (no Norte, Parauapebas e Manacapuru; Caruaru e Sinop) [README, decisão 6]
- Grade do ERA5 de 0,25°: municípios muito próximos compartilham o mesmo ponto de clima [s3]
- Critério das semanas instáveis mede onde o nowcast é aplicado, não quanto os números mudam [s2]

## 9. Painel (talvez em outro capítulo)

- Semana epidemiológica como unidade, previsões das próximas 4 semanas com tendência, previsões passadas com seletor de período e antecedência, acerto de tendência, filtro por tipo de município [s6]
- Cuidado para não mostrar previsões passadas feitas com o modelo de produção, que já viu essas semanas [s6]

---

## Temas para discutir

- O painel entra na metodologia ou em um capítulo próprio?
- Quanto detalhe dar à evolução (etapas intermediárias) em comparação com o resultado final?
- As limitações entram na metodologia ou na discussão dos resultados?
