from datetime import date, timedelta

from .models import BloqueioAgenda


def calcular_pascoa(ano):
    """
    Calcula a data da Páscoa para o ano informado.
    Algoritmo de Meeus/Jones/Butcher.
    """

    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (
        19 * a
        + b
        - d
        - g
        + 15
    ) % 30
    i = c // 4
    k = c % 4
    l = (
        32
        + 2 * e
        + 2 * i
        - h
        - k
    ) % 7
    m = (
        a
        + 11 * h
        + 22 * l
    ) // 451

    mes = (
        h
        + l
        - 7 * m
        + 114
    ) // 31

    dia = (
        (h + l - 7 * m + 114) % 31
    ) + 1

    return date(ano, mes, dia)


def feriados_nacionais(ano):
    """
    Retorna os feriados nacionais do Brasil
    para o ano informado.

    Não inclui pontos facultativos.
    """

    pascoa = calcular_pascoa(ano)

    sexta_feira_paixao = (
        pascoa - timedelta(days=2)
    )

    return [
        {
            "data": date(ano, 1, 1),
            "descricao": "Confraternização Universal",
        },
        {
            "data": sexta_feira_paixao,
            "descricao": "Paixão de Cristo",
        },
        {
            "data": date(ano, 4, 21),
            "descricao": "Tiradentes",
        },
        {
            "data": date(ano, 5, 1),
            "descricao": "Dia Mundial do Trabalho",
        },
        {
            "data": date(ano, 9, 7),
            "descricao": "Independência do Brasil",
        },
        {
            "data": date(ano, 10, 12),
            "descricao": "Nossa Senhora Aparecida",
        },
        {
            "data": date(ano, 11, 2),
            "descricao": "Finados",
        },
        {
            "data": date(ano, 11, 15),
            "descricao": "Proclamação da República",
        },
        {
            "data": date(ano, 11, 20),
            "descricao": (
                "Dia Nacional de Zumbi e da "
                "Consciência Negra"
            ),
        },
        {
            "data": date(ano, 12, 25),
            "descricao": "Natal",
        },
    ]


def importar_feriados_nacionais(ano):
    """
    Importa os feriados nacionais para o
    BloqueioAgenda.

    Não cria registros duplicados.
    """

    criados = 0
    existentes = 0

    for feriado in feriados_nacionais(ano):

        chave = (
            f"nacional-{ano}-"
            f"{feriado['data'].strftime('%m-%d')}"
        )

        bloqueio = (
            BloqueioAgenda.objects
            .filter(chave_feriado=chave)
            .first()
        )

        if bloqueio:
            existentes += 1
            continue

        BloqueioAgenda.objects.create(
            tipo="feriado",
            origem="nacional",
            chave_feriado=chave,
            data_inicio=feriado["data"],
            data_fim=feriado["data"],
            hora_inicio=None,
            hora_fim=None,
            profissional=None,
            descricao=feriado["descricao"],
            ativo=True,
        )

        criados += 1

    return {
        "criados": criados,
        "existentes": existentes,
    }