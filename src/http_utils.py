"""
Requisições HTTP com novas tentativas, para que a ingestão rode sem supervisão.

Trata:
  - 429 (limite de requisições): espera o tempo indicado pelo servidor (cabeçalho
    Retry-After) ou, na Open-Meteo, o tempo da janela do limite atingido (minuto ou hora);
  - erros temporários (5xx, timeout, falha de conexão): espera crescente entre tentativas.

O limite diário da Open-Meteo não é esperado (seriam horas): a função lança
LimiteDiarioAtingido, e a ingestão para com uma mensagem para rodar de novo no dia
seguinte, mantendo o que já foi salvo.
"""
import logging
import time

import requests

TENTATIVAS = 6
ESPERA_ERRO_TEMPORARIO = 10  # segundos; dobra a cada tentativa
ESPERA_LIMITE_MINUTO = 65
ESPERA_LIMITE_HORA = 3600


class LimiteDiarioAtingido(Exception):
    pass


def _espera_para_429(response):
    retry_after = response.headers.get('Retry-After')
    if retry_after and retry_after.isdigit():
        return int(retry_after)
    try:
        motivo = str(response.json().get('reason', '')).lower()
    except ValueError:
        motivo = response.text.lower()
    if 'daily' in motivo:
        raise LimiteDiarioAtingido(motivo)
    if 'hourly' in motivo:
        return ESPERA_LIMITE_HORA
    return ESPERA_LIMITE_MINUTO


def get_com_retentativas(url, params, timeout=120, descricao=''):
    """requests.get com novas tentativas; devolve a resposta ou lança o último erro."""
    for tentativa in range(1, TENTATIVAS + 1):
        ultima = tentativa == TENTATIVAS
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            if ultima:
                raise
            espera = ESPERA_ERRO_TEMPORARIO * 2 ** (tentativa - 1)
            logging.warning(f"{descricao}: {type(e).__name__}; nova tentativa em {espera}s ({tentativa}/{TENTATIVAS - 1})")
            time.sleep(espera)
            continue

        if response.status_code == 429 and not ultima:
            espera = _espera_para_429(response)
            logging.warning(f"{descricao}: limite de requisições atingido; nova tentativa em {espera}s "
                            f"({tentativa}/{TENTATIVAS - 1})")
            time.sleep(espera)
            continue
        if response.status_code >= 500 and not ultima:
            espera = ESPERA_ERRO_TEMPORARIO * 2 ** (tentativa - 1)
            logging.warning(f"{descricao}: erro {response.status_code} no servidor; nova tentativa em {espera}s "
                            f"({tentativa}/{TENTATIVAS - 1})")
            time.sleep(espera)
            continue
        if response.status_code == 429:
            _espera_para_429(response)  # lança LimiteDiarioAtingido, se for o caso
        response.raise_for_status()
        return response
