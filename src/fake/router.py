from fastapi import BackgroundTasks
from .schema import PaymentRequest
from .service import FakeService
from ..core.BaseResponse import WrappedRouter
from datetime import datetime
import os

fakeRouter = WrappedRouter(prefix="/fake")

@fakeRouter.post("/create-payment")
def create_payment(data: PaymentRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger fake payment CSV generation in the background.
    """
    # Determine filename based on dateStart (month and year)
    if data.dateStart:
        try:
            dt = datetime.strptime(data.dateStart, "%Y-%m-%d")
        except (ValueError, TypeError):
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    filename = f"{dt.strftime('%B_%Y')}_payments.csv"
    
    # Define the output file path using the dynamic filename
    file_path = os.path.join(os.path.dirname(__file__), filename)
    
    # Schedule the generation as a background task
    background_tasks.add_task(FakeService.generate_payment_csv, data, file_path)
    
    # Return a success message (wrapped in BaseResponse by WrappedRouter)
    return {"message": "CSV generation started"}
