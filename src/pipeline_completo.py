"""
Refaz, na ordem, tudo o que depende dos dados: pré-processamento, modelos de produção,
análise exploratória, todos os experimentos, a comparação entre fotos dos dados e os
números do relatório (numeros_relatorio.py). É o
comando para atualizar os números do README e do relatório com os dados mais recentes.

Retomada: ao fim de cada passo, grava em reports/pipeline_estado.json o passo, a
identificação dos dados processados (snapshot.id_dados_processados), a data e a duração.
Rodar de novo pula os passos já concluídos com os mesmos dados; se os dados mudarem,
tudo é refeito. O experimento de classificadores também retoma dentro do passo (cache por
unidade). A saída de cada passo fica em reports/logs/<passo>.log.

Duração: várias horas (os experimentos são os passos mais longos).

Uso:
  python -m src.pipeline_completo --baixar     baixa os dados novos (com foto) e refaz tudo
  python -m src.pipeline_completo              usa os dados atuais (ou continua de onde parou)
  python -m src.pipeline_completo --refazer    refaz todos os passos, mesmo os já concluídos
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

from src.snapshot import id_dados_processados

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD = ['ingestion', 'ingestion_clima']
# (módulo em src/, argumentos); a ordem respeita as dependências entre os experimentos
PASSOS = [
    # o mais longo e o mais esperado: primeiro; 6 processos (com 8, a comparação chegou ao limite de memória
    # num computador de 28 GB: Random Forest profundo e LSTM ao mesmo tempo). Não muda os resultados.
    ('experimento_classificadores', ['--processos', '6']),
    ('train', []),
    ('eda', []),
    ('experimento_modelos', ['--reajustar']),
    ('experimento_clima_classificador', []),  # usa comparacao_modelos_por_municipio.csv
    ('experimento_rt', []),                   # idem
    ('experimento_generalizacao', []),
    ('experimento_atraso', []),
    ('experimento_estados', []),             # níveis: dois estados (decisão 16)
    ('experimento_niveis', []),              # níveis: verde, amarelo, vermelho e quadradinhos (decisão 16)
    ('experimento_niveis_robustez', []),     # desmobilização, atraso dos dados e intervalos de confiança (decisão 16)
    ('experimento_casos_atraso', []),        # casos aproximados como no painel (2 semanas de atraso)
    ('exportar_painel', []),                 # modelos de produção e JSON do painel estático (web/public/dados)
]
# Fora do pipeline: experimento_variaveis.py (base de SP) e experimento_clima_semanal.py (base de 63
# municípios) são históricos; os resultados citados em docs/historia_decisoes.md são os dos commits
# originais, e rodá-los com a base atual seria outro experimento.
ARQUIVO_ESTADO = 'reports/pipeline_estado.json'
PASTA_LOGS = 'reports/logs'


def rodar(modulo, argumentos=()):
    os.makedirs(PASTA_LOGS, exist_ok=True)
    log = os.path.join(PASTA_LOGS, f'{modulo}.log')
    logging.info(f"Rodando {modulo} {' '.join(argumentos)} (saída em {log})...")
    inicio = time.time()
    with open(log, 'w', encoding='utf-8') as f:
        retorno = subprocess.run([sys.executable, '-m', f'src.{modulo}', *argumentos], stdout=f,
                                 stderr=subprocess.STDOUT, env={**os.environ, 'PYTHONPATH': '.',
                                                               'PYTHONIOENCODING': 'utf-8'})
    duracao = time.time() - inicio
    if retorno.returncode != 0:
        logging.error(f"{modulo} falhou (código {retorno.returncode}); veja {log}. "
                      "Corrija e rode de novo: os passos concluídos não são refeitos.")
        sys.exit(1)
    logging.info(f"{modulo} concluído em {duracao / 60:.0f} min.")
    return duracao


def ler_estado():
    if not os.path.exists(ARQUIVO_ESTADO):
        return {}
    with open(ARQUIVO_ESTADO, encoding='utf-8') as f:
        return json.load(f)


def gravar_estado(estado):
    with open(ARQUIVO_ESTADO + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    os.replace(ARQUIVO_ESTADO + '.tmp', ARQUIVO_ESTADO)


def run_pipeline(baixar=False, refazer=False):
    if baixar:
        for modulo in DOWNLOAD:
            rodar(modulo)
    rodar('preprocessing')
    id_ = id_dados_processados()
    estado = ler_estado()
    if estado.get('id_dados') != id_:
        estado = {'id_dados': id_, 'passos': {}}
    logging.info(f"Dados processados: {id_}.")

    for modulo, argumentos in PASSOS:
        if modulo in estado['passos'] and not refazer:
            logging.info(f"{modulo}: já concluído com estes dados ({estado['passos'][modulo]['concluido']}).")
            continue
        duracao = rodar(modulo, argumentos)
        estado['passos'][modulo] = {'concluido': datetime.now().isoformat(timespec='seconds'),
                                    'minutos': round(duracao / 60, 1)}
        gravar_estado(estado)

    rodar('revisao_dados')
    rodar('numeros_relatorio')  # depende de train e dos experimentos
    logging.info("Pipeline concluído. Números do README e do relatório podem ser atualizados a partir de reports/.")


if __name__ == "__main__":
    run_pipeline(baixar='--baixar' in sys.argv, refazer='--refazer' in sys.argv)
