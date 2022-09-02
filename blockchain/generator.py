from sha3 import keccak_256


class Generator:
    def __init__(self, phone_number, password):
        self.phone_number = phone_number
        self.password = password

    def generate_private_key(self):
        phone_number_first_part = self.phone_number[:len(self.phone_number) // 2]
        phone_number_second_part = self.phone_number[len(self.phone_number) // 2:]
        password_first_part = self.password[:len(self.password) // 2]
        password_second_part = self.password[len(self.password) // 2:]

        private_key = keccak_256(phone_number_first_part.encode('utf-8')).digest()
        private_key = keccak_256(phone_number_second_part.encode('utf-8')).digest()
        private_key = keccak_256(password_first_part.encode('utf-8')).digest()
        private_key = keccak_256(password_second_part.encode('utf-8')).digest()
        private_key = hex(int.from_bytes(private_key, 'big'))
        return private_key
