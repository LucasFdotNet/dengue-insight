"""
Refaz, na ordem, tudo o que depende dos dados: pré-processamento, modelos de produção,
análise exploratória, todos os experimentos e a comparação entre fotos dos dados. É o
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
    ('train', []),
    ('eda', []),
    ('experimento_modelos', ['--reajustar']),
    ('experimento_clima_classificador', []),  # usa comparacao_modelos_por_municipio.csv
    ('experimento_rt', []),                   # idem
    ('experimento_classificadores', []),
    ('experimento_generalizacao', []),
    ('experimento_atraso', []),
    ('experimento_clima_semanal', []),
    ('experimento_variaveis', []),
]
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
    logging.info("Pipeline concluído. Números do README e do relatório podem ser atualizados a partir de reports/.")


if __name__ == "__main__":
    run_pipeline(baixar='--baixar' in sys.argv, refazer='--refazer' in sys.argv)
