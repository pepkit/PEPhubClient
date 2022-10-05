from typing import Optional

from pydantic import BaseModel

# PEPHUB_BASE_URL = "https://pephub.databio.org/"
# PEPHUB_PEP_API_BASE_URL = "https://pephub.databio.org/pep/"
# PEPHUB_LOGIN_URL = "https://pephub.databio.org/auth/login"
PEPHUB_BASE_URL = "http://0.0.0.0:8000/"
PEPHUB_PEP_API_BASE_URL = "http://0.0.0.0:8000/pep/"
PEPHUB_LOGIN_URL = "http://127.0.0.1:8000/auth/login"


class RegistryPath(BaseModel):
    protocol: Optional[str]
    namespace: str
    item: str
    subitem: Optional[str]
    tag: Optional[str]