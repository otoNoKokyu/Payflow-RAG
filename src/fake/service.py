import csv
import random
import os
from datetime import datetime, timedelta
from .schema import PaymentRequest

import logging

# Set up logging
logger = logging.getLogger(__name__)

class FakeService:
    @staticmethod
    def generate_payment_csv(data: PaymentRequest, file_path: str):
        """
        Generates fake payment data and saves it to a CSV file.
        """
        logger.info(f"Starting CSV generation for status: {data.payment_status or 'random'} at {file_path}")
        
        try:
            # Determine date range
            try:
                start_dt = datetime.strptime(data.dateStart, "%Y-%m-%d") if data.dateStart else datetime.now() - timedelta(days=30)
                end_dt = datetime.strptime(data.dateEnd, "%Y-%m-%d") if data.dateEnd else datetime.now()
            except (ValueError, TypeError) as e:
                logger.warning(f"Date parsing failed, using defaults: {e}")
                start_dt = datetime.now() - timedelta(days=30)
                end_dt = datetime.now()
            
            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt
                
            statuses = ["SUCCESS", "PENDING", "FAILED", "REFUNDED", "CANCELLED"]
            records = []
            
            # Determine how many to generate
            count = data.payment_status_bulk_count if data.payment_status_bulk_count else 10
            
            for _ in range(count):
                # If a specific status is requested, use it. Otherwise, pick random.
                status = data.payment_status if data.payment_status else random.choice(statuses)
                records.append(FakeService._create_record(start_dt, end_dt, status))
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["payment_id", "date", "amount", "status", "currency"])
                writer.writeheader()
                writer.writerows(records)
            
            logger.info(f"Successfully generated CSV with {len(records)} records at {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate CSV at {file_path}: {str(e)}", exc_info=True)

    @staticmethod
    def _create_record(start_date: datetime, end_date: datetime, status: str) -> dict:
        delta = end_date - start_date
        random_days = random.randrange(delta.days + 1) if delta.days > 0 else 0
        random_seconds = random.randrange(86400)
        payment_date = start_date + timedelta(days=random_days, seconds=random_seconds)
        
        return {
            "payment_id": f"PAY-{random.randint(100000, 999999)}",
            "date": payment_date.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": round(random.uniform(10.0, 1000.0), 2),
            "status": status,
            "currency": "USD"
        }
