from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class RejectedRecord(BaseModel):
    index: int = Field(description="The index of the record in the incoming batch")
    record: Dict[str, Any] = Field(description="The raw payload that failed validation")
    errors: List[Dict[str, Any]] = Field(description="List of Pydantic validation errors")

class ImportReport(BaseModel):
    total_analyzed: int = Field(0, description="Total number of records in the batch")
    successful_creates: int = Field(0, description="Number of new assets created")
    successful_updates: int = Field(0, description="Number of existing assets updated")
    rejected_records: List[RejectedRecord] = Field(default_factory=list, description="Records that failed validation")
