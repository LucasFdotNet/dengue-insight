# 🦟 Dengue Insight: Análise Preditiva para Monitoramento de Surtos de Dengue

Solução analítica e preditiva desenvolvida para o **Projeto Integrador em Computação IV (DRP04)** da **Universidade Virtual do Estado de São Paulo (UNIVESP)**.

---

## 📌 Sobre o Projeto

O **Dengue Insight** integra dados epidemiológicos e ambientais provenientes de fontes públicas para identificar padrões históricos e antecipar tendências de evolução dos casos de dengue com antecedência de 1 a 4 semanas.

O objetivo é fornecer uma ferramenta acessível para suporte à tomada de decisão de órgãos públicos e conhecimento da sociedade, permitindo direcionar ações preventivas e alocação de recursos em localidades vulneráveis.

### Municípios Monitorados
* **Campinas - SP** (Código IBGE: `3509502`)
* **Cosmópolis - SP** (Código IBGE: `3512803`)
* **Piracicaba - SP** (Código IBGE: `3538709`)

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