"""
Data Processing Utilities for FlushBot
Handles CSV/Parquet batch processing and historical message analysis
"""

import asyncio
import os
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import csv

from loguru import logger
from config.settings import settings
from core.ai_analyzer import ai_analyzer
from core.database import db_manager


class BatchProcessor:
    """Processes historical messages from CSV/Parquet files"""
    
    def __init__(self):
        self.export_path = Path(settings.csv_export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)
        
    async def process_csv_file(self, file_path: str, chat_id: Optional[int] = None) -> Dict:
        """
        Process messages from CSV file
        
        Expected CSV format:
        - timestamp, user_id, chat_id, message_text, message_id
        """
        
        logger.info(f"Processing CSV file: {file_path}")
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_cols = ['timestamp', 'user_id', 'chat_id', 'message_text', 'message_id']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Filter by chat_id if specified
            if chat_id:
                df = df[df['chat_id'] == chat_id]
            
            # Convert to list of message dicts
            messages = []
            for _, row in df.iterrows():
                message = {
                    "text": str(row['message_text']),
                    "context": {
                        "user_id": int(row['user_id']),
                        "chat_id": int(row['chat_id']),
                        "message_id": int(row['message_id']),
                        "timestamp": str(row['timestamp']),
                        "batch_processing": True
                    }
                }
                messages.append(message)
            
            # Process in batches
            results = await self._process_message_batch(messages)
            
            # Generate summary report
            summary = self._generate_batch_summary(messages, results)
            
            # Save results
            await self._save_batch_results(file_path, results, summary)
            
            logger.info(f"Completed processing {len(messages)} messages from {file_path}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to process CSV file {file_path}: {e}")
            raise
    
    async def process_parquet_file(self, file_path: str, chat_id: Optional[int] = None) -> Dict:
        """Process messages from Parquet file"""
        
        if not settings.parquet_support:
            raise ValueError("Parquet support is disabled")
        
        logger.info(f"Processing Parquet file: {file_path}")
        
        try:
            # Read Parquet file
            df = pd.read_parquet(file_path)
            
            # Convert to CSV format for processing
            temp_csv = f"/tmp/temp_parquet_{datetime.now().timestamp()}.csv"
            df.to_csv(temp_csv, index=False)
            
            # Process as CSV
            result = await self.process_csv_file(temp_csv, chat_id)
            
            # Cleanup temp file
            os.remove(temp_csv)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process Parquet file {file_path}: {e}")
            raise
    
    async def _process_message_batch(self, messages: List[Dict]) -> List[Dict]:
        """Process batch of messages with AI analysis"""
        
        results = []
        batch_size = settings.batch_processing_size
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(messages) + batch_size - 1)//batch_size}")
            
            # Analyze batch with AI
            batch_results = await ai_analyzer.batch_analyze(batch)
            results.extend(batch_results)
            
            # Rate limiting between batches
            if i + batch_size < len(messages):
                await asyncio.sleep(2)  # 2 second delay between batches
        
        return results
    
    def _generate_batch_summary(self, messages: List[Dict], results: List[Dict]) -> Dict:
        """Generate summary report for batch processing"""
        
        total_messages = len(messages)
        total_violations = sum(1 for r in results if r.get("violations"))
        
        # Categorize violations
        violation_categories = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for result in results:
            violations = result.get("violations", [])
            for violation in violations:
                category = violation.get("category", "unknown")
                severity = violation.get("severity", "low")
                
                violation_categories[category] = violation_categories.get(category, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_messages": total_messages,
            "total_violations": total_violations,
            "violation_rate": total_violations / total_messages if total_messages > 0 else 0,
            "violation_categories": violation_categories,
            "severity_distribution": severity_counts,
            "processing_timestamp": datetime.now().isoformat(),
            "ai_analysis_used": any(r.get("ai_analysis", False) for r in results)
        }
    
    async def _save_batch_results(self, input_file: str, results: List[Dict], summary: Dict):
        """Save batch processing results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(input_file).stem
        
        # Save detailed results
        results_file = self.export_path / f"{base_name}_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "input_file": input_file,
                "summary": summary,
                "detailed_results": results
            }, f, indent=2, default=str)
        
        # Save summary report
        summary_file = self.export_path / f"{base_name}_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Batch results saved to {results_file}")
        logger.info(f"Summary saved to {summary_file}")


class DataExporter:
    """Exports chat data to various formats"""
    
    def __init__(self):
        self.export_path = Path(settings.csv_export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)
    
    async def export_chat_messages(
        self, 
        chat_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "csv"
    ) -> str:
        """Export chat messages to file"""
        
        # Default to last 30 days if no dates specified
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        logger.info(f"Exporting messages for chat {chat_id} from {start_date} to {end_date}")
        
        try:
            # Get messages from database
            with db_manager.get_session() as session:
                from core.database import Message, User, Violation
                
                # Query messages with user info and violations
                query = session.query(Message, User)\
                    .join(User, Message.user_id == User.user_id)\
                    .filter(Message.chat_id == chat_id)\
                    .filter(Message.timestamp >= start_date)\
                    .filter(Message.timestamp <= end_date)\
                    .order_by(Message.timestamp)
                
                messages_data = []
                for message, user in query.all():
                    # Get violations for this message
                    violations = session.query(Violation)\
                        .filter(Violation.message_id == message.id)\
                        .all()
                    
                    message_data = {
                        "timestamp": message.timestamp.isoformat(),
                        "message_id": message.message_id,
                        "chat_id": message.chat_id,
                        "user_id": message.user_id,
                        "username": user.username or "",
                        "message_text": message.text or "",
                        "message_type": message.message_type,
                        "analyzed": message.analyzed,
                        "violation_detected": message.violation_detected,
                        "analysis_confidence": message.analysis_confidence,
                        "violation_count": len(violations),
                        "violation_types": [v.violation_type for v in violations],
                        "violation_severities": [v.severity for v in violations]
                    }
                    messages_data.append(message_data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{chat_id}_export_{timestamp}.{format}"
            filepath = self.export_path / filename
            
            # Export in requested format
            if format.lower() == "csv":
                await self._export_to_csv(messages_data, filepath)
            elif format.lower() == "json":
                await self._export_to_json(messages_data, filepath)
            elif format.lower() == "parquet" and settings.parquet_support:
                await self._export_to_parquet(messages_data, filepath)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {len(messages_data)} messages to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export chat {chat_id} data: {e}")
            raise
    
    async def _export_to_csv(self, data: List[Dict], filepath: Path):
        """Export data to CSV format"""
        
        if not data:
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in data:
                # Convert lists to JSON strings for CSV compatibility
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, (list, dict)):
                        processed_row[key] = json.dumps(value)
                    else:
                        processed_row[key] = value
                writer.writerow(processed_row)
    
    async def _export_to_json(self, data: List[Dict], filepath: Path):
        """Export data to JSON format"""
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump({
                "export_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_messages": len(data),
                    "format_version": "1.0"
                },
                "messages": data
            }, jsonfile, indent=2, default=str)
    
    async def _export_to_parquet(self, data: List[Dict], filepath: Path):
        """Export data to Parquet format"""
        
        df = pd.DataFrame(data)
        
        # Convert complex columns to JSON strings
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column contains lists or dicts
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if isinstance(sample, (list, dict)):
                    df[col] = df[col].apply(lambda x: json.dumps(x) if pd.notna(x) else None)
        
        df.to_parquet(filepath, index=False)
    
    async def export_violation_report(self, chat_id: Optional[int] = None, days: int = 30) -> str:
        """Export violation analysis report"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Generating violation report for {days} days")
        
        try:
            with db_manager.get_session() as session:
                from core.database import Violation, User, Chat
                
                # Build query
                query = session.query(Violation, User, Chat)\
                    .join(User, Violation.user_id == User.user_id)\
                    .join(Chat, Violation.chat_id == Chat.chat_id)\
                    .filter(Violation.timestamp >= start_date)
                
                if chat_id:
                    query = query.filter(Violation.chat_id == chat_id)
                
                violations_data = []
                for violation, user, chat in query.all():
                    violation_data = {
                        "timestamp": violation.timestamp.isoformat(),
                        "chat_id": violation.chat_id,
                        "chat_title": chat.title,
                        "user_id": violation.user_id,
                        "username": user.username or "",
                        "violation_type": violation.violation_type,
                        "severity": violation.severity,
                        "confidence": violation.confidence,
                        "detected_by": violation.detected_by,
                        "ai_model": violation.ai_model,
                        "description": violation.description,
                        "keywords_matched": violation.keywords_matched,
                        "patterns_matched": violation.patterns_matched
                    }
                    violations_data.append(violation_data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chat_suffix = f"_chat_{chat_id}" if chat_id else "_all_chats"
            filename = f"violation_report{chat_suffix}_{timestamp}.csv"
            filepath = self.export_path / filename
            
            # Export to CSV
            await self._export_to_csv(violations_data, filepath)
            
            logger.info(f"Violation report saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate violation report: {e}")
            raise


# Global instances
batch_processor = BatchProcessor()
data_exporter = DataExporter()