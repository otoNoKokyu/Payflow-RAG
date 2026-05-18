
import uuid
import datetime
import os
from typing import Literal

import pandas as pd

from ..core.RAGCore import store
from .chunking import get_strategy


class ProccessData:
    def __init__(self,file_path:str):
        self.file_path = file_path

class ProcessPayment(ProccessData):

    def load(self):
        self.dataFrame=pd.read_csv(self.file_path)

    def transform(self):
        df = self.dataFrame.copy()
        # Normalize date column: handle both 'date' and 'created_at'
        if 'created_at' in df.columns:
            df['date'] = pd.to_datetime(df['created_at'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
            raise KeyError("Neither 'date' nor 'created_at' column found in CSV")

        # Group by date (Daily, Weekly, Monthly)
        self.daily_groups = df.groupby(df['date'].dt.date).agg({'amount': 'sum', 'payment_id': 'count'}).reset_index()
        self.weekly_groups = df.groupby(df['date'].dt.to_period('W')).agg({'amount': 'sum', 'payment_id': 'count'}).reset_index()
        self.monthly_groups = df.groupby(df['date'].dt.to_period('M')).agg({'amount': 'sum', 'payment_id': 'count'}).reset_index()

        # Group by currency
        self.currency_groups = df.groupby('currency').agg({'amount': 'sum', 'payment_id': 'count'}).reset_index()

        # Group by status
        self.status_groups = df.groupby('status').agg({'amount': 'sum', 'payment_id': 'count'}).reset_index()
    

    def tokenize(self):
        self.tokens = []
        
        def get_day_suffix(n):
            if 11 <= n <= 13:
                return 'th'
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

        def format_date(dt):
            return f"{dt.day}{get_day_suffix(dt.day)} {dt.strftime('%B %Y')}".lower()

        if hasattr(self, 'dataFrame'):
            for _, row in self.dataFrame.iterrows():
                dt = pd.to_datetime(row['date'])
                date_str = format_date(dt)
                self.tokens.append({
                    'text': f"Payment ID {row['payment_id']} on {date_str} for {row['amount']} {row['currency']} has status {row['status']}.",
                    'metadata': {
                        'type': 'individual',
                        'period_type': 'exact',
                        'payment_id': row['payment_id'],
                        'date_str': date_str,
                        'amount': float(row['amount']),
                        'currency': row['currency'],
                        'status': row['status']
                    }
                })
        
        if hasattr(self, 'daily_groups'):
            for _, row in self.daily_groups.iterrows():
                dt = pd.to_datetime(row['date'])
                date_str = format_date(dt)
                self.tokens.append({
                    'text': f"Daily summary for {date_str}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {
                        'type': 'daily_summary',
                        'period_type': 'day',
                        'start_date': date_str,
                        'end_date': date_str,
                        'count': int(row['payment_id']),
                        'amount': float(row['amount'])
                    }
                })

        if hasattr(self, 'weekly_groups'):
            for _, row in self.weekly_groups.iterrows():
                period = row['date']
                start_date = format_date(period.start_time)
                end_date = format_date(period.end_time)
                self.tokens.append({
                    'text': f"Weekly summary from {start_date} to {end_date}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {
                        'type': 'weekly_summary',
                        'period_type': 'week',
                        'start_date': start_date,
                        'end_date': end_date,
                        'count': int(row['payment_id']),
                        'amount': float(row['amount'])
                    }
                })

        if hasattr(self, 'monthly_groups'):
            for _, row in self.monthly_groups.iterrows():
                period = row['date']
                start_date = format_date(period.start_time)
                end_date = format_date(period.end_time)
                self.tokens.append({
                    'text': f"Monthly summary from {start_date} to {end_date}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {
                        'type': 'monthly_summary',
                        'period_type': 'month',
                        'start_date': start_date,
                        'end_date': end_date,
                        'count': int(row['payment_id']),
                        'amount': float(row['amount'])
                    }
                })

        overall_start_date = None
        overall_end_date = None
        if hasattr(self, 'dataFrame') and not self.dataFrame.empty:
            df_dates = [pd.to_datetime(d) for d in self.dataFrame['date']]
            overall_start_date = format_date(min(df_dates))
            overall_end_date = format_date(max(df_dates))

        if hasattr(self, 'currency_groups'):
            for _, row in self.currency_groups.iterrows():
                self.tokens.append({
                    'text': f"Currency summary for {row['currency']} from {overall_start_date} to {overall_end_date}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {
                        'type': 'currency_summary',
                        'period_type': 'all_time',
                        'currency': row['currency'],
                        'count': int(row['payment_id']),
                        'amount': float(row['amount']),
                        'start_date': overall_start_date,
                        'end_date': overall_end_date
                    }
                })

        if hasattr(self, 'status_groups'):
            for _, row in self.status_groups.iterrows():
                self.tokens.append({
                    'text': f"Status summary for '{row['status']}' from {overall_start_date} to {overall_end_date}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {
                        'type': 'status_summary',
                        'period_type': 'all_time',
                        'status': row['status'],
                        'count': int(row['payment_id']),
                        'amount': float(row['amount']),
                        'start_date': overall_start_date,
                        'end_date': overall_end_date
                    }
                })
                
        return self.tokens

    def post_tokenize(self):
        self.post_tokenized_data = [
            {'id': str(uuid.uuid4()), 'text': t['text'], **t['metadata']} for t in self.tokens
        ]
        return self.post_tokenized_data

    def store(self):
        return store(self.post_tokenized_data, namespace='payment')


    def process(self):
        self.load()
        self.transform()
        self.tokenize()
        self.post_tokenize()
        self.store()
        return True
    
class ProcessPolicy(ProccessData):
    """Processes policy documents through a pluggable chunking strategy."""

    def __init__(self, file_path: str, chunking_strategy: str = "docling", creation_date: str = None, isLegacy: bool = False, status: str = 'active', department: str = None, project_codename: str = None):
        super().__init__(file_path)
        self.strategy = get_strategy(chunking_strategy)
        self.creation_date = creation_date
        self.isLegacy = isLegacy
        self.status = status
        self.department = department
        self.project_codename = project_codename

    def tokenize(self):
        """Delegate chunking to the selected strategy and attach policy metadata."""
        chunk_results = self.strategy.chunk(self.file_path)
        now = datetime.datetime.utcnow().isoformat()

        self.tokens = [
            {
                'text': c.text,
                'metadata': {
                    'type': 'policy',
                    'source': os.path.basename(self.file_path),
                    'uploaded_at': now,
                    'creation_date': self.creation_date,
                    'isLegacy': self.isLegacy,
                    'status': self.status,
                    'department': self.department,
                    'project_codename': self.project_codename,
                },
            }
            for c in chunk_results
        ]

    def post_tokenize(self):
        self.post_tokenized_data = [
            {'id': str(uuid.uuid4()), 'text': t['text'], **t['metadata']} for t in self.tokens
        ]
        return self.post_tokenized_data

    def store(self):
        return store(self.post_tokenized_data, namespace='policy')

    def process(self):
        self.tokenize()
        self.post_tokenize()
        self.store()
        return True

class ProcessReport(ProccessData):
    """Processes report documents through a pluggable chunking strategy."""

    def __init__(self, file_path: str, chunking_strategy: str = "docling", creation_date: str = None, isLegacy: bool = False, status: str = 'active', department: str = None, project_codename: str = None):
        super().__init__(file_path)
        self.strategy = get_strategy(chunking_strategy)
        self.creation_date = creation_date
        self.isLegacy = isLegacy
        self.status = status
        self.department = department
        self.project_codename = project_codename

    def tokenize(self):
        """Delegate chunking to the selected strategy and attach report metadata."""
        chunk_results = self.strategy.chunk(self.file_path)
        now = datetime.datetime.utcnow().isoformat()

        self.tokens = [
            {
                'text': c.text,
                'metadata': {
                    'type': 'report',
                    'source': os.path.basename(self.file_path),
                    'uploaded_at': now,
                    'creation_date': self.creation_date,
                    'isLegacy': self.isLegacy,
                    'status': self.status,
                    'department': self.department,
                    'project_codename': self.project_codename,
                },
            }
            for c in chunk_results
        ]

    def post_tokenize(self):
        self.post_tokenized_data = [
            {'id': str(uuid.uuid4()), 'text': t['text'], **t['metadata']} for t in self.tokens
        ]
        return self.post_tokenized_data

    def store(self):
        return store(self.post_tokenized_data, namespace='report')

    def process(self):
        self.tokenize()
        self.post_tokenize()
        self.store()
        return True