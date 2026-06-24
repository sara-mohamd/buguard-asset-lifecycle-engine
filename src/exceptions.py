class AssetDomainError(Exception):
    """Base exception for all asset domain errors."""
    pass

class AssetNotFoundError(AssetDomainError):
    """Raised when an asset is not found."""
    def __init__(self, asset_id: str):
        super().__init__(f"Asset with ID '{asset_id}' not found.")
        self.asset_id = asset_id

class AssetDuplicateError(AssetDomainError):
    """Raised when an asset already exists (e.g. duplicate type and value)."""
    def __init__(self, message: str = "Asset already exists."):
        super().__init__(message)
