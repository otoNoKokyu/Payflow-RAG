from pydantic import BaseModel, model_validator

class PaymentRequest(BaseModel):
    dateStart: str | None = None
    dateEnd: str | None = None
    payment_status: str | None = None
    payment_status_bulk_count: int | None = None

    @model_validator(mode='after')
    def validate_payment_request(self) -> 'PaymentRequest':
        if self.dateStart and self.dateEnd:
            return self
        
        if self.payment_status and self.payment_status_bulk_count is not None:
            return self
            
        raise ValueError("Either (dateStart and dateEnd) or (payment_status and payment_status_bulk_count) must be provided")
