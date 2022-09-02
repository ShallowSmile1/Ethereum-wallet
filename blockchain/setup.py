from web3 import Web3, HTTPProvider
from json import load, dump
from time import sleep
import requests


class Configurator:
    def __init__(self):
        with open("network.json") as network:
            data = load(network)
            self.rpcUrl = data["rpcUrl"]
            self.private_key = data["privKey"]
            self.gas_price_source = data["gasPriceUrl"]
            self.default_price = data["defaultGasPrice"]
            
        with open("registrar.abi") as abi:
            self.reg_abi = abi.read()
        with open("registrar.bin") as bin:
            self.reg_bytecode = bin.read()
        with open("payments.abi") as abi:
            self.pay_abi = abi.read()
        with open("payments.bin") as bin:
            self.pay_bytecode = bin.read()

        self.web3 = Web3(HTTPProvider(self.rpcUrl))
        self.account = self.web3.eth.account.privateKeyToAccount(self.private_key)

    def deploy(self):
        # Получаем баланс генезис - аккаунта
        balance = self.web3.eth.getBalance(self.account.address)

        # Создаём смарт - контракты для хранения транзакций и номеров телефона пользователей
        contract_reg = self.web3.eth.contract(abi = self.reg_abi, bytecode = self.reg_bytecode)
        contract_pay = self.web3.eth.contract(abi = self.pay_abi, bytecode = self.pay_bytecode)

        # Запрашиваем текущий gas price
        data = requests.get(self.gas_price_source)
        if data.status_code != 200:
            gas_price = self.default_price
        else:
            gas_price = int(data.json()["fast"] * 10**9)
        
        if balance < 1500000 * 2 * gas_price:
            print(f"No enough funds to send transaction. Your funds: {balance}")
            return

        # Создаём транзакцию для смарт - контракта, который будет хранить словарь: номер телефона -> адрес
        tx_reg = contract_reg.constructor().buildTransaction({
            "from": self.account.address,
            "nonce": self.web3.eth.getTransactionCount(self.account.address),
            "gas": 1500000,
            "gasPrice": gas_price
        })
        # Подписываем транзакцию с помощью своего аккаунта
        singned_reg = self.account.signTransaction(tx_reg)
        # Получаем хэш транзакции
        regHash = self.web3.eth.sendRawTransaction(singned_reg.rawTransaction)
        # Получаем полную информации о транзакции
        reg_reciept = self.web3.eth.waitForTransactionReceipt(regHash)
        while reg_reciept['status'] != 1:
            sleep(0.1)
            reg_reciept = self.web3.eth.getTransactionReceipt(regHash)
        # Записываем адрес смарт - контракта
        reg_address = reg_reciept["contractAddress"]

        # Создаём транзакцию для смарт - контракта, который будет хранить список транзакций пользователей
        tx_pay = contract_pay.constructor().buildTransaction({
            "from": self.account.address,
            "nonce": self.web3.eth.getTransactionCount(self.account.address),
            "gas": 1500000,
            "gasPrice": gas_price
        })
        singned_pay = self.account.signTransaction(tx_pay)
        payId = self.web3.eth.sendRawTransaction(singned_pay.rawTransaction)
        pay_reciept = self.web3.eth.waitForTransactionReceipt(payId)
        while pay_reciept['status'] != 1:
            sleep(0.1)
            pay_reciept = self.web3.eth.getTransactionReceipt(payId)
        pay_address = pay_reciept["contractAddress"]

        # Получаем адреса наших контрактов и записываем в файл
        print("KYC Registrar:", reg_address)
        print("Payment Handler:", pay_address)
        with open("registrar.json", 'w') as registrar:
            dump({"registrar": reg_address, "payments": pay_address}, registrar)
            