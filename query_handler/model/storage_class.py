from enum import Enum

class StorageClass(str, Enum):
    STANDARD = 'STANDARD'
    STANDARD_IA = 'STANDARD_IA'
    GLACIER_IR = 'GLACIER_IR'
    GLACIER = 'GLACIER'