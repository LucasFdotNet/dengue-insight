# Referências do Dengue Insight

Este arquivo lista as fontes que o projeto usa e diz, para cada uma, **o que o projeto tira dela** (um método, um número, uma definição ou um argumento) e **onde isso aparece**: um arquivo em `src/`, uma decisão do [`README.md`](../README.md) ou uma seção de [`historia_decisoes.md`](historia_decisoes.md). Serve para quem quer conferir de onde vem uma escolha e para montar as referências do relatório. Só entram fontes que o projeto de fato usa. As citações seguem um formato ABNT simplificado. Quando um dado da citação não pôde ser conferido, está marcado com "(a confirmar)".

---

## 1. Dados

**CODECO, C. T.; COELHO, F. C.; CRUZ, O. G.; OLIVEIRA, S.; CASTRO, T.; BASTOS, L. S.** Infodengue: a nowcasting system for the surveillance of arboviruses in Brazil. *Revue d'Épidémiologie et de Santé Publique*, v. 66, supl. 5, p. S386, 2018. Disponível em: <https://doi.org/10.1016/j.respe.2018.05.408>.

**CODEÇO, C. T. et al.** InfoDengue: a nowcasting system for the surveillance of dengue fever transmission. *bioRxiv*, 2016. Preprint. Disponível em: <https://doi.org/10.1101/046193>.

* Descrevem o InfoDengue (Fiocruz e FGV), a fonte dos casos semanais por município. O projeto baixa a série pela API `alertcity` (`src/ingestion.py`) e usa os casos estimados com *nowcast* (`casos_est`) como base de todos os modelos.
* O projeto não usa nos modelos nenhum indicador calculado pelo InfoDengue (Rt, `p_rt1`, nível de alerta, `nivel_inc`). Eles servem só de comparação: o Rt e o `p_rt1` contra o classificador de tendência (decisão 8; seções 9 e 17; `src/experimento_rt.py`), e o alerta e o `nivel_inc` contra os estados e níveis do projeto (`src/estados.py`, `src/experimento_estados.py`).

**INFODENGUE.** API de dados do InfoDengue (`alertcity`). Rio de Janeiro: Fiocruz; FGV. Disponível em: <https://info.dengue.mat.br/services/api>. Acesso em: 10 out. 2026.

* Documentação dos parâmetros e das colunas da API (`casos`, `casos_est`, `casos_est_min`, `casos_est_max`, `Rt`, `p_rt1`, `nivel`, `nivel_inc` e outras). O significado das colunas está resumido em [`glossario.md`](glossario.md).

**BASTOS, L. S.; ECONOMOU, T.; GOMES, M. F. C.; VILLELA, D. A. M. et al.** A modelling approach for correcting reporting delays in disease surveillance data. *Statistics in Medicine*, v. 38, n. 22, p. 4363-4377, 2019. Disponível em: <https://doi.org/10.1002/sim.8303>.

* Explica o *nowcasting*: estimar quantos casos uma semana recente ainda vai receber quando as notificações atrasadas chegarem. É o motivo de descartar as 10 semanas mais recentes do treino e da avaliação (`SEMANAS_INSTAVEIS` em `src/train.py`; decisão 3; seção 2) e de as previsões partirem da última semana completa nos municípios sem *nowcast* (`src/predict.py`).

**HERSBACH, H. et al.** The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, v. 146, n. 730, p. 1999-2049, 2020. Disponível em: <https://doi.org/10.1002/qj.3803>.

* Descreve o ERA5, a reanálise do Copernicus/ECMWF: grade de 0,25°, mesmo método para toda a série, com chuva. É a fonte da temperatura, da chuva e da umidade do projeto, no lugar do clima do InfoDengue (decisão 4; seção 3). Também explica uma limitação: municípios vizinhos caem no mesmo ponto da grade.

**OPEN-METEO.** Historical Weather API. 2026. Disponível em: <https://open-meteo.com/en/docs/historical-weather-api>. Acesso em: 7 out. 2026.

* Serviço usado para baixar o ERA5 por latitude e longitude, sem chave de acesso (`models=era5`; `src/ingestion_clima.py` e `src/http_utils.py`; decisão 4). A atribuição exigida dos dados é registrada no README: ERA5 do Copernicus Climate Change Service, licença CC BY 4.0, acesso via Open-Meteo.

**IBGE.** Censo Demográfico 2022. Tabela 4709: população residente, variação absoluta de população residente e taxa de crescimento geométrico. Rio de Janeiro: IBGE, 2023. Disponível em: <https://sidra.ibge.gov.br/tabela/4709>. Acesso em: 10 out. 2026.

* População de cada município em `data/config/cidades.csv` (`src/cidades.py`; decisão 1). Usada para escolher os municípios (mais de 100 mil habitantes; vagas por UF em proporção à população; incidência por 100 mil habitantes).

**BRASIL. Ministério da Saúde.** Painel de Monitoramento das Arboviroses. Brasília, DF: Ministério da Saúde, 2024. Disponível em: <https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue/painel-de-monitoramento>. Acesso em: 18 set. 2026.

* Números nacionais da epidemia de 2024 (mais de 6 milhões de casos prováveis e mais de 5 mil óbitos), usados na introdução do relatório final para mostrar o tamanho do problema.

---

## 2. Vigilância e limiares epidêmicos

**BRASIL. Ministério da Saúde. Secretaria de Vigilância em Saúde e Ambiente. Departamento de Doenças Transmissíveis.** Plano de contingência nacional para dengue, chikungunya e Zika. Brasília, DF: Ministério da Saúde, 2025. 102 p. Disponível em: <https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/guias-e-manuais/2025/plano-de-contingencia-nacional-para-dengue-chikungunya-e-zika.pdf>. Acesso em: 10 out. 2026.

* **Diagrama de controle (canal endêmico)**, seção 5 (pp. 21-23): para cada semana epidemiológica, a mediana dos casos prováveis dos últimos cinco anos do município; o primeiro quartil (Q1) é o limite inferior e o terceiro quartil (Q3) o limite superior do canal. A curva do ano atual (incidência ou *nowcasting*) é comparada com esse canal.
* **Estágios** (Quadro 1, pp. 25-26, e anexo do plano municipal, pp. 92-99): **mobilização**, casos ou *nowcasting* acima da mediana e abaixo do Q3 por quatro semanas consecutivas (p. 92); **alerta**, acima do Q3 por pelo menos quatro semanas (p. 96); **desmobilização**, quando a curva volta ao canal endêmico ou cai de forma sustentada por mais de quatro semanas (p. 52). O plano também indica os relatórios e limiares do InfoDengue como apoio (pp. 23 e 90).
* **O que o plano não define:** se os anos epidêmicos entram ou saem dos cinco anos; como calcular o quartil; se o canal usa contagem ou taxa (o texto fala em casos prováveis e a figura em coeficiente de incidência); e o que fazer em municípios com muitas semanas zeradas. O projeto faz essas escolhas e as registra em `src/estados.py`.
* É a referência para a definição dos níveis verde, amarelo e vermelho e do alerta de mobilização (`src/estados.py`, `src/experimento_estados.py`, `src/experimento_niveis.py`). Essa definição está em desenvolvimento (decisão 16 do README e seção 22 da história, em elaboração).

**ALERTADENGUE.** AlertTools: funções do InfoDengue em R. Arquivos `R/infodengue_apply_mem.R` e `R/alert_functions.R`. GitHub. Disponível em: <https://github.com/AlertaDengue/AlertTools>. Acesso em: 10 out. 2026.

**ALERTADENGUE.** AlertaDengueAnalise: parametrização e análises do InfoDengue. Arquivo `parameters/update_parameters.R`. GitHub. Disponível em: <https://github.com/AlertaDengue/AlertaDengueAnalise>. Acesso em: 10 out. 2026.

* O código-fonte mostra como o InfoDengue calcula os limiares de cada município. O MEM (método abaixo) é aplicado à série histórica de incidência e dá o limiar pré-epidêmico e o epidêmico. Há mínimos de 5 casos (pré-epidêmico) e 10 casos (epidêmico). Quando o MEM falha ou fica abaixo do mínimo, o limiar vira um percentil dos casos semanais (10% para o pré-epidêmico, 95% para o epidêmico), respeitando os mesmos mínimos; em `update_parameters.R`, municípios sem MEM recebem direto os mínimos.
* Também define o `nivel_inc`: 0 abaixo do limiar pré-epidêmico, 1 entre os dois limiares e 2 acima do epidêmico, comparando a incidência estimada por 100 mil habitantes (`p_inc100k`).
* O projeto usa essa descrição só para comparar e validar os seus limiares, sem usar o `nivel_inc` nos modelos. Exemplo: com o percentil 90%, 88% das semanas de nível alto do projeto estão no `nivel_inc = 2` (`src/estados.py`).

**VEGA, T.; LOZANO, J. E.; MEERHOFF, T.; SNACKEN, R.; MOTT, J.; ORTIZ DE LEJARAZU, R. et al.** Influenza surveillance in Europe: establishing epidemic thresholds by the Moving Epidemic Method. *Influenza and Other Respiratory Viruses*, v. 7, n. 4, p. 546-558, 2013. Disponível em: <https://doi.org/10.1111/j.1750-2659.2012.00422.x>.

**VEGA, T.; LOZANO, J. E.; MEERHOFF, T.; SNACKEN, R.; BEAUTÉ, J.; JORGENSEN, P. et al.** Influenza surveillance in Europe: comparing intensity levels calculated using the moving epidemic method. *Influenza and Other Respiratory Viruses*, v. 9, n. 5, p. 234-246, 2015. Disponível em: <https://doi.org/10.1111/irv.12330>.

* Artigos que criaram o MEM (*Moving Epidemic Method*): o de 2013 define os limiares epidêmicos (início e fim da temporada) e o de 2015, os níveis de intensidade. O projeto não aplica o MEM; os artigos entram só como referência do método que o InfoDengue usa para os limiares com que o projeto se compara (`src/estados.py`).

**GOUVEIA, A. S.; GOMES, M. F. C.; ALMEIDA, I. F.; LANA, R. M.; BASTOS, L. S. et al.** Unraveling regional variability in Dengue outbreaks in Brazil: leveraging the Moving Epidemics Method (MEM) and climate data to optimize vector control strategies. *PLOS Neglected Tropical Diseases*, v. 19, n. 6, e0013175, 2025. Disponível em: <https://doi.org/10.1371/journal.pntd.0013175>. Preprint: <https://doi.org/10.1101/2025.05.09.25327307>.

* Aplica o MEM à dengue no Brasil (120 macrorregiões de saúde, 2010 a 2023), com início, duração e intensidade das epidemias, e agrupa as regiões pelo clima. Para o projeto, mostra que o MEM é usado na dengue brasileira e que a época e a intensidade das epidemias variam muito entre regiões, o que apoia limiares próprios por município (`src/estados.py`).

---

## 3. Clima e dengue

**BARCELLOS, C.; LOWE, R.** Expansion of the dengue transmission area in Brazil: the role of climate and cities. *Tropical Medicine & International Health*, v. 19, n. 2, p. 159-168, 2014. Disponível em: <https://doi.org/10.1111/tmi.12227>.

* Explica como o clima age sobre o mosquito e o vírus: temperaturas entre 25 °C e 30 °C encurtam a fase larval e o período de incubação no vetor, e a chuva cria criadouros. É a justificativa para testar temperatura, chuva e umidade como variáveis (decisão 9; seções 10, 14 e 18; `src/experimento_clima_classificador.py`).

**LOWE, R. et al.** Combined effects of hydrometeorological hazards and urbanisation on dengue risk in Brazil: a spatiotemporal modelling study. *The Lancet Planetary Health*, v. 5, n. 4, p. e209-e219, 2021. Disponível em: <https://doi.org/10.1016/S2542-5196(20)30292-8>.

* Dois argumentos: sistemas de alerta precoce com clima e casos ajudam a reduzir óbitos (justificativa do projeto no relatório) e o efeito do clima sobre os casos aparece com defasagem de semanas. Por isso o classificador recebe o clima das semanas S-1 a S-4 (decisão 9) e a análise exploratória mede a correlação com o clima de 0 a 16 semanas antes (`src/numeros_relatorio.py`, `src/eda.py`).

**FORATTINI, O. P.** *Culicidologia médica: identificação, biologia, epidemiologia*. v. 2. São Paulo: Editora da Universidade de São Paulo, 2002.

* Descrição do *Aedes aegypti* como vetor urbano adaptado ao ambiente humano, cuja população depende do microclima. Usada na fundamentação teórica do relatório final.

---

## 4. Modelos e métodos de aprendizado de máquina

**KE, G. et al.** LightGBM: a highly efficient gradient boosting decision tree. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS 30 (NeurIPS 2017). Red Hook: Curran Associates, 2017. p. 3146-3154. Disponível em: <https://proceedings.neurips.cc/paper_files/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf>.

* O algoritmo dos dois modelos em produção: o classificador de tendência com clima e o modelo por quantis (`src/modelos/lightgbm_classificador_clima.py`, `src/modelos/lightgbm_quantis.py`, `src/train.py`; decisão 11). Também é a base dos modelos de estado e de nível (`src/modelos/estado_lightgbm.py`, `src/modelos/nivel_lightgbm.py`).

**CHEN, T.; GUESTRIN, C.** XGBoost: a scalable tree boosting system. In: ACM SIGKDD INTERNATIONAL CONFERENCE ON KNOWLEDGE DISCOVERY AND DATA MINING, 22., 2016, San Francisco. *Proceedings...* New York: ACM, 2016. p. 785-794. Disponível em: <https://doi.org/10.1145/2939672.2939785>.

* Outro *boosting* de árvores, comparado para saber se o resultado dependia da biblioteca. Empatou com o LightGBM (`src/modelos/xgboost_classificador.py`, `src/experimento_classificadores.py`; decisão 15; seção 21).

**BREIMAN, L.** Random forests. *Machine Learning*, v. 45, n. 1, p. 5-32, 2001. Disponível em: <https://doi.org/10.1023/A:1010933404324>.

* Árvores independentes combinadas por votação (*bagging*). Comparado ao LightGBM e ficou um pouco abaixo nos horizontes curtos (`src/modelos/random_forest_classificador.py`; decisão 15; seção 21).

**HOCHREITER, S.; SCHMIDHUBER, J.** Long short-term memory. *Neural Computation*, v. 9, n. 8, p. 1735-1780, 1997. Disponível em: <https://doi.org/10.1162/neco.1997.9.8.1735>.

* A rede LSTM, que lê a sequência das últimas 12 semanas de casos e clima. Comparada ao LightGBM e não o superou (`src/modelos/lstm_classificador.py`; decisão 15; seção 21).

**MUSSUMECI, E.; CODEÇO COELHO, F.** Large-scale multivariate forecasting models for Dengue - LSTM versus random forest regression. *Spatial and Spatio-temporal Epidemiology*, v. 35, 100372, 2020. Disponível em: <https://doi.org/10.1016/j.sste.2020.100372>. Preprint: <https://doi.org/10.1101/2020.01.23.20018556>.

* Compara LSTM, Random Forest e Lasso para prever a dengue semanal em 790 municípios brasileiros; a LSTM teve o menor erro. Foi o que motivou testar LSTM e Random Forest no projeto (`src/experimento_classificadores.py`; decisão 15; seção 21). No nosso problema (tendência em 1 a 4 semanas, com as variáveis do projeto), a LSTM não superou o LightGBM.

**GRINSZTAJN, L.; OYALLON, E.; VAROQUAUX, G.** Why do tree-based models still outperform deep learning on typical tabular data? In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS 35 (NeurIPS 2022), Datasets and Benchmarks Track. 2022. Disponível em: <https://proceedings.neurips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf>. Versão arXiv: <https://arxiv.org/abs/2207.08815>.

* Mostra, em 45 conjuntos de dados, que modelos de árvores continuam melhores que redes neurais em dados tabulares de tamanho médio. Apoia a leitura de que MLP e LSTM não superarem o LightGBM é o esperado, e não falha de ajuste (decisão 15; seção 21).

**KOENKER, R.; BASSETT, G.** Regression quantiles. *Econometrica*, v. 46, n. 1, p. 33-50, 1978. Disponível em: <https://doi.org/10.2307/1913643>.

* A regressão por quantis: prever os quantis de 10%, 50% e 90% em vez de um valor só, o que dá a faixa de 80% do número de casos no painel (`src/modelos/lightgbm_quantis.py`; decisão 11; seção 16).

**HILBE, J. M.** *Negative binomial regression*. 2. ed. Cambridge: Cambridge University Press, 2011.

* A binomial negativa como modelo clássico da epidemiologia para contagens com variância maior que a média. Entrou na comparação de modelos como referência linear e ficou bem abaixo dos modelos de árvores (`src/modelos/binomial_negativa.py`; decisão 11; seção 16).

---

## 5. Avaliação

**HYNDMAN, R. J.; ATHANASOPOULOS, G.** *Forecasting: principles and practice*. 2. ed. Melbourne: OTexts, 2018. Disponível em: <https://otexts.com/fpp2/>.

* Duas ideias: o baseline de persistência (repetir o valor atual), que todo modelo precisa superar, e a validação *walk-forward* (origem móvel), em que o modelo só treina com o passado (`src/modelos/baseline_persistencia.py`, `src/train.py`, `src/avaliacao.py`; decisão 6; seção 5).

**ROBERTS, D. R. et al.** Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, v. 40, n. 8, p. 913-929, 2017. Disponível em: <https://doi.org/10.1111/ecog.02881>.

* Avaliar em locais que também estão no treino superestima o desempenho; a validação deve deixar grupos inteiros de fora. Base da validação cruzada por município (5 grupos de 20) e dos 15 municípios de validação (`src/experimento_generalizacao.py`; decisões 6 e 10; seção 14).

**BRODERSEN, K. H.; ONG, C. S.; STEPHAN, K. E.; BUHMANN, J. M.** The balanced accuracy and its posterior distribution. In: INTERNATIONAL CONFERENCE ON PATTERN RECOGNITION, 20., 2010, Istambul. *Proceedings...* Los Alamitos: IEEE, 2010. p. 3121-3124. Disponível em: <https://doi.org/10.1109/ICPR.2010.764>.

* O acerto balanceado (média do acerto em cada classe), métrica principal da tendência. Corrige o viés de prever sempre "estável": um classificador que escolhe sempre a mesma classe tira 1/3 (`src/avaliacao.py`; decisões 7 e 11; seção 16).

**EFRON, B.; TIBSHIRANI, R. J.** *An introduction to the bootstrap*. New York: Chapman & Hall, 1993.

* O *bootstrap*: refazer o cálculo em amostras sorteadas com reposição para obter intervalos de confiança. O projeto sorteia municípios, e não semanas, 2.000 vezes, com sorteio pareado nas comparações entre modelos (`src/experimento_generalizacao.py`, `src/experimento_modelos.py`, `src/experimento_classificadores.py`; decisão 6; seção 14).

**BUEHLER, J. W.; HOPKINS, R. S.; OVERHAGE, J. M.; SOSIN, D. M.; TONG, V.** Framework for evaluating public health surveillance systems for early detection of outbreaks: recommendations from the CDC Working Group. *MMWR Recommendations and Reports*, v. 53, n. RR-5, p. 1-11, 2004. Disponível em: <https://www.cdc.gov/mmwr/preview/mmwrhtml/rr5305a1.htm>.

* Base para avaliar o alerta por episódio, e não por semana: sensibilidade (quantas epidemias foram avisadas), antecedência (*timeliness*, quantas semanas antes do início) e valor preditivo dos alarmes (quantos alarmes se confirmaram) (`src/experimento_estados.py`, `src/experimento_niveis.py`).

---

## 6. Método de trabalho e visualização

**CHAPMAN, P. et al.** *CRISP-DM 1.0: step-by-step data mining guide*. Chicago: SPSS Inc., 2000.

* O ciclo CRISP-DM (entender o problema, preparar os dados, modelar, avaliar), combinado ao Design Thinking. Cada volta do ciclo gerou uma decisão registrada em [`historia_decisoes.md`](historia_decisoes.md).

**FEW, S.** *Information dashboard design: displaying data for at-a-glance monitoring*. 2. ed. Burlingame: Analytics Press, 2019 (a confirmar: a 2.ª edição costuma ser datada de 2013).

**TUFTE, E. R.** *The visual display of quantitative information*. 2. ed. Cheshire: Graphics Press, 2001.

* Princípios de painéis e gráficos que reduzem a carga de leitura. Orientam o desenho do painel (`app.py` e `painel/`; decisão 13).

**STREAMLIT.** The fastest way to build and share data apps. 2026. Disponível em: <https://streamlit.io>. Acesso em: 18 set. 2026.

**PLOTLY TECHNOLOGIES INC.** Collaborative data science. Montreal, QC: Plotly Technologies Inc., 2015. Disponível em: <https://plot.ly>. Acesso em: 18 set. 2026.

* Ferramentas do painel web (Streamlit) e dos gráficos interativos (Plotly) (`app.py` e `painel/`; decisão 13).

---

## Pendências

* **Limiar de 300 casos por 100 mil habitantes.** O README (decisão 1) e o relatório final citam esse valor como "incidência alta" pela classificação do Ministério da Saúde, mas o projeto ainda não registrou o documento de origem. Falta localizar a publicação (a confirmar) antes de citá-la.
