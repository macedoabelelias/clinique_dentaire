from datetime import datetime, timedelta

from django import forms

from .models import Agendamento


class AgendamentoForm(forms.ModelForm):

    class Meta:

        model = Agendamento

        fields = [

            'paciente',
            'profissional',
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
    # VALIDAÇÃO DE CONFLITO DE HORÁRIO
    # =========================================

    def clean(self):

        cleaned_data = super().clean()

        profissional = cleaned_data.get(
            'profissional'
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

        # =====================================
        # STATUS QUE BLOQUEIAM O HORÁRIO
        # =====================================

        status_bloqueadores = [
            'agendado',
            'confirmado',
            'atendimento',
        ]

        # =====================================
        # SE O NOVO AGENDAMENTO NÃO BLOQUEIA
        # NENHUMA NECESSIDADE DE VALIDAR
        # =====================================

        if status not in status_bloqueadores:

            return cleaned_data

        # =====================================
        # CALCULA INÍCIO E FIM
        # =====================================

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

        # =====================================
        # BUSCA AGENDAMENTOS DO MESMO
        # PROFISSIONAL E MESMA DATA
        # =====================================

        conflitos = Agendamento.objects.filter(

            profissional=profissional,

            data=data,

            status__in=status_bloqueadores

        )

        # =====================================
        # NA EDIÇÃO, IGNORA O PRÓPRIO
        # AGENDAMENTO
        # =====================================

        if self.instance and self.instance.pk:

            conflitos = conflitos.exclude(
                pk=self.instance.pk
            )

        # =====================================
        # VERIFICA SOBREPOSIÇÃO
        # =====================================

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

            # =================================
            # REGRA DE SOBREPOSIÇÃO
            # =================================
            #
            # Existe conflito quando:
            #
            # início novo < fim existente
            #
            # E
            #
            # fim novo > início existente
            #
            # =================================

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

        return cleaned_data