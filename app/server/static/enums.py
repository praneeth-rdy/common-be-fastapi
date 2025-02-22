from enum import Enum


class AccountStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    RESTRICTED = 'RESTRICTED'
    SIGN_UP = 'SIGN_UP'


class TokenType(str, Enum):
    BEARER = 'bearer'
    RESET_PASSWORD = 'reset_password'
    REFRESH = 'refresh'
    SIGN_UP = 'sign_up'
