from django.db import models
from django.contrib.auth.models import User

from accounts.models import Paciente, Procedimento


# =========================================
# PROFISSIONAIS
# =========================================

class Profissional(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profissional",
    )

    nome = models.CharField(
        max_length=200
    )

    especialidade = models.CharField(
        max_length=100,
        blank=True,
    )

    telefone = models.CharField(
        max_length=20,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    cor_agenda = models.CharField(
        max_length=20,
        default="#2563eb",
    )

    ativo = models.BooleanField(
        default=True,
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ["nome"]

        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"

    def __str__(self):
        return self.nome

# =========================================
# AGENDAMENTOS
# =========================================

class Agendamento(models.Model):

    STATUS_CHOICES = [
        ("agendado", "Agendado"),
        ("confirmado", "Confirmado"),
        ("atendimento", "Em Atendimento"),
        ("finalizado", "Finalizado"),
        ("faltou", "Faltou"),
        ("cancelado", "Cancelado"),
    ]

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="agendamentos",
    )

    # =========================================
    # PÓS-TRATAMENTO
    # =========================================

    pos_tratamento = models.ForeignKey(
        "accounts.PosTratamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendamentos_retorno",
        verbose_name="Pós-Tratamento",
    )

    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="agendamentos",
    )

    procedimento = models.ForeignKey(
        Procedimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    data = models.DateField()

    hora_inicio = models.TimeField()

    duracao = models.PositiveIntegerField(
        default=60,
        help_text="Duração em minutos",
    )

    observacoes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="agendado",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "data",
            "hora_inicio",
        ]

        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"

    def __str__(self):

        return (
            f"{self.paciente.nome} - "
            f"{self.data.strftime('%d/%m/%Y')} "
            f"às {self.hora_inicio.strftime('%H:%M')}"
        )

# =========================================================
# BLOQUEIOS DA AGENDA
# =========================================================

class BloqueioAgenda(models.Model):

    TIPO_CHOICES = [
        ("feriado", "Feriado"),
        ("ferias", "Férias"),
        ("ausencia", "Ausência do profissional"),
        ("almoco", "Horário de almoço"),
        ("manual", "Bloqueio manual"),
        ("manutencao", "Manutenção"),
        ("outro", "Outro"),
    ]

    ORIGEM_CHOICES = [
        ("manual", "Cadastro manual"),
        ("nacional", "Calendário nacional"),
        ("estadual", "Calendário estadual"),
        ("municipal", "Calendário municipal"),
    ]

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default="manual",
        verbose_name="Tipo de bloqueio"
    )

    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default="manual",
        verbose_name="Origem"
    )

    chave_feriado = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Chave do feriado"
    )

    data_inicio = models.DateField(
        verbose_name="Data inicial"
    )

    data_fim = models.DateField(
        verbose_name="Data final"
    )

    hora_inicio = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Hora inicial"
    )

    hora_fim = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Hora final"
    )

    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bloqueios_agenda",
        verbose_name="Profissional"
    )

    descricao = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Descrição"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "data_inicio",
            "hora_inicio"
        ]

        verbose_name = "Bloqueio da Agenda"

        verbose_name_plural = "Bloqueios da Agenda"

    def __str__(self):

        descricao = (
            self.descricao
            or self.get_tipo_display()
        )

        return (
            f"{descricao} - "
            f"{self.data_inicio.strftime('%d/%m/%Y')}"
        )

# =====================================================
# CONSULTÓRIOS
# =====================================================

class Consultorio(models.Model):

    nome = models.CharField(
        max_length=100,
        verbose_name="Nome do consultório"
    )

    descricao = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Descrição"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Consultório"
        verbose_name_plural = "Consultórios"

    def __str__(self):
        return self.nome