from datetime import datetime, timedelta

from django import forms

from .models import (
    Agendamento,
    BloqueioAgenda,
)


class AgendamentoForm(forms.ModelForm):

    class Meta:

        model = Agendamento

        fields = [

            'paciente',
            'profissional',
            'consultorio',
            'procedimento',
            'data',
            'hora_inicio',
            'duracao',
            'status',
            'observacoes'

        ]

        widgets = {

            'data': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'hora_inicio': forms.TimeInput(
                attrs={
                    'type': 'time'
                }
            ),

            'observacoes': forms.Textarea(
                attrs={
                    'rows': 4
                }
            )

        }

        # =========================================
    # VALIDAÇÃO
    # =========================================

    def clean(self):

        cleaned_data = super().clean()

        profissional = cleaned_data.get(
            'profissional'
        )

        consultorio = cleaned_data.get(
            'consultorio'
        )

        data = cleaned_data.get(
            'data'
        )

        hora_inicio = cleaned_data.get(
            'hora_inicio'
        )

        duracao = cleaned_data.get(
            'duracao'
        )

        status = cleaned_data.get(
            'status'
        )

        # =====================================
        # SE DADOS ESSENCIAIS NÃO EXISTIREM
        # =====================================

        if not all([
            profissional,
            data,
            hora_inicio,
            duracao
        ]):

            return cleaned_data

        # =========================================
        # CONFIGURAÇÃO DA CLÍNICA
        # =========================================

        from accounts.models import (
            ConfiguracaoClinica
        )

        config = (
            ConfiguracaoClinica.objects
            .filter(id=1)
            .first()
        )

        # =========================================
        # STATUS QUE BLOQUEIAM O HORÁRIO
        # =========================================

        status_bloqueadores = [
            'agendado',
            'confirmado',
            'atendimento',
        ]

        # =========================================
        # VALIDAÇÕES DA AGENDA DA CLÍNICA
        # =========================================

        if config:

            # =====================================
            # DIA DA SEMANA
            # =====================================

            dias_funcionamento = {

                0: config.funciona_segunda,
                1: config.funciona_terca,
                2: config.funciona_quarta,
                3: config.funciona_quinta,
                4: config.funciona_sexta,
                5: config.funciona_sabado,
                6: config.funciona_domingo,

            }

            dia_funciona = (
                dias_funcionamento.get(
                    data.weekday(),
                    False
                )
            )

            if not dia_funciona:

                self.add_error(
                    'data',
                    (
                        'A clínica não possui '
                        'atendimento neste dia.'
                    )
                )

                return cleaned_data

            # =====================================
            # HORÁRIOS DA CLÍNICA
            # =====================================

            inicio_agenda = (
                config.hora_inicio_agenda
            )

            fim_agenda = (
                config.hora_fim_agenda
            )

            minutos_hora = (
                hora_inicio.hour * 60
                +
                hora_inicio.minute
            )

            minutos_inicio = (
                inicio_agenda.hour * 60
                +
                inicio_agenda.minute
            )

            minutos_fim = (
                fim_agenda.hour * 60
                +
                fim_agenda.minute
            )

            # =====================================
            # INÍCIO FORA DO HORÁRIO
            # =====================================

            if minutos_hora < minutos_inicio:

                self.add_error(
                    'hora_inicio',
                    (
                        'Horário fora do período '
                        'de atendimento da clínica. '
                        f'A clínica inicia os atendimentos '
                        f'às {inicio_agenda.strftime("%H:%M")}.'
                    )
                )

                return cleaned_data

            # =====================================
            # INÍCIO NO HORÁRIO DE ENCERRAMENTO
            # =====================================

            if minutos_hora >= minutos_fim:

                self.add_error(
                    'hora_inicio',
                    (
                        'Horário fora do período '
                        'de atendimento da clínica. '
                        f'A clínica encerra os atendimentos '
                        f'às {fim_agenda.strftime("%H:%M")}.'
                    )
                )

                return cleaned_data

            # =====================================
            # VALIDAÇÃO DO INTERVALO
            # =====================================

            intervalo = (
                config.intervalo_agenda
                or 30
            )

            if (
                (
                    minutos_hora
                    -
                    minutos_inicio
                )
                %
                intervalo
                != 0
            ):

                self.add_error(
                    'hora_inicio',
                    (
                        'Horário inválido. '
                        f'A agenda utiliza intervalos '
                        f'de {intervalo} minutos. '
                        'Escolha um horário compatível '
                        'com a grade da agenda.'
                    )
                )

                return cleaned_data

            # =====================================
            # VERIFICA SE A DURAÇÃO ULTRAPASSA
            # O HORÁRIO DE ENCERRAMENTO
            # =====================================

            minutos_fim_novo = (
                minutos_hora
                +
                int(duracao)
            )

            if minutos_fim_novo > minutos_fim:

                self.add_error(
                    'duracao',
                    (
                        'O agendamento ultrapassa '
                        'o horário de funcionamento '
                        f'da clínica, que encerra às '
                        f'{fim_agenda.strftime("%H:%M")}.'
                    )
                )

                return cleaned_data

        # =========================================
        # SE O STATUS NÃO BLOQUEIA HORÁRIO
        # =========================================

        if status not in status_bloqueadores:

            return cleaned_data

        # =========================================
        # CALCULA INÍCIO E FIM
        # =========================================

        inicio_novo = datetime.combine(
            data,
            hora_inicio
        )

        fim_novo = (
            inicio_novo
            +
            timedelta(
                minutes=int(duracao)
            )
        )

        # =========================================
        # BLOQUEIOS DA AGENDA
        # =========================================

        bloqueios_clinica = (
            BloqueioAgenda.objects
            .filter(
                ativo=True,
                data_inicio__lte=data,
                data_fim__gte=data,
                profissional__isnull=True,
            )
        )

        bloqueios_profissional = (
            BloqueioAgenda.objects
            .filter(
                ativo=True,
                data_inicio__lte=data,
                data_fim__gte=data,
                profissional=profissional,
            )
        )

        bloqueios = (
            list(bloqueios_clinica)
            +
            list(bloqueios_profissional)
        )

        # =========================================
        # VERIFICA CADA BLOQUEIO
        # =========================================

        for bloqueio in bloqueios:

            # =====================================
            # BLOQUEIO DE DIA INTEIRO
            # =====================================

            if (
                not bloqueio.hora_inicio
                or
                not bloqueio.hora_fim
            ):

                if bloqueio.profissional:

                    descricao_profissional = (
                        f'para o profissional '
                        f'{bloqueio.profissional.nome}'
                    )

                else:

                    descricao_profissional = (
                        'para toda a clínica'
                    )

                descricao = (
                    bloqueio.descricao
                    or
                    bloqueio.get_tipo_display()
                )

                self.add_error(
                    'data',
                    (
                        'Não é possível realizar '
                        'agendamento nesta data. '
                        'Existe um bloqueio '
                        f'{descricao_profissional}: '
                        f'{descricao}.'
                    )
                )

                return cleaned_data

            # =====================================
            # BLOQUEIO COM HORÁRIO
            # =====================================

            inicio_bloqueio = datetime.combine(
                data,
                bloqueio.hora_inicio
            )

            fim_bloqueio = datetime.combine(
                data,
                bloqueio.hora_fim
            )

            # =====================================
            # VERIFICA SOBREPOSIÇÃO
            # =====================================

            if (
                inicio_novo < fim_bloqueio
                and
                fim_novo > inicio_bloqueio
            ):

                descricao = (
                    bloqueio.descricao
                    or
                    bloqueio.get_tipo_display()
                )

                self.add_error(
                    'hora_inicio',
                    (
                        'Horário indisponível. '
                        f'Existe um bloqueio de '
                        f'{bloqueio.hora_inicio.strftime("%H:%M")} '
                        f'às '
                        f'{bloqueio.hora_fim.strftime("%H:%M")}: '
                        f'{descricao}.'
                    )
                )

                return cleaned_data

        # =========================================
        # BUSCA AGENDAMENTOS DO MESMO
        # PROFISSIONAL E MESMA DATA
        # =========================================

        conflitos = (
            Agendamento.objects
            .filter(
                profissional=profissional,
                data=data,
                status__in=status_bloqueadores
            )
        )

        # =========================================
        # NA EDIÇÃO, IGNORA O PRÓPRIO
        # AGENDAMENTO
        # =========================================

        if self.instance and self.instance.pk:

            conflitos = (
                conflitos.exclude(
                    pk=self.instance.pk
                )
            )

        # =========================================
        # VERIFICA SOBREPOSIÇÃO
        # =========================================

        for agendamento in conflitos:

            inicio_existente = datetime.combine(
                agendamento.data,
                agendamento.hora_inicio
            )

            fim_existente = (
                inicio_existente
                +
                timedelta(
                    minutes=int(
                        agendamento.duracao
                    )
                )
            )

            # =====================================
            # REGRA DE SOBREPOSIÇÃO
            # =====================================

            if (
                inicio_novo < fim_existente
                and
                fim_novo > inicio_existente
            ):

                self.add_error(
                    'hora_inicio',
                    (
                        'Horário indisponível. '
                        f'O profissional '
                        f'{profissional.nome} já possui '
                        f'um agendamento das '
                        f'{agendamento.hora_inicio.strftime("%H:%M")} '
                        f'às '
                        f'{fim_existente.strftime("%H:%M")}.'
                    )
                )

                break

        # =========================================
        # BUSCA AGENDAMENTOS DO MESMO
        # CONSULTÓRIO E MESMA DATA
        # =========================================

        if consultorio:

            conflitos_consultorio = (
                Agendamento.objects
                .filter(
                    consultorio=consultorio,
                    data=data,
                    status__in=status_bloqueadores
                )
            )

            # =====================================
            # NA EDIÇÃO, IGNORA O PRÓPRIO
            # AGENDAMENTO
            # =====================================

            if self.instance and self.instance.pk:

                conflitos_consultorio = (
                    conflitos_consultorio.exclude(
                        pk=self.instance.pk
                    )
                )

            # =====================================
            # VERIFICA SOBREPOSIÇÃO
            # =====================================

            for agendamento in conflitos_consultorio:

                inicio_existente = datetime.combine(
                    agendamento.data,
                    agendamento.hora_inicio
                )

                fim_existente = (
                    inicio_existente
                    +
                    timedelta(
                        minutes=int(
                            agendamento.duracao
                        )
                    )
                )

                # =====================================
                # REGRA DE SOBREPOSIÇÃO
                # =====================================

                if (
                    inicio_novo < fim_existente
                    and
                    fim_novo > inicio_existente
                ):

                    self.add_error(
                        'hora_inicio',
                        (
                            'Horário indisponível. '
                            f'O consultório '
                            f'{consultorio.nome} já possui '
                            f'um agendamento das '
                            f'{agendamento.hora_inicio.strftime("%H:%M")} '
                            f'às '
                            f'{fim_existente.strftime("%H:%M")}.'
                        )
                    )

                    break

        # =========================================
        # RETORNA OS DADOS
        # =========================================

        return cleaned_data