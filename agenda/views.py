from datetime import datetime, date, timedelta
import json

from urllib.parse import quote_plus

from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.contrib.auth.decorators import login_required

from django.contrib import messages

from accounts.permissions import permissao_required

from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import AgendamentoForm
from agenda.models import (
    Profissional,
    Agendamento,
    BloqueioAgenda,
)
from accounts.models import (
    ItemOrcamento,
    Orcamento,
    Paciente,
    Procedimento,
    Tratamento,
    PerfilUsuario,
    ConfiguracaoClinica,
)

from django.db.models import Q


# =========================================
# NOVO AGENDAMENTO PELO PACIENTE
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "inserir")
def novo_agendamento_paciente(request, paciente_id):

    paciente = get_object_or_404(
        Paciente,
        id=paciente_id
    )

    # =========================================
    # PROFISSIONAIS DISPONÍVEIS PARA AGENDAMENTO
    # =========================================

    profissionais_disponiveis = (
        Profissional.objects
        .filter(
            ativo=True
        )
        .select_related(
            "usuario"
        )
        .order_by(
            "nome"
        )
    )

    # =========================================
    # PROFISSIONAL INICIAL
    # =========================================

    profissional_responsavel = None

    if paciente.dentista:

        profissional_responsavel = (
            profissionais_disponiveis
            .filter(
                usuario=paciente.dentista
            )
            .first()
        )

    # =========================================
    # TRATAMENTO ATIVO
    # =========================================

    tratamento = (
        paciente.tratamentos
        .filter(
            status="ATIVO"
        )
        .first()
    )

    # =========================================
    # CRIA TRATAMENTO SE NÃO EXISTIR
    # =========================================

    if tratamento is None and paciente.dentista:

        tratamento = Tratamento.objects.create(
            paciente=paciente,
            dentista=paciente.dentista,
            titulo="Tratamento Inicial"
        )

    # =========================================
    # ORÇAMENTO APROVADO DO TRATAMENTO
    # =========================================

    orcamento = None

    if tratamento:

        orcamento = (
            Orcamento.objects
            .filter(
                paciente=paciente,
                tratamento=tratamento,
                status="aprovado"
            )
            .order_by("-id")
            .first()
        )

    # =========================================
    # PROCEDIMENTOS DO ORÇAMENTO
    # =========================================

    procedimentos_ids = []

    if orcamento:

        procedimentos_ids = (
            ItemOrcamento.objects
            .filter(
                orcamento=orcamento
            )
            .values_list(
                "procedimento_id",
                flat=True
            )
        )

    # =========================================
    # POST
    # =========================================

    if request.method == "POST":

        form = AgendamentoForm(
            request.POST
        )

        # -----------------------------------------
        # PROFISSIONAIS DISPONÍVEIS
        # -----------------------------------------

        form.fields[
            "profissional"
        ].queryset = (
            profissionais_disponiveis
        )

        # -----------------------------------------
        # PROCEDIMENTOS DO ORÇAMENTO
        # -----------------------------------------

        if orcamento:

            form.fields[
                "procedimento"
            ].queryset = (
                Procedimento.objects
                .filter(
                    id__in=procedimentos_ids
                )
                .distinct()
            )

        else:

            form.fields[
                "procedimento"
            ].queryset = (
                Procedimento.objects.all()
            )

        # -----------------------------------------
        # SALVA
        # -----------------------------------------

        if form.is_valid():

            agendamento = form.save(
                commit=False
            )

            # Mantém o paciente da URL
            agendamento.paciente = paciente

            agendamento.save()

            return redirect(
                "agenda"
            )

        print(form.errors)

    # =========================================
    # GET
    # =========================================

    else:

        form = AgendamentoForm(
            initial={
                "paciente": paciente,
                "profissional": profissional_responsavel,
            }
        )

        # -----------------------------------------
        # PROFISSIONAIS DISPONÍVEIS
        # -----------------------------------------

        form.fields[
            "profissional"
        ].queryset = (
            profissionais_disponiveis
        )

        # -----------------------------------------
        # PROCEDIMENTOS
        # -----------------------------------------

        if orcamento:

            form.fields[
                "procedimento"
            ].queryset = (
                Procedimento.objects
                .filter(
                    id__in=procedimentos_ids
                )
                .distinct()
            )

        else:

            form.fields[
                "procedimento"
            ].queryset = (
                Procedimento.objects.all()
            )

    # =========================================
    # CONTEXTO
    # =========================================

    return render(

        request,

        "agenda/agendamento_form.html",

        {
            "form": form,
            "paciente": paciente,
            "orcamento": orcamento,
        }

    )

# =========================================
# ALTERAR STATUS DO AGENDAMENTO
# =========================================

def alterar_status_agendamento(agendamento_id, status):

    agendamento = get_object_or_404(
        Agendamento,
        id=agendamento_id
    )

    agendamento.status = status

    agendamento.save()

    # =========================================
    # SINCRONIZA PÓS-TRATAMENTO
    # =========================================

    if (
        status == "finalizado"
        and agendamento.pos_tratamento_id
    ):

        pos = agendamento.pos_tratamento

        # Só altera se ainda não estiver realizado
        if pos.status_retorno != "REALIZADO":

            pos.status_retorno = "REALIZADO"

            pos.save(
                update_fields=[
                    "status_retorno",
                    "atualizado_em",
                ]
            )

    return agendamento

# =========================================
# INICIAR ATENDIMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def iniciar_atendimento(request, agendamento_id):

    agendamento = alterar_status_agendamento(
        agendamento_id,
        'atendimento'
    )

    return redirect(
        'perfil_paciente',
        id=agendamento.paciente.id
    )

# =========================================
# EDITAR AGENDAMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def editar_agendamento(request, id):

    agendamento = get_object_or_404(
        Agendamento,
        id=id
    )

    # =========================================
    # FORM
    # =========================================

    form = AgendamentoForm(
        request.POST or None,
        instance=agendamento
    )

    # =========================================
    # PROFISSIONAIS ATIVOS
    # =========================================

    form.fields[
        "profissional"
    ].queryset = (
        Profissional.objects.filter(
            ativo=True
        )
        .order_by("nome")
    )

    # =========================================
    # PACIENTE ATUAL
    # =========================================

    paciente = agendamento.paciente

    # =========================================
    # PACIENTE DO POST
    # =========================================

    if request.method == "POST":

        paciente_post_id = request.POST.get(
            "paciente"
        )

        if paciente_post_id:

            paciente = get_object_or_404(
                Paciente,
                id=paciente_post_id
            )

    # =========================================
    # PROCEDIMENTOS
    # =========================================

    form.fields[
        "procedimento"
    ].queryset = Procedimento.objects.none()

    if paciente:

        tratamento = paciente.tratamentos.filter(
            status="ATIVO"
        ).first()

        if tratamento:

            orcamento = (
                Orcamento.objects.filter(
                    paciente=paciente,
                    tratamento=tratamento,
                    status="aprovado"
                )
                .order_by("-id")
                .first()
            )

            if orcamento:

                procedimentos_ids = (
                    ItemOrcamento.objects.filter(
                        orcamento=orcamento,
                        status__in=[
                            "planejado",
                            "andamento",
                            "realizado",
                            "reavaliar",
                        ]
                    )
                    .values_list(
                        "procedimento_id",
                        flat=True
                    )
                )

                # =========================================
                # MANTÉM PROCEDIMENTO ATUAL
                # =========================================

                procedimento_atual = (
                    agendamento.procedimento_id
                )

                queryset = Procedimento.objects.filter(
                    id__in=procedimentos_ids
                )

                if procedimento_atual:

                    queryset = (
                        Procedimento.objects.filter(
                            Q(
                                id__in=procedimentos_ids
                            )
                            |
                            Q(
                                id=procedimento_atual
                            )
                        )
                    )

                form.fields[
                    "procedimento"
                ].queryset = (
                    queryset
                    .distinct()
                    .order_by("nome")
                )

    # =========================================
    # SALVA
    # =========================================

    if form.is_valid():

        agendamento = form.save(
            commit=False
        )

        agendamento.save()

        return redirect(
            "agenda"
        )

    # =========================================
    # CONTEXTO
    # =========================================

    return render(

        request,

        "agenda/agendamento_form.html",

        {

            "form": form,

            "agendamento": agendamento,

        }

    )

# =========================================
# FINALIZAR ATENDIMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def finalizar_atendimento(request, agendamento_id):

    alterar_status_agendamento(
        agendamento_id,
        'finalizado'
    )

    return redirect(
        'agenda'
    )


# =========================================
# CONFIRMAR AGENDAMENTO
# =========================================
@login_required(login_url='/')
@permissao_required("agenda", "editar")
def confirmar_agendamento(request, agendamento_id):

    alterar_status_agendamento(
        agendamento_id,
        'confirmado'
    )

    return redirect(
        'agenda'
    )


# =========================================
# AGENDA
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "visualizar")
def agenda_view(request):

    data_str = request.GET.get("data")

    modo = request.GET.get(
        "modo",
        "minha"
    )

    if data_str:

        data_agenda = datetime.strptime(
            data_str,
            "%Y-%m-%d"
        ).date()

    else:

        data_agenda = date.today()

    agendamentos = Agendamento.objects.filter(
        data=data_agenda
    ).order_by(
        "hora_inicio"
    )

    # =========================================
    # CONFIGURAÇÃO DA AGENDA
    # =========================================

    config = (
        ConfiguracaoClinica.objects
        .filter(id=1)
        .first()
    )

    context = {

        "agendamentos": agendamentos,

        "modo": modo,

        "data_agenda": data_agenda,

        "config": config,

        "total_agendado": agendamentos.filter(
            status="agendado"
        ).count(),

        "total_confirmado": agendamentos.filter(
            status="confirmado"
        ).count(),

        "total_atendimento": agendamentos.filter(
            status="atendimento"
        ).count(),

        "total_finalizado": agendamentos.filter(
            status="finalizado"
        ).count(),

    }

    return render(
        request,
        "agenda/calendario.html",
        context
    )

# =========================================
# MOVER AGENDAMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def mover_agendamento(request):

    if request.method == 'POST':

        dados = json.loads(
            request.body
        )

        agendamento = get_object_or_404(
            Agendamento,
            id=dados['agendamento_id']
        )

        agendamento.data = dados['nova_data']

        agendamento.save()

        return JsonResponse({

            'sucesso': True

        })

    return JsonResponse({

        'sucesso': False

    })

# =========================================
# NOVO AGENDAMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "inserir")
def novo_agendamento(request):

    paciente_id = request.GET.get("paciente")

    data_url = request.GET.get("data")
    hora_url = request.GET.get("hora")

    paciente = None
    profissional_responsavel = None

    # =========================================
    # PACIENTE INFORMADO
    # =========================================

    if paciente_id:

        paciente = get_object_or_404(
            Paciente,
            id=paciente_id
        )

        # -----------------------------------------
        # DENTISTA RESPONSÁVEL
        # -----------------------------------------

        if paciente.dentista:

            profissional_responsavel = (
                Profissional.objects
                .filter(
                    usuario=paciente.dentista,
                    ativo=True
                )
                .first()
            )

    # =========================================
    # POST
    # =========================================

    if request.method == "POST":

        form = AgendamentoForm(
            request.POST
        )

        if form.is_valid():

            agendamento = form.save(
                commit=False
            )

            # -------------------------------------
            # PACIENTE
            # -------------------------------------

            if paciente:
                agendamento.paciente = paciente

            agendamento.save()

            return redirect(
                "agenda"
            )

    # =========================================
    # GET
    # =========================================

    else:

        initial = {}

        # -----------------------------------------
        # PACIENTE
        # -----------------------------------------

        if paciente:

            initial["paciente"] = paciente

        # -----------------------------------------
        # PROFISSIONAL
        # -----------------------------------------

        if profissional_responsavel:

            initial["profissional"] = (
                profissional_responsavel
            )

        # -----------------------------------------
        # DATA CLICADA NA AGENDA
        # -----------------------------------------

        if data_url:

            initial["data"] = data_url

        # -----------------------------------------
        # HORÁRIO CLICADO NA AGENDA
        # -----------------------------------------

        if hora_url:

            initial["hora_inicio"] = hora_url

        form = AgendamentoForm(
            initial=initial
        )

    # =========================================
    # CONTEXTO
    # =========================================

    context = {

        "form": form,

        "paciente": paciente,

        "data_url": data_url,

        "hora_url": hora_url,

    }

    return render(

        request,

        "agenda/agendamento_form.html",

        context,

    )

# =========================================
# EVENTOS FULLCALENDAR
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "visualizar")
def eventos_agenda(request):

    # =========================================
    # MODO DA AGENDA
    # =========================================

    modo = request.GET.get(
        "modo",
        "minha"
    )

    # =========================================
    # AGENDAMENTOS
    # =========================================

    agendamentos = (
        Agendamento.objects
        .select_related(
            "paciente",
            "profissional",
            "procedimento"
        )
    )

    # =========================================
    # AGENDAMENTOS
    # =========================================

    agendamentos = (
        Agendamento.objects
        .select_related(
            "paciente",
            "profissional",
            "procedimento"
        )
    )

    # =========================================
    # FILTRO DA AGENDA
    # =========================================

    perfil_usuario = getattr(
        request.user,
        "perfil",
        None
    )

    tipo_usuario = (
        perfil_usuario.tipo_usuario
        if perfil_usuario
        else None
    )

    # =========================================
    # MINHA AGENDA
    # =========================================

    if modo == "minha":

        # Dentista vê somente seus agendamentos
        if tipo_usuario == PerfilUsuario.DENTISTA:

            try:

                profissional = request.user.profissional

                agendamentos = agendamentos.filter(
                    profissional=profissional
                )

            except Profissional.DoesNotExist:

                agendamentos = Agendamento.objects.none()

        else:

            # Administrador, Secretária, Gestor,
            # Contabilidade, etc.
            # visualizam toda a agenda.
            pass

        print("=" * 60)
        print("MODO:", modo)
        print("USUÁRIO:", request.user.username)
        print("TIPO:", tipo_usuario)
        print("TOTAL AGENDAMENTOS:", agendamentos.count())
        print("=" * 60)

    # =========================================
    # AGENDA DA CLÍNICA
    # =========================================

    elif modo == "clinica":

        # Todos visualizam a agenda completa.
        pass
    eventos = []

    for agendamento in agendamentos:

        cor = '#0d6efd'
        print(
            f'ID={agendamento.id} | STATUS={agendamento.status}'
        )

        if agendamento.status == 'confirmado':
            cor = '#198754'

        elif agendamento.status == 'atendimento':
            cor = '#fd7e14'

        elif agendamento.status == 'finalizado':
            cor = '#6c757d'

        elif agendamento.status == 'cancelado':
            cor = '#dc3545'

        elif agendamento.status == 'faltou':
            cor = '#991b1b'

        whatsapp_url = '#'

        telefone = (
            agendamento.paciente.whatsapp
            or agendamento.paciente.telefone
            or ''
        )

        if telefone:

            telefone_limpo = ''.join(
                filter(str.isdigit, telefone)
            )

            print(
                f'ID={agendamento.id} | STATUS={agendamento.status}'
            )

            if agendamento.status == 'agendado':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Estamos entrando em contato para confirmar sua consulta.\n\n'
                    f'Data: {agendamento.data.strftime("%d/%m/%Y")}\n'
                    f'Horário: {agendamento.hora_inicio.strftime("%H:%M")}\n'
                    f'Procedimento: '
                    f'{agendamento.procedimento.nome if agendamento.procedimento else "Consulta"}\n\n'
                    f'Por favor, responda esta mensagem confirmando sua presença.'
                )

            elif agendamento.status == 'confirmado':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Lembramos sua consulta.\n\n'
                    f'Data: {agendamento.data.strftime("%d/%m/%Y")}\n'
                    f'Horário: {agendamento.hora_inicio.strftime("%H:%M")}\n'
                    f'Procedimento: '
                    f'{agendamento.procedimento.nome if agendamento.procedimento else "Consulta"}\n\n'
                    f'Aguardamos você!'
                )

            elif agendamento.status == 'atendimento':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Seu atendimento está em andamento.\n\n'
                    f'Caso necessite de alguma informação adicional, estamos à disposição.'
                )

            elif agendamento.status == 'finalizado':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Esperamos que seu atendimento tenha sido excelente.\n\n'
                    f'Caso tenha qualquer dúvida, estamos à disposição.\n\n'
                    f'Obrigado pela confiança!'
                )

            elif agendamento.status == 'faltou':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Notamos que você não compareceu à consulta agendada.\n\n'
                    f'Gostaria de remarcar seu atendimento?\n\n'
                    f'Estamos à disposição.'
                )

            elif agendamento.status == 'cancelado':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Seu agendamento foi cancelado.\n\n'
                    f'Caso deseje, podemos encontrar uma nova data para atendimento.'
                )
            
            elif agendamento.status == 'reagendar':

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Gostaríamos de reagendar sua consulta.\n\n'
                    f'Entre em contato conosco para escolhermos um novo horário.'
                )

            else:

                mensagem = (
                    f'Olá {agendamento.paciente.nome}!\n\n'
                    f'Seu agendamento está registrado em nosso sistema.\n\n'
                    f'Data: {agendamento.data.strftime("%d/%m/%Y")}\n'
                    f'Horário: {agendamento.hora_inicio.strftime("%H:%M")}'
                )

            whatsapp_url = (
                'https://api.whatsapp.com/send?phone=55'
                + telefone_limpo
                + '&text='
                + quote_plus(mensagem)
            )

        print(whatsapp_url)   

        eventos.append({

    'id': agendamento.id,

    'title': (
        f'{agendamento.paciente.nome.split()[0]}'
    ),

    # =========================================
    # DATA + HORÁRIO DO AGENDAMENTO
    # =========================================

    'start': (
        f'{agendamento.data.isoformat()}T'
        f'{agendamento.hora_inicio.strftime("%H:%M:%S")}'
    ),

    'allDay': False,
    'url': f'/agenda/editar/{agendamento.id}/',

    'extendedProps': {

                'status': agendamento.get_status_display(),

                'paciente': agendamento.paciente.nome,

                'procedimento': (
                    agendamento.procedimento.nome
                    if agendamento.procedimento
                    else 'Não informado'
                ),

                'profissional': (
                    agendamento.profissional.nome
                ),

                'perfil_url': reverse(
                    'perfil_paciente',
                    args=[agendamento.paciente.id]
                ),

                'editar_url': reverse(
                    'editar_agendamento',
                    args=[agendamento.id]
                ),

                'confirmar_url': reverse(
                    'confirmar_agendamento',
                    args=[agendamento.id]
                ),

                'faltou_url': reverse(
                    'marcar_falta',
                    args=[agendamento.id]
                ),

                'cancelar_url': reverse(
                    'cancelar_agendamento',
                    args=[agendamento.id]
                ),

                'iniciar_url': reverse(
                    'iniciar_atendimento',
                    args=[agendamento.id]
                ),

                'finalizar_url': reverse(
                    'finalizar_atendimento',
                    args=[agendamento.id]
                ),

                'whatsapp_url': whatsapp_url,
                
                "excluir_url": reverse(
                    "excluir_agendamento",
                    args=[agendamento.id]
                ),

            },

            'backgroundColor': cor,

            'borderColor': cor,

        })

    return JsonResponse(
        eventos,
        safe=False
    )

# =========================================
# EVENTOS DE BLOQUEIO — FULLCALENDAR
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "visualizar")
def eventos_bloqueios(request):

    modo = request.GET.get(
        "modo",
        "minha"
    )

    bloqueios = (
        BloqueioAgenda.objects
        .filter(
            ativo=True
        )
        .select_related(
            "profissional"
        )
        .order_by(
            "data_inicio",
            "hora_inicio"
        )
    )

    eventos = []

    # =========================================
    # PERFIL DO USUÁRIO
    # =========================================

    perfil_usuario = getattr(
        request.user,
        "perfil",
        None
    )

    tipo_usuario = (
        perfil_usuario.tipo_usuario
        if perfil_usuario
        else None
    )

    # =========================================
    # PROFISSIONAL DO USUÁRIO
    # =========================================

    profissional_usuario = None

    if tipo_usuario == PerfilUsuario.DENTISTA:

        try:

            profissional_usuario = (
                request.user.profissional
            )

        except Profissional.DoesNotExist:

            profissional_usuario = None

    # =========================================
    # PROCESSA OS BLOQUEIOS
    # =========================================

    for bloqueio in bloqueios:

        # =====================================
        # BLOQUEIO PARA TODA A CLÍNICA
        # =====================================

        if bloqueio.profissional is None:

            # ---------------------------------
            # BLOQUEIO COM HORÁRIO
            # ---------------------------------

            if (
                bloqueio.hora_inicio
                and
                bloqueio.hora_fim
            ):

                start = (
                    f"{bloqueio.data_inicio.isoformat()}T"
                    f"{bloqueio.hora_inicio.strftime('%H:%M:%S')}"
                )

                end = (
                    f"{bloqueio.data_inicio.isoformat()}T"
                    f"{bloqueio.hora_fim.strftime('%H:%M:%S')}"
                )

                eventos.append({

                    "id": (
                        f"bloqueio-{bloqueio.id}"
                    ),

                    "title": (
                        f"🔒 "
                        f"{bloqueio.get_tipo_display()}"
                    ),

                    "start": start,

                    "end": end,

                    "allDay": False,

                    "display": "background",

                    "backgroundColor": "#f8d7da",

                    "borderColor": "#dc3545",

                    "extendedProps": {

                        "bloqueio": True,

                        "tipo": (
                            bloqueio.get_tipo_display()
                        ),

                        "descricao": (
                            bloqueio.descricao
                            or
                            bloqueio.get_tipo_display()
                        ),

                        "profissional": (
                            "Toda a clínica"
                        ),

                    },

                })

            # ---------------------------------
            # BLOQUEIO DE DIA INTEIRO
            # ---------------------------------

            else:

                data_fim = (
                    bloqueio.data_fim
                    + timedelta(days=1)
                )

                eventos.append({

                    "id": (
                        f"bloqueio-{bloqueio.id}"
                    ),

                    "title": (
                        f"🔒 "
                        f"{bloqueio.get_tipo_display()}"
                    ),

                    "start": (
                        bloqueio.data_inicio.isoformat()
                    ),

                    "end": (
                        data_fim.isoformat()
                    ),

                    "allDay": True,

                    "display": "background",

                    "backgroundColor": "#f8d7da",

                    "borderColor": "#dc3545",

                    "extendedProps": {

                        "bloqueio": True,

                        "tipo": (
                            bloqueio.get_tipo_display()
                        ),

                        "descricao": (
                            bloqueio.descricao
                            or
                            bloqueio.get_tipo_display()
                        ),

                        "profissional": (
                            "Toda a clínica"
                        ),

                    },

                })

            continue

        # =====================================
        # BLOQUEIO DE PROFISSIONAL
        # =====================================

        # Só exibimos visualmente o bloqueio
        # específico quando estamos na
        # "Minha Agenda" daquele profissional.
        #
        # Na Agenda da Clínica não podemos pintar
        # a grade inteira, pois o bloqueio pertence
        # somente a um profissional.

        if (
            modo == "minha"
            and
            profissional_usuario
            and
            bloqueio.profissional_id
            ==
            profissional_usuario.id
        ):

            # ---------------------------------
            # BLOQUEIO COM HORÁRIO
            # ---------------------------------

            if (
                bloqueio.hora_inicio
                and
                bloqueio.hora_fim
            ):

                start = (
                    f"{bloqueio.data_inicio.isoformat()}T"
                    f"{bloqueio.hora_inicio.strftime('%H:%M:%S')}"
                )

                end = (
                    f"{bloqueio.data_inicio.isoformat()}T"
                    f"{bloqueio.hora_fim.strftime('%H:%M:%S')}"
                )

                eventos.append({

                    "id": (
                        f"bloqueio-{bloqueio.id}"
                    ),

                    "title": (
                        f"🔒 "
                        f"{bloqueio.get_tipo_display()}"
                    ),

                    "start": start,

                    "end": end,

                    "allDay": False,

                    "display": "background",

                    "backgroundColor": "#fff3cd",

                    "borderColor": "#ffc107",

                    "extendedProps": {

                        "bloqueio": True,

                        "tipo": (
                            bloqueio.get_tipo_display()
                        ),

                        "descricao": (
                            bloqueio.descricao
                            or
                            bloqueio.get_tipo_display()
                        ),

                        "profissional": (
                            bloqueio.profissional.nome
                        ),

                    },

                })

            # ---------------------------------
            # BLOQUEIO DE DIA INTEIRO
            # ---------------------------------

            else:

                data_fim = (
                    bloqueio.data_fim
                    + timedelta(days=1)
                )

                eventos.append({

                    "id": (
                        f"bloqueio-{bloqueio.id}"
                    ),

                    "title": (
                        f"🔒 "
                        f"{bloqueio.get_tipo_display()}"
                    ),

                    "start": (
                        bloqueio.data_inicio.isoformat()
                    ),

                    "end": (
                        data_fim.isoformat()
                    ),

                    "allDay": True,

                    "display": "background",

                    "backgroundColor": "#fff3cd",

                    "borderColor": "#ffc107",

                    "extendedProps": {

                        "bloqueio": True,

                        "tipo": (
                            bloqueio.get_tipo_display()
                        ),

                        "descricao": (
                            bloqueio.descricao
                            or
                            bloqueio.get_tipo_display()
                        ),

                        "profissional": (
                            bloqueio.profissional.nome
                        ),

                    },

                })

    return JsonResponse(
        eventos,
        safe=False
    )


# =========================================
# FALTA
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def marcar_falta(request, agendamento_id):

    alterar_status_agendamento(
        agendamento_id,
        'faltou'
    )

    return redirect(
        'agenda'
    )

# =========================================
# CANCELAR
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
def cancelar_agendamento(request, agendamento_id):

    alterar_status_agendamento(
        agendamento_id,
        'cancelado'
    )

    return redirect(
        'agenda'
    )

# =========================================
# EXCLUIR AGENDAMENTO
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "excluir")
def excluir_agendamento(request, agendamento_id):

    agendamento = get_object_or_404(
        Agendamento,
        id=agendamento_id
    )

    # =========================================
    # PROTEGE ATENDIMENTOS JÁ INICIADOS
    # =========================================

    if agendamento.status in [
        "atendimento",
        "finalizado",
    ]:
        messages.error(
            request,
            "Este agendamento não pode ser excluído "
            "porque o atendimento já foi iniciado ou finalizado."
        )

        return redirect(
            "agenda"
        )

    # =========================================
    # CONFIRMAÇÃO
    # =========================================

    if request.method == "POST":

        agendamento.delete()

        messages.success(
            request,
            "Agendamento excluído com sucesso."
        )

        return redirect(
            "agenda"
        )

    # =========================================
    # TELA DE CONFIRMAÇÃO
    # =========================================

    return render(
        request,
        "agenda/agendamento_excluir.html",
        {
            "agendamento": agendamento,
        }
    )

# =========================================
# ALTERAR STATUS — AJAX
# =========================================

@login_required(login_url='/')
@permissao_required("agenda", "editar")
@require_POST
def alterar_status_ajax(request):

    dados = json.loads(request.body)

    agendamento = get_object_or_404(
        Agendamento,
        id=dados['agendamento_id']
    )

    novo_status = dados['status']

    agendamento.status = novo_status

    agendamento.save()

    # =========================================
    # SINCRONIZA PÓS-TRATAMENTO
    # =========================================

    if (
        novo_status == "finalizado"
        and agendamento.pos_tratamento_id
    ):

        pos = agendamento.pos_tratamento

        # Só altera se ainda não estiver realizado
        if pos.status_retorno != "REALIZADO":

            pos.status_retorno = "REALIZADO"

            pos.save(
                update_fields=[
                    "status_retorno",
                    "atualizado_em",
                ]
            )

    return JsonResponse({
        "sucesso": True,
        "status": agendamento.status
    })

# =========================================================
# BLOQUEIOS DA AGENDA
# =========================================================

@login_required(login_url='/')
@permissao_required("agenda", "visualizar")
def lista_bloqueios(request):

    bloqueios = (
        BloqueioAgenda.objects
        .select_related("profissional")
        .order_by(
            "data_inicio",
            "hora_inicio"
        )
    )

    return render(
        request,
        "agenda/bloqueios_lista.html",
        {
            "bloqueios": bloqueios,
        }
    )


@login_required(login_url='/')
@permissao_required("agenda", "inserir")
def novo_bloqueio(request):

    if request.method == "POST":

        tipo = request.POST.get("tipo")
        data_inicio = request.POST.get("data_inicio")
        data_fim = request.POST.get("data_fim")
        hora_inicio = request.POST.get("hora_inicio")
        hora_fim = request.POST.get("hora_fim")
        profissional_id = request.POST.get("profissional")
        descricao = request.POST.get("descricao")

        profissional = None

        if profissional_id:
            profissional = get_object_or_404(
                Profissional,
                id=profissional_id
            )

        BloqueioAgenda.objects.create(
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            hora_inicio=hora_inicio or None,
            hora_fim=hora_fim or None,
            profissional=profissional,
            descricao=descricao or None,
        )

        return redirect(
            "lista_bloqueios"
        )

    profissionais = (
        Profissional.objects
        .filter(ativo=True)
        .order_by("nome")
    )

    return render(
        request,
        "agenda/bloqueio_form.html",
        {
            "profissionais": profissionais,
        }
    )


@login_required(login_url='/')
@permissao_required("agenda", "editar")
def editar_bloqueio(request, id):

    bloqueio = get_object_or_404(
        BloqueioAgenda,
        id=id
    )

    if request.method == "POST":

        bloqueio.tipo = request.POST.get("tipo")
        bloqueio.data_inicio = request.POST.get(
            "data_inicio"
        )
        bloqueio.data_fim = request.POST.get(
            "data_fim"
        )

        bloqueio.hora_inicio = (
            request.POST.get("hora_inicio")
            or None
        )

        bloqueio.hora_fim = (
            request.POST.get("hora_fim")
            or None
        )

        profissional_id = request.POST.get(
            "profissional"
        )

        if profissional_id:

            bloqueio.profissional = get_object_or_404(
                Profissional,
                id=profissional_id
            )

        else:

            bloqueio.profissional = None

        bloqueio.descricao = (
            request.POST.get("descricao")
            or None
        )

        bloqueio.ativo = (
            request.POST.get("ativo") == "on"
        )

        bloqueio.save()

        return redirect(
            "lista_bloqueios"
        )

    profissionais = (
        Profissional.objects
        .filter(ativo=True)
        .order_by("nome")
    )

    return render(
        request,
        "agenda/bloqueio_form.html",
        {
            "bloqueio": bloqueio,
            "profissionais": profissionais,
        }
    )


@login_required(login_url='/')
@permissao_required("agenda", "excluir")
def excluir_bloqueio(request, id):

    bloqueio = get_object_or_404(
        BloqueioAgenda,
        id=id
    )

    if request.method == "POST":

        bloqueio.delete()

        return redirect(
            "lista_bloqueios"
        )

    return render(
        request,
        "agenda/bloqueio_excluir.html",
        {
            "bloqueio": bloqueio,
        }
    )

# =========================================================
# IMPORTAÇÃO DE FERIADOS NACIONAIS
# =========================================================

@login_required(login_url='/')
@permissao_required("agenda", "inserir")
def importar_feriados_nacionais_view(request):

    if request.method != "POST":
        return redirect("lista_bloqueios")

    ano = request.POST.get("ano")

    try:
        ano = int(ano)
    except (TypeError, ValueError):

        messages.error(
            request,
            "Ano inválido para importação dos feriados."
        )

        return redirect(
            "lista_bloqueios"
        )

    from .feriados import importar_feriados_nacionais

    resultado = importar_feriados_nacionais(
        ano
    )

    criados = resultado["criados"]
    existentes = resultado["existentes"]

    if criados:

        messages.success(
            request,
            (
                f"{criados} feriado(s) nacional(is) "
                f"de {ano} importado(s) com sucesso."
            )
        )

    if existentes:

        messages.info(
            request,
            (
                f"{existentes} feriado(s) nacional(is) "
                f"de {ano} já estava(m) cadastrado(s)."
            )
        )

    return redirect(
        "lista_bloqueios"
    )