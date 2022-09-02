from eth_account import account
from web3 import Web3, HTTPProvider
from json import load
from sha3 import keccak_256
import requests
from time import sleep, time
from datetime import datetime
from generator import Generator
import os
from collections import namedtuple


class AccountManager:
    def __init__(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(current_dir, "network.json")) as network:
            data = load(network)
            self.rpcUrl = data["rpcUrl"]
            self.gas_url = data["gasPriceUrl"]
            self.default_price = data["defaultGasPrice"]

        with open(os.path.join(current_dir, "registrar.abi")) as abi:
            self.reg_abi = abi.read()
        with open(os.path.join(current_dir, "registrar.bin")) as bin:
            self.reg_bytecode = bin.read()
        with open(os.path.join(current_dir, "payments.abi")) as abi:
            self.pay_abi = abi.read()
        with open(os.path.join(current_dir, "payments.bin")) as bin:
            self.pay_bytecode = bin.read()

        with open(os.path.join(current_dir, "registrar.json")) as registrar:
            data = load(registrar)
            self.address_reg = data["registrar"]
            self.address_pay = data["payments"]

        self.web3 = Web3(HTTPProvider(self.rpcUrl))
        self.private_key = ""
        self.account = ""
        self.contract_pay = self.web3.eth.contract(address = self.address_pay, abi = self.pay_abi)

    def login(self, phone_number, password):
        generator = Generator(phone_number, password)
        self.private_key = generator.generate_private_key()
        self.account = self.web3.eth.account.privateKeyToAccount(self.private_key)

    def logout(self):
        self.private_key = ""
        self.account = ""

    def is_logged_in(self):
        return self.private_key != ""
    
    def convert(self, balance):
        if self.is_logged_in():
            if balance == 0:
                return str(balance) + " poa"
            if balance < 10**3:
                return str(balance) + " wei"
            elif balance < 10**6:
                balance = balance / 10**3
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " kwei"
                return str(balance) + " kwei"
            elif balance < 10**9:
                balance = balance / 10**6
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " mwei"
                return str(balance) + " mwei"
            elif balance < 10**12:
                balance = balance / 10**9
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " gwei"
                return str(balance) + " gwei"
            elif balance < 10**15:
                balance = balance / 10**12
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " szabo"
                return str(balance) + " szabo"
            elif balance < 10**18:
                balance = balance / 10**15
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " finney"
                return str(balance) + " finney"
            else:
                balance = balance / 10**18
                if len(str(balance)) > 8:
                    return "{0:.6f}".format(balance).rstrip('0').rstrip(".") + " poa"
                return str(balance) + " poa"
        else:
            print("Авторизуйся, додик")

    def make_transaction(self, reciever, value):
        if self.is_logged_in():
            # Получаем текущий баланс пользователя
            balance = self.web3.eth.getBalance(self.account.address)

            # Запрашиваем текущий gas price
            data = requests.get(self.gas_url)
            gas = self.web3.eth.estimateGas({"to": reciever, "from": self.account.address, "value": value})
            if data.status_code != 200:
                gas_price = self.default_price
            else:
                gas_price = int(data.json()["fast"] * 10**9)
            if balance < gas * gas_price:
                print("Not enough funds to send this value")
                return

            # Формируем транзакцию
            tx = {
                "to": reciever,
                "nonce": self.web3.eth.getTransactionCount(self.account.address),
                "gas": gas,
                "gasPrice": gas_price,
                "value": int(value)
            }
            # Подписываем транзакцию
            sign = self.account.signTransaction(tx)
            #Получаем хэш транзакции
            tx_hash = self.web3.eth.sendRawTransaction(sign.rawTransaction)
            # Получаем полную информацию о транзакции
            tx_reciept = self.web3.eth.waitForTransactionReceipt(tx_hash)
            while tx_reciept["status"] != 1:
                sleep(0.1)
                tx_reciept = self.web3.eth.getTransactionReceipt(tx_hash)
        

            # Создаём транзакцию для записи о переводе в смарт - контракт
            tx_pay = {
                "from": self.account.address,
                "nonce": self.web3.eth.getTransactionCount(self.account.address),
                "gas": 1500000,
                "gasPrice": gas_price
            }
            # Извлекаем хэщ транзакции перевода
            tx_bytes = self.web3.toBytes(tx_reciept["transactionHash"])
            # Кладём транзакцию о переводе в контракт
            to_signed_pay = self.contract_pay.functions.add_payment(self.account.address, reciever, tx_bytes).buildTransaction(tx_pay)
            # Подписываем транзакцию
            signed_tx = self.account.signTransaction(to_signed_pay)

            # Получаем хэш транзакции
            pay_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            # Получаем полную информацию о транзакции
            pay_reciept = self.web3.eth.waitForTransactionReceipt(pay_hash)
            while pay_reciept["status"] != 1:
                sleep(0.1)
                pay_reciept = self.web3.eth.getTransactionReceipt(pay_hash)

            print("""Payment of {} to {} scheduled""".format(self.convert(int(value)), reciever))
            print("Transaction Hash:", tx_reciept["transactionHash"].hex())
            print("Your transaction added to your payments list!")
            print("Payment added:", pay_reciept["transactionHash"].hex())
        else:
            print("Авторизуйся, додик")

    def show_payments(self):
        if self.is_logged_in():
            # Получаем платежи текущего пользователя из контракта
            Payment = namedtuple('Payment', 'time direction sender value')
            payments = self.contract_pay.functions.get_payments_list(self.account.address).call()
            payments_to_return = []
            for payment in payments:
                data = self.web3.eth.getTransaction(payment.hex())
                if data["from"] == self.account.address: 
                    format  = "%m/%d/%Y %H:%M:%S"
                    date = datetime.fromtimestamp(self.web3.eth.getBlock(data["blockNumber"])["timestamp"])
                    time_sending = date.strftime(format)
                    to = data["to"]
                    value = int(data["value"])
                    processed_payment = Payment(time_sending, "TO", to, value)
                    payments_to_return.append(processed_payment)
                else:
                    format  = "%m/%d/%Y %H:%M:%S"
                    date = datetime.fromtimestamp(self.web3.eth.getBlock(data["blockNumber"])["timestamp"])
                    time_sending = date.strftime(format)
                    sender = data["from"]
                    value = int(data["value"])
                    processed_payment = Payment(time_sending, "FROM", sender, value)
                    payments_to_return.append(processed_payment)
            return payments_to_return
        else:
            print("Авторизуйся, додик")

    def get_balance(self):
        if self.is_logged_in():
            balance = self.web3.eth.getBalance(self.account.address)
            return balance
        else:
            print("Авторизуйся, додик")
