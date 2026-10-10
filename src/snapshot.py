"""
Fotos (snapshots) dos dados brutos.

O InfoDengue revisa as semanas recentes (nowcast e notificações atrasadas) e o ERA5
preliminar é substituído pelo definitivo, então os mesmos dados mudam de uma coleta para
outra. Cada ingestão concluída guarda uma cópia compactada do que foi baixado, para que
seja possível reproduzir resultados antigos e medir quanto os dados mudam ao longo do tempo.

Estrutura:
  data/snapshots/AAAA-MM-DD/infodengue.zip    data/raw/{cidade}_raw.csv
  data/snapshots/AAAA-MM-DD/infodengue.json   manifesto: data da coleta e, por município,
                                              linhas, primeira e última semana e SHA-256
  data/snapshots/AAAA-MM-DD/clima.zip         data/raw/clima/{cidade}_clima.csv
  data/snapshots/AAAA-MM-DD/clima.json

A pasta tem a data da coleta (a modificação mais recente entre os arquivos). Uma nova foto
no mesmo dia substitui a anterior.

Uso (foto manual dos dados atuais; as ingestões fazem isso sozinhas):
  python -m src.snapshot
"""
import hashlib
import json
import logging
import os
import zipfile
from datetime import datetime

import pandas as pd

from src.cidades import CIDADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PASTA_SNAPSHOTS = 'data/snapshots'
FONTES = {
    'infodengue': 'data/raw/{cidade}_raw.csv',
    'clima': 'data/raw/clima/{cidade}_clima.csv',
}


def _sha256(caminho):
    with open(caminho, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def _resumo(caminho):
    df = pd.read_csv(caminho, usecols=['data_iniSE'])
    return {
        'linhas': len(df),
        'primeira_semana': str(df['data_iniSE'].min()),
        'ultima_semana': str(df['data_iniSE'].max()),
        'sha256': _sha256(caminho),
    }


def salvar_foto(fonte):
    """Compacta os arquivos brutos de 'fonte' ('infodengue' ou 'clima') em data/snapshots/<data da coleta>/."""
    arquivos = {cidade: FONTES[fonte].format(cidade=cidade) for cidade in CIDADES}
    ausentes = [c for c, a in arquivos.items() if not os.path.exists(a)]
    if ausentes:
        raise FileNotFoundError(f"Foto de {fonte} não criada; faltam arquivos de: {', '.join(ausentes)}")

    coleta = datetime.fromtimestamp(max(os.path.getmtime(a) for a in arquivos.values()))
    pasta = os.path.join(PASTA_SNAPSHOTS, coleta.strftime('%Y-%m-%d'))
    os.makedirs(pasta, exist_ok=True)

    destino = os.path.join(pasta, f'{fonte}.zip')
    with zipfile.ZipFile(destino + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for caminho in arquivos.values():
            z.write(caminho, arcname=os.path.relpath(caminho, 'data/raw').replace(os.sep, '/'))
    os.replace(destino + '.tmp', destino)

    manifesto = {
        'fonte': fonte,
        'coleta': coleta.isoformat(timespec='seconds'),
        'municipios': {cidade: _resumo(caminho) for cidade, caminho in arquivos.items()},
    }
    with open(os.path.join(pasta, f'{fonte}.json'), 'w', encoding='utf-8') as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=1)

    logging.info(f"Foto de {fonte} salva em {destino} ({os.path.getsize(destino) / 1e6:.1f} MB)")
    return destino


if __name__ == "__main__":
    for fonte in FONTES:
        salvar_foto(fonte)
