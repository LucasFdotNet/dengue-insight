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

1. **Ingestão (`src/ingestion.py`):** Conecta à API pública do InfoDengue (Fiocruz/FGV) via requisições HTTP REST e extrai as séries temporais consolidadas das semanas epidemiológicas.
2. **Pré-processamento (`src/preprocessing.py`):** Realiza limpeza, tratamento de valores faltantes por interpolação e gera defasagens temporais (*lag features* de 1 a 4 semanas) e médias móveis.
3. **Treinamento e Validação (`src/train.py`):** Utiliza algoritmos baseados em Gradient Boosting (**LightGBM**) treinados de forma multi-horizonte (H+1 a H+4 semanas) com divisão temporal cronológica, avaliados por MAE, RMSE e R².
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

* **Decisão:** as últimas `SEMANAS_INSTAVEIS` semanas (hoje, 8) ficam fora do treino e da avaliação, em `src/train.py`.
* **Motivo:** o `casos_est` das semanas recentes é uma estimativa (*nowcast*) que o InfoDengue ainda revisa conforme chegam notificações atrasadas.
* **Detalhes:** o corte é aplicado depois do `dropna`, para que alvos que apontam para semanas instáveis também sejam descartados. O corte fica no treino, e não no pré-processamento, porque o dashboard e as previsões precisam das semanas recentes.
* **Pendente:** o valor 8 é provisório e será medido com os dados das cidades de treino.

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

### Decisões pendentes

* **Variáveis climáticas:** proposta de usar temperatura mínima, média e máxima, precipitação total da semana e umidade relativa média.
* **Modelo único para todas as cidades de treino ou um modelo por cidade.**
* **Tipo de alvo:** casos absolutos (atual) ou variação relativa, `log1p(y[t+h]) - log1p(y[t])`.
* **Validação:** substituir o corte único 80/20 por validação *walk-forward* com janelas anuais.
