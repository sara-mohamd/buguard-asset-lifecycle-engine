from pydantic import BaseModel, ConfigDict, Field, AliasChoices, model_validator, IPvAnyAddress, computed_field
from typing import List, Dict, Any, Union, Optional
from typing_extensions import Annotated, Literal
from datetime import datetime
import uuid
import re

from src.models.asset import AssetType, AssetStatus

# FQDN Regex for Domain and Subdomain
FQDN_REGEX = re.compile(r"^(?=.{1,253}\.?$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}\.?$")

class AssetBaseCommon(BaseModel):
    """Fields common to all asset types."""
    status: AssetStatus = AssetStatus.active
    source: str = Field("manual", description="Source of the asset discovery")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_", "metadata"))

class DomainAsset(AssetBaseCommon):
    type: Literal[AssetType.domain]
    value: str

    @model_validator(mode='after')
    def validate_fqdn(self):
        if not FQDN_REGEX.match(self.value):
            raise ValueError(f"Value '{self.value}' is not a valid FQDN for domain")
        return self

class SubdomainAsset(AssetBaseCommon):
    type: Literal[AssetType.subdomain]
    value: str

    @model_validator(mode='after')
    def validate_fqdn(self):
        if not FQDN_REGEX.match(self.value):
            raise ValueError(f"Value '{self.value}' is not a valid FQDN for subdomain")
        return self

class IpAddressAsset(AssetBaseCommon):
    type: Literal[AssetType.ip_address]
    value: IPvAnyAddress
    
    @computed_field
    @property
    def value_str(self) -> str:
        return str(self.value)

class ServiceAsset(AssetBaseCommon):
    type: Literal[AssetType.service]
    value: str

    @model_validator(mode='after')
    def validate_service(self):
        parts = self.value.split('/')
        if len(parts) != 2:
            raise ValueError(f"Service value '{self.value}' must be in format 'port/protocol'")
        port, proto = parts
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            raise ValueError("Service port must be an integer between 1 and 65535")
        if proto.lower() not in ("tcp", "udp"):
            raise ValueError("Service protocol must be tcp or udp")
        return self

class CertificateAsset(AssetBaseCommon):
    type: Literal[AssetType.certificate]
    value: str

    @model_validator(mode='after')
    def validate_certificate(self):
        if self.value.startswith("CN="):
            cn_val = self.value[3:]
            if not FQDN_REGEX.match(cn_val):
                raise ValueError(f"Certificate CN '{cn_val}' is not a valid FQDN")
        
        expires = self.metadata.get("expires")
        if expires:
            try:
                datetime.fromisoformat(expires.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("metadata 'expires' must be ISO-8601 formatted string")
        return self

class TechnologyAsset(AssetBaseCommon):
    type: Literal[AssetType.technology]
    value: str

# Use a Discriminated Union so Pydantic automatically routes the payload to the correct schema based on the 'type' field.
AssetCreate = Annotated[
    Union[DomainAsset, SubdomainAsset, IpAddressAsset, ServiceAsset, CertificateAsset, TechnologyAsset],
    Field(discriminator="type")
]

class AssetUpdate(BaseModel):
    """Schema for updating an existing asset. Identity fields (type, value) cannot be changed."""
    status: Optional[AssetStatus] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias=AliasChoices("metadata_", "metadata"))

class AssetResponse(AssetBaseCommon):
    id: uuid.UUID
    type: AssetType
    value: str
    first_seen: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PaginatedAssetResponse(BaseModel):
    items: List[AssetResponse]
    total: int
