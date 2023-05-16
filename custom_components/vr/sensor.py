

"""Platform for sensor integration."""
from __future__ import annotations

from datetime import timedelta,datetime
from distutils.command.config import config
import logging
from multiprocessing import Event
import voluptuous
import json
import re


import requests
from homeassistant import const
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant import util
from homeassistant.helpers import config_validation
import pandas as pd
_LOGGER = logging.getLogger(__name__)


DEFAULT_NAME = 'Vr refeição'
UPDATE_FREQUENCY = timedelta(minutes=10)
EMAIL ="email"
PASSWORD = "password"

PLATFORM_SCHEMA = config_validation.PLATFORM_SCHEMA.extend(
    {
        voluptuous.Required(EMAIL): config_validation.string,
        voluptuous.Required(PASSWORD): config_validation.string,

        
       

    }
)


def setup_platform(
    hass,
    config,
    add_entities,
    discovery_info
):
    """Set up the Vr refeição sensors."""
  
    add_entities([VRSensor(config)])


class VRSensor(SensorEntity):
    """Representation of a VR sensor."""

    def __init__(self,config):
        """Initialize a new copasa sensor."""
        self._attr_name = "vr refeicao"
        self.config = config
        self.transactions = None
        self.refresh_token = None
        self.saldo = None
       

       


    @property
    def icon(self):
        """Return icon."""
        return "mdi:bank"

           
    @property
    def state(self):
        """Returns the state of the sensor."""
        return self._state
    
    @util.Throttle(UPDATE_FREQUENCY)
    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self.transactions = transactions()
        self.refresh_token = get_refresh_token(self.config)
        self.saldo = get_cards()
        self._state =  self.saldo
  
      
        
 

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        self._attributes = {
            "transactions": self.transactions,

        }
        return  self._attributes

  



   
def get_clientId():
    url = "https://portal-trabalhador.vr.com.br/static/js/main.a93bf1b4.chunk.js"
    resp = requests.get(url)
    data = resp.text
    match = re.search(r'clientId:"([^"]+)"', data)

    if match:
        clientId = match.group(1)
    return clientId   

def get_code():
    clientId = get_clientId()
    url = 'https://api.vr.com.br/oauth/grant-code'
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }

    data = f'{{"client_id":"{clientId}","redirect_uri":"http://localhost/"}}'

    resp = requests.post(url, headers=headers, data=data)
    data = json.loads(resp.content)
    code = data['redirect_uri'].replace('http://localhost/?code=','')
    return code

def get_token():
    url = "https://api.vr.com.br/oauth/access-token"
    code = get_code()
    clientId = self.get_clientId()
    headers = CaseInsensitiveDict()
    headers["Authorization"] = "Basic MDhkZGMyNzktYjBhZS0zYWVlLWI2MjgtN2I0ZDVkYzAzZjVjOjM3ZjE0MjRkLTE1MDQtM2QwYi1hZjJiLTc0OTdjYzFkMWU1OQ=="
    headers["Content-Type"] = "application/json;charset=UTF-8"
    headers["Accept"] = "application/json, text/plain, */*"
    headers["Client_id"] = clientId
    data = f'{{"grant_type":"authorization_code","code":"{code}"}}'


    resp = requests.post(url, headers=headers, data=data)
    token = json.loads(resp.content)
    return token

def get_refresh_token(config):
    clientId = get_clientId()
    token =get_token()
    url = "https://api.vr.com.br/autenticacao-usuario-rhsso/v3/access-token"
    headers = CaseInsensitiveDict()

    headers["Client_id"] = clientId
    headers["Access_token"] = token['access_token']
    data = f'{{"email":"{config['EMAIL']}","password":"{config['PASSWORD']"}}'
    resp = requests.post(url, headers=headers, data=data)
    refresh_token = json.loads(resp.content)
    return refresh_token


def get_cards():

    refresh_token = get_refresh_token()
    url = "https://pt-bff-painel-portal-trabalhador-prd.vr.com.br/cards/v2/"
    headers = CaseInsensitiveDict()
    headers["Authorization"] = refresh_token['access_token']
    headers["Issuer"] = "VRPAT"
    resp = requests.get(url, headers=headers)
    data = json.loads(resp.content)

    saldo = data['result'][0]['saldo']
    nomeProduto = data['result'][0]['nomeProduto']
    nomeCartao = data['result'][0]['nomeCartao']
    ultimaDataCredito = data['result'][0]['ultimaDataCredito']
    tokenCartao = data['result'][0]['tokenCartao']
    numeroConta = data['result'][0]['numeroConta']
    data = {
            'nomeProduto':nomeProduto,
            'saldo':saldo,
            'nomeCartao':nomeCartao,
            'ultimaDataCredito':ultimaDataCredito,
            'tokenCartao':tokenCartao,
            'numeroConta':numeroConta
          }
    return data
def transactions():
    transactions= []
    cards = get_cards()
    refresh_token = get_refresh_token()
    tokenCartao =  cards['tokenCartao']
    numeroConta =  cards['numeroConta']
    url = f'https://pt-bff-extrato-portal-trabalhador-prd.vr.com.br/extract/v2/transactionsbydays/{tokenCartao}/{numeroConta}/15/0/20'

    headers = CaseInsensitiveDict()
    headers["Authorization"] = refresh_token['access_token']
    headers["Issuer"] = "VRPAT"
    headers["Accept"] = "application/json, text/plain, */*"
    resp = requests.get(url, headers=headers)
    data = json.loads(resp.content)
    for item in data['result']:
        transactions.append(item)
    return transactions

