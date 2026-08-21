
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