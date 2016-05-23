# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import httplib
import urllib
import urllib2
import re

from django.utils.encoding import smart_str, force_unicode
from gestorpsi.boleto.models import BradescoBilletData
from django.contrib.auth.models import User
from gestorpsi.document.models import Document, TypeDocument
from gestorpsi.address.models import City, Address, Country

from gestorpsi.gcm.models import Plan, Invoice
from gestorpsi.organization.models import Organization

from gestorpsi.boleto.models import INSCRIPTION_DEFAULT_VALUE
URL_GERADOR_BOLETOS = 'http://dev.geradorboletos.doois.com.br/bradesco/'
#URL_GERADOR_BOLETOS = 'http://localhost:8080/boleto/bradesco/'
CHAVE_UNICA = ''


def gera_boleto_bradesco(resp_usuario_id, invoice, days=7, second_copy=False):
    '''
    Receives a dict filled with the data that will be sent to the billet generator
    and returns a permalink to the billet generated.
    '''

    user = User.objects.get(pk=int(resp_usuario_id))
    profile = user.get_profile()
    person = profile.person

    d = Document()
    t = TypeDocument.objects.get(description='CPF')
    try:
        cpf = person.document.get(typeDocument__id=t.id).document
    except:
        cpf = ''
    try:
        addr = endereco = person.address.all()[0]
    except:
        addr = endereco = None
    data = BradescoBilletData.objects.all()[0]

    org = Organization.objects.filter(
        organization__isnull=True).filter(person__profile__user=user)[0]
    inv = invoice

    org.current_invoice = inv
    org.save()
    if inv.billet_url is not None and len(inv.billet_url) > 5 and not second_copy:
        return inv.billet_url
    else:
        dados = {}
        # INFORMANDO DADOS SOBRE O CEDENTE (quem vai receber).
        dados['cedente_nome'] = data.cedente_nome
        dados['cedente_cnpj'] = data.cedente_cnpj

        # INFORMANDO DADOS SOBRE O SACADO (quem vai pagar).
        dados['sacado_nome'] = person.name
        dados['sacado_cpf'] = cpf

        # Informando o endereço do sacado.
        try:
            dados['enderecosac_uf'] = str(endereco.city.state.shortName)
        except:
            dados['enderecosac_uf'] = ''
        try:
            dados['enderecosac_localidade'] = endereco.city.name
        except:
            dados['enderecosac_localidade'] = ''
        try:
            dados['enderecosac_cep'] = endereco.zipCode
        except:
            dados['enderecosac_cep'] = ''
        try:
            dados['enderecosac_bairro'] = str(endereco.neighborhood)
        except:
            dados['enderecosac_bairro'] = ''
        try:
            dados['enderecosac_logradouro'] = endereco.addressLine1
        except:
            dados['enderecosac_logradouro'] = ''
        try:
            dados['enderecosac_numero'] = endereco.addressNumber
        except:
            dados['enderecosac_numero'] = ''

        # INFORMANDO DADOS SOBRE O SACADOR AVALISTA (aquele que é contactado em
        # caso de problemas).
        dados['sacadoravalista_nome'] = data.sacadoravalista_nome
        dados['sacadoravalista_cnpj'] = data.sacadoravalista_cnpj

        # Informando o endereço do sacador avalista.
        dados['enderecosacaval_uf'] = data.enderecosacaval_uf.shortName
        dados['enderecosacaval_localidade'] = data.enderecosacaval_localidade
        dados['enderecosacaval_cep'] = data.enderecosacaval_cep
        dados['enderecosacaval_bairro'] = data.enderecosacaval_bairro
        dados['enderecosacaval_logradouro'] = data.enderecosacaval_logradouro
        dados['enderecosacaval_numero'] = data.enderecosacaval_numero

        # INFORMANDO OS DADOS SOBRE O TÍTULO.

        # Informando dados sobre a conta bancaria do titulo.
        dados['contabancaria_numerodaconta'] = data.contabancaria_numerodaconta
        dados[
            'contabancaria_numerodaconta_digito'] = data.contabancaria_numerodaconta_digito
        dados['contabancaria_carteira'] = data.contabancaria_carteira
        dados['contabancaria_agencia'] = data.contabancaria_agencia
        dados['contabancaria_agencia_digito'] = data.contabancaria_agencia_digito

        # Código fornecido pelo Banco para identificação do título ou identificação
        # do título atribuído pelo emissor do título de cobrança.
        dados['titulo_nossonumero'] = ("%0.11d") % inv.id
        digito = 0
        for p in str(inv.id):
            digito += int(p)
        digito = digito % 10
        dados['titulo_digitodonossonumero'] = str(digito)

        dados['titulo_deducao'] = "0.00"
        dados['titulo_mora'] = "0.00"
        dados['titulo_acrecimo'] = "0.00"
        dados['titulo_valorcobrado'] = "0.00"
        dados['titulo_desconto'] = "0.00"
        dados['titulo_valor'] = str(inv.ammount)
        dados['titulo_datadodocumento'] = str(inv.date)
        dados['titulo_datadovencimento'] = str(inv.due_date)

        # INFORMANDO OS DADOS SOBRE O BOLETO.
        dados['boleto_localpagamento'] = "Pagável preferencialmente no Bradesco."
        dados['boleto_instrucaoaosacado'] = "Pode ser pago em quaisquer agências."
        dados['boleto_instrucao1'] = "Após vencimento cobrar 50% de multa e 100% de juros ao dia."
        #dados['boleto_instrucao2'] = "PARA PAGAMENTO 2 até Amanhã Não cobre!"
        #dados['boleto_instrucao3'] = "PARA PAGAMENTO 3 até Depois de amanhã, OK, não cobre."
        #dados['boleto_instrucao4'] = "PARA PAGAMENTO 4 até 04/xx/xxxx de 4 dias atrás COBRAR O VALOR DE: R$ 01,00"
        #dados['boleto_instrucao5'] = "PARA PAGAMENTO 5 até 05/xx/xxxx COBRAR O VALOR DE: R$ 02,00"
        #dados['boleto_instrucao6'] = "PARA PAGAMENTO 6 até 06/xx/xxxx COBRAR O VALOR DE: R$ 03,00"
        #dados['boleto_instrucao7'] = "PARA PAGAMENTO 7 até xx/xx/xxxx COBRAR O VALOR QUE VOCÊ QUISER!"
        #dados['boleto_instrucao8'] = "APÓS o Vencimento, Pagável Somente na Rede X."

        for p in dados.keys():
            dados[p] = smart_str(dados[p])

        url = URL_GERADOR_BOLETOS
        data = urllib.urlencode(dados)
        # print datetime.now().strftime("%y-%m-%d %H:%M:%S")
        #raise Exception(url)
        # if the data parameter is here, it's a POST request
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        the_page = response.read()

        if len(the_page) == 40:
            inv.billet_url = url + the_page
            inv.save()
            return url + the_page
        else:
            return False


def gera_boleto_bradesco_inscricao(resp_usuario_id, days=7):
    '''
    Receives a dict filled with the data that will be sent to the billet generator
    and returns a permalink to the billet generated.
    '''
    from gestorpsi import settings

    user = User.objects.get(pk=int(resp_usuario_id))
    profile = user.get_profile()
    person = profile.person

    d = Document()
    t = TypeDocument.objects.get(description='CPF')
    try:
        cpf = person.document.get(typeDocument__id=t.id).document
    except:
        cpf = ''
    try:
        addr = endereco = person.address.all()[0]
    except:
        addr = endereco = None
    if BradescoBilletData.objects.all():  # condicacao adicionada para evitar interrupcao no formulario de cadastro em 15/04/2013 (czd)
        data = BradescoBilletData.objects.all()[0]
    else:
        data = None

    org = Organization.objects.filter(
        organization__isnull=True).filter(person__profile__user=user)[0]
    inv = Invoice(organization=org, status=1)
    due_date = (datetime.now() + timedelta(days=days))
    inv.due_date = due_date.strftime("%Y-%m-%d")
    expiry_date = (due_date + relativedelta(months=1)
                   ).replace(day=org.default_payment_day)
    inv.expiry_date = expiry_date.strftime("%Y-%m-%d")
    try:
        if float(data.inscription_default_value) > 0:
            inv.ammount = str(data.inscription_default_value)
        else:
            inv.ammount = str(INSCRIPTION_DEFAULT_VALUE)
    except:
        inv.ammount = str(INSCRIPTION_DEFAULT_VALUE)

    inv.save()

    org.current_invoice = inv
    org.save()

    if inv.billet_url is not None and len(inv.billet_url) > 5:
        return inv.billet_url
    else:
        # condicacao adicionada para evitar interrupcao no formulario de
        # cadastro em 15/04/2013 (czd)
        if data:
            dados = {}
            # INFORMANDO DADOS SOBRE O CEDENTE (quem vai receber).
            dados['cedente_nome'] = data.cedente_nome
            dados['cedente_cnpj'] = data.cedente_cnpj

            # INFORMANDO DADOS SOBRE O SACADO (quem vai pagar).
            dados['sacado_nome'] = person.name
            dados['sacado_cpf'] = cpf

            # Informando o endereço do sacado.
            try:
                dados['enderecosac_uf'] = str(endereco.city.state.shortName)
            except:
                dados['enderecosac_uf'] = ''
            try:
                dados['enderecosac_localidade'] = endereco.city.name
            except:
                dados['enderecosac_localidade'] = ''
            try:
                dados['enderecosac_cep'] = endereco.zipCode
            except:
                dados['enderecosac_cep'] = ''
            try:
                dados['enderecosac_bairro'] = str(endereco.neighborhood)
            except:
                dados['enderecosac_bairro'] = ''
            try:
                dados['enderecosac_logradouro'] = endereco.addressLine1
            except:
                dados['enderecosac_logradouro'] = ''
            try:
                dados['enderecosac_numero'] = endereco.addressNumber
            except:
                dados['enderecosac_numero'] = ''

            # INFORMANDO DADOS SOBRE O SACADOR AVALISTA (aquele que é
            # contactado em caso de problemas).
            dados['sacadoravalista_nome'] = data.sacadoravalista_nome
            dados['sacadoravalista_cnpj'] = data.sacadoravalista_cnpj

            # Informando o endereço do sacador avalista.
            dados['enderecosacaval_uf'] = None if not hasattr(
                data.enderecosacaval_uf, "shortName") else data.enderecosacaval_uf.shortName
            dados['enderecosacaval_localidade'] = data.enderecosacaval_localidade
            dados['enderecosacaval_cep'] = data.enderecosacaval_cep
            dados['enderecosacaval_bairro'] = data.enderecosacaval_bairro
            dados['enderecosacaval_logradouro'] = data.enderecosacaval_logradouro
            dados['enderecosacaval_numero'] = data.enderecosacaval_numero

            # INFORMANDO OS DADOS SOBRE O TÍTULO.

            # Informando dados sobre a conta bancaria do titulo.
            dados['contabancaria_numerodaconta'] = data.contabancaria_numerodaconta
            dados[
                'contabancaria_numerodaconta_digito'] = data.contabancaria_numerodaconta_digito
            dados['contabancaria_carteira'] = data.contabancaria_carteira
            dados['contabancaria_agencia'] = data.contabancaria_agencia
            dados['contabancaria_agencia_digito'] = data.contabancaria_agencia_digito

            # Código fornecido pelo Banco para identificação do título ou identificação
            # do título atribuído pelo emissor do título de cobrança.
            dados['titulo_nossonumero'] = ("%0.11d") % inv.id
            digito = 0
            for p in str(inv.id):
                digito += int(p)
            digito = digito % 10
            dados['titulo_digitodonossonumero'] = str(digito)

            dados['titulo_deducao'] = "0.00"
            dados['titulo_mora'] = "0.00"
            dados['titulo_acrecimo'] = "0.00"
            dados['titulo_valorcobrado'] = "0.00"
            dados['titulo_desconto'] = "0.00"
            dados['titulo_valor'] = str(inv.ammount)
            dados['titulo_datadodocumento'] = str(inv.date)
            dados['titulo_datadovencimento'] = str(inv.due_date)
            dados['titulo_numerododocumento'] = str(inv.id)

            # INFORMANDO OS DADOS SOBRE O BOLETO.
            dados['boleto_localpagamento'] = "Pagável preferencialmente no Bradesco."
            dados['boleto_instrucaoaosacado'] = "Pode ser pago em quaisquer agências."
            dados[
                'boleto_instrucao1'] = "Após vencimento cobrar 50% de multa e 100% de juros ao dia."
            #dados['boleto_instrucao2'] = "PARA PAGAMENTO 2 até Amanhã Não cobre!"
            #dados['boleto_instrucao3'] = "PARA PAGAMENTO 3 até Depois de amanhã, OK, não cobre."
            #dados['boleto_instrucao4'] = "PARA PAGAMENTO 4 até 04/xx/xxxx de 4 dias atrás COBRAR O VALOR DE: R$ 01,00"
            #dados['boleto_instrucao5'] = "PARA PAGAMENTO 5 até 05/xx/xxxx COBRAR O VALOR DE: R$ 02,00"
            #dados['boleto_instrucao6'] = "PARA PAGAMENTO 6 até 06/xx/xxxx COBRAR O VALOR DE: R$ 03,00"
            #dados['boleto_instrucao7'] = "PARA PAGAMENTO 7 até xx/xx/xxxx COBRAR O VALOR QUE VOCÊ QUISER!"
            #dados['boleto_instrucao8'] = "APÓS o Vencimento, Pagável Somente na Rede X."

            for p in dados.keys():
                dados[p] = smart_str(dados[p])

            url = URL_GERADOR_BOLETOS
            data = urllib.urlencode(dados)
            # print datetime.now().strftime("%y-%m-%d %H:%M:%S")
            #raise Exception(url)
            # if the data parameter is here, it's a POST request
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            the_page = response.read()

            if len(the_page) == 40:
                inv.billet_url = url + the_page
                inv.save()
                return url + the_page
            else:
                return False
