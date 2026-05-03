
import uuid
from CompanyRAG.src.core.RAGCore import store
from CompanyRAG.src.core.RAGCore import embed
from typing import Literal
from fastapi import UploadFile
import pandas as pd
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,      # Small for this example; usually 500-1000
    chunk_overlap=20,    # Keeps a bit of the previous chunk for context
    separators=["\n\n", "\n", " ", ""] # Order of priority for splitting
)

class ProccessData:
    def __init__(self,file_path:str):
        self.file_path = file_path

class ProcessPayment(ProccessData):

    def load(self):
        self.dataFrame=pd.read_csv(self.file_path)

    def transform(self):
        df = self.dataFrame.copy()
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])

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

        def get_week_name(n):
            week_num = (n - 1) // 7 + 1
            return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(week_num, "nth")

        if hasattr(self, 'dataFrame'):
            for _, row in self.dataFrame.iterrows():
                dt = pd.to_datetime(row['date'])
                date_str = f"{dt.day}{get_day_suffix(dt.day)} {dt.strftime('%B')}"
                self.tokens.append({
                    'text': f"Payment ID {row['payment_id']} on {date_str} for {row['amount']} {row['currency']} has status {row['status']}.",
                    'metadata': {'type': 'individual', 'payment_id': row['payment_id'], 'date_str': date_str, 'amount': float(row['amount']), 'currency': row['currency'], 'status': row['status']}
                })
        
        if hasattr(self, 'daily_groups'):
            for _, row in self.daily_groups.iterrows():
                dt = pd.to_datetime(row['date'])
                date_str = f"{dt.day}{get_day_suffix(dt.day)} {dt.strftime('%B')}"
                self.tokens.append({
                    'text': f"Daily summary for {date_str}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {'type': 'daily_summary', 'date_str': date_str, 'count': int(row['payment_id']), 'amount': float(row['amount'])}
                })

        if hasattr(self, 'weekly_groups'):
            for _, row in self.weekly_groups.iterrows():
                dt = row['date'].end_time
                week_str = f"{get_week_name(dt.day)} week of {dt.strftime('%B')}"
                self.tokens.append({
                    'text': f"Weekly summary for {week_str}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {'type': 'weekly_summary', 'week_str': week_str, 'count': int(row['payment_id']), 'amount': float(row['amount'])}
                })

        if hasattr(self, 'monthly_groups'):
            for _, row in self.monthly_groups.iterrows():
                month_str = row['date'].strftime('%B')
                self.tokens.append({
                    'text': f"Monthly summary for {month_str}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {'type': 'monthly_summary', 'month_str': month_str, 'count': int(row['payment_id']), 'amount': float(row['amount'])}
                })

        if hasattr(self, 'currency_groups'):
            for _, row in self.currency_groups.iterrows():
                self.tokens.append({
                    'text': f"Currency summary for {row['currency']}: {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {'type': 'currency_summary', 'currency': row['currency'], 'count': int(row['payment_id']), 'amount': float(row['amount'])}
                })

        if hasattr(self, 'status_groups'):
            for _, row in self.status_groups.iterrows():
                self.tokens.append({
                    'text': f"Status summary for '{row['status']}': {row['payment_id']} payments totaling {row['amount']}.",
                    'metadata': {'type': 'status_summary', 'status': row['status'], 'count': int(row['payment_id']), 'amount': float(row['amount'])}
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

    def load(self):
        self.file_type = self.file_path.split('.')[-1]
        if(self.file_type == 'docx'):
            loader = Docx2txtLoader(self.file_path)
            self.data = loader.load()

    def tokenize(self):
        chunks = splitter.split_text(self.data[0].page_content)
        
        self.tokens = []
        for i, chunk in enumerate(chunks):
            self.tokens.append({'text': chunk, 'metadata': {'type': 'policy', 'page': self.data[0].metadata['page'], 'source': self.data[0].metadata['source']}})
        
    def post_tokenize(self):
        self.post_tokenized_data = [
            {'id': str(uuid.uuid4()), 'text': t['text'], **t['metadata']} for t in self.tokens
        ]
        return self.post_tokenized_data
    def store(self):
        return store(self.post_tokenized_data, namespace='policy')
    def process(self):
        self.load()
        self.tokenize()
        self.post_tokenize()
        # self.store()
        return True