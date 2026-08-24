
# clinique_dentaire
#Software de gerenciamento de clínicas e consultório odontológicos. 
Obs.: Para fazer a mudança de Logotipo na views.py - Crtl+F = digito logo.png e modifico a imagem para vários formulários. Em cabecalhos.html =
Hoje está assim: <div class="documento-cabecalho">

    {% if configuracao.logo %}
        <img
            src="{{ configuracao.logo.url }}"
            class="logo-clinica"
            alt="Logo"
        >
    {% endif %}    basta alterar para 

<div class="documento-cabecalho">

    <img
        src="{% static 'img/nova_logo.png' %}"
        class="logo-clinica"
        alt="Clinique Dentaire"
    >


    Para zerar todo banco de dados, apagar completamente o db.sqlite3, posso usar: no PoweShell - python manage.py flush

    Para zerar o banco sem apagar dados (shell)= from accounts.models import *
from agenda.models import *

print("\n========== CONTAS ==========")

for modelo in [
    Procedimento,
    Paciente,
    Tratamento,
    PosTratamento,
    Orcamento,
    ItemOrcamento,
    ContaReceber,
    ContaPagar,
]:
    try:
        print(f"{modelo.__name__}: {modelo.objects.count()}")
    except Exception as e:
        print(f"{modelo.__name__}: ERRO - {e}")


print("\n========== AGENDA ==========")

for modelo in [
    Agendamento,
    Profissional,
]:
    try:
        print(f"{modelo.__name__}: {modelo.objects.count()}")
    except Exception as e:
        print(f"{modelo.__name__}: ERRO - {e}")