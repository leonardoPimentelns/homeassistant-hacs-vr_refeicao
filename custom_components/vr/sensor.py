

"""Platform for sensor integration."""
from __future__ import annotations

from datetime import timedelta,datetime
from distutils.command.config import config
import logging
from multiprocessing import Event
import voluptuous
import json


from barcode.writer import SVGWriter
import barcode
EAN = barcode.get_barcode_class('itf')
barcode.PROVIDED_BARCODES
import requests
from homeassistant import const
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant import util
from homeassistant.helpers import config_validation
import pandas as pd
_LOGGER = logging.getLogger(__name__)


DEFAULT_NAME = 'Copasa'
UPDATE_FREQUENCY = timedelta(minutes=10)
REGISTRATION ="matricula"
IDENTIFIER = "identificador"
CPF_CNPJ= "cpf_cnpj"

PLATFORM_SCHEMA = config_validation.PLATFORM_SCHEMA.extend(
    {
        voluptuous.Required(REGISTRATION): config_validation.string,
        voluptuous.Required(IDENTIFIER): config_validation.string,
        voluptuous.Required(CPF_CNPJ): config_validation.string
        
       

    }
)


def setup_platform(
    hass,
    config,
    add_entities,
    discovery_info
):
    """Set up the Copasa sensors."""
  
    add_entities([InvoiceSensor(config)])


class InvoiceSensor(SensorEntity):
    """Representation of a Copasa sensor."""

    def __init__(self,config):
        """Initialize a new copasa sensor."""
        self._attr_name = "copasa"
        self.live_event = None
        self.invoice_details = None
        self.paid_invoices = None
        self.open_invoices = None
        self.config = config
        self.costumer_id = None

       


    @property
    def icon(self):
        """Return icon."""
        return "mdi:bank"


    @util.Throttle(UPDATE_FREQUENCY)
    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self.costumer_id = get_costumer_id(self.config)
        self.invoice_details = get_invoice_details(self.config)
        self.paid_invoices = get_paid_invoices(self.config)
        self.open_invoices = get_open_invoices(self.config)
        self.matches = ""
        
            


    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        self._attributes = {
            "invoice_details": self.invoice_details,
            "paid_invoices": self.paid_invoices,
            "open_invoices": self.open_invoices,

        }
        return  self._attributes

  
def get_costumer_id(config):
    
    url = "https://copasaportalprd.azurewebsites.net/Copasa.Portal/Services/MyAccount_ListIdentifiers_GetIdentifiers" 
    token ="CpfCnpj="+config[CPF_CNPJ]+"&url=https://copasaproddyn365api.azurewebsites.net"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    resp = requests.post(url,data=token,headers=headers)
    costumer = json.loads(resp.content)
    costumer = costumer[0]['contactid']
    return costumer
   



def get_invoice_details(config):
    reference = pd.to_datetime('today')-pd.DateOffset(months=1)
    reference = reference.strftime('%Y%m')
    url = "https://copasaproddyn365api.azurewebsites.net/api/Ocorrencia/MyAccount_DuplicateOfAccounts_GetInvoiceDetails" 
    token= {"Registration":config[REGISTRATION],"Reference":reference,"Company":"Copasa"}
    
    resp = requests.post(url, json = token)
    invoice_details = json.loads(resp.content)
   
    return  invoice_details
    



def get_paid_invoices(config):
    url = "https://copasaproddyn365api.azurewebsites.net/api/Ocorrencia/MyAccount_DuplicateOfAccounts_GetPaidInvoices"
    token = {"Identifier":config[IDENTIFIER],"Registration":config[REGISTRATION],"idCpfCnpj":get_costumer_id(config),"Company":"Copasa"}
    
    resp = requests.post(url, json = token)
    invoices = json.loads(resp.content)
    return  invoices



def get_open_invoices(config):
    url = "https://copasaproddyn365api.azurewebsites.net/api/Ocorrencia/MyAccount_DuplicateOfAccounts_GetOpenInvoices"
    token = {"Identifier":config[IDENTIFIER],"Registration":config[REGISTRATION],"idCpfCnpj":get_costumer_id(config),"Company":"Copasa"}
    
    resp = requests.post(url, json = token)
    invoices = json.loads(resp.content)
    barcode = invoices['faturas'][0]['numeroCodigoBarras']
    numeroFatura = invoices['faturas'][0]['numeroFatura']
    valorUltimaFatura = get_paid_invoices(config)
    valorUltimaFatura =valorUltimaFatura['contas'][0]['valorTotalFatura'].replace('.','').replace(',','.')
    valorFatura = invoices['faturas'][0]['valorFatura'].replace('.','').replace(',','.')
    diferenca = (float(valorFatura) - float(valorUltimaFatura)) /(float(valorUltimaFatura))*100 
    referencia = invoices['faturas'][0]['referencia']
    dataVencimento = invoices['faturas'][0]['dataVencimento']
    dataVencimento = datetime.strptime(dataVencimento, '%Y%m%d').strftime("%d-%m-%Y")
    referencia = datetime.strptime(referencia, '%Y%m').strftime("%m-%Y")
    qrcode ="https://wwwapp.copasa.com.br/servicos/WebServiceAPI/Prd/CopasaAtende/api/fatura/exibe/QRCode/"+config[REGISTRATION]+"/"+numeroFatura+"/"+referencia+"/"+dataVencimento+"/"+valorFatura+""
    invoices = {"valorFatura":valorFatura,"valorUltimaFatura":valorUltimaFatura,"diferenca":round(diferenca,2),"faturas":{"numeroFatura":numeroFatura,'referencia':referencia,"dataVencimento":dataVencimento,"qrcode":qrcode,"barcode":barcode} }
    return  invoices
    