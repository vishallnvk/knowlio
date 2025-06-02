import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.aws_service_helpers.s3_helper import S3Helper
from helpers.common_helper.logger_helper import LoggerHelper
from models.usage_log_model import UsageLogModel

logger = LoggerHelper(__name__).get_logger()

USAGE_LOGS_TABLE = "usage_logs"
EXPORT_BUCKET = "knowlio-exports"

class AnalyticsHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=USAGE_LOGS_TABLE)
        self.s3 = S3Helper(bucket_name=EXPORT_BUCKET)

    def log_content_access(self, log_data: Dict) -> Dict:
        """Log content access by a consumer"""
        usage_log = UsageLogModel(log_data)
        log_item = usage_log.__dict__

        logger.info("Logging content access: %s", log_item)
        self.db.put_item(log_item)
        return {
            "message": "Content access logged successfully", 
            "log_id": log_item["log_id"]
        }

    def get_usage_report_by_content(self, content_id: str) -> Dict:
        """Retrieve usage report for a specific content item"""
        logger.info("Fetching usage report for content_id: %s", content_id)
        
        # Query all logs for this content
        logs = self.db.query_items("content_id", content_id)
        
        # Aggregate statistics
        total_accesses = len(logs)
        unique_consumers = len(set(log.get("consumer_id", "") for log in logs))
        access_types = {}
        regions = {}
        
        for log in logs:
            # Count access types
            access_type = log.get("access_type", "VIEW")
            access_types[access_type] = access_types.get(access_type, 0) + 1
            
            # Count regions
            region = log.get("region", "UNKNOWN")
            regions[region] = regions.get(region, 0) + 1

        return {
            "content_id": content_id,
            "total_accesses": total_accesses,
            "unique_consumers": unique_consumers,
            "access_types": access_types,
            "regions": regions,
            "recent_logs": logs[:10]  # Return 10 most recent logs
        }

    def get_usage_report_by_consumer(self, consumer_id: str) -> Dict:
        """Retrieve usage report across all content for a consumer"""
        logger.info("Fetching usage report for consumer_id: %s", consumer_id)
        
        # Query all logs for this consumer
        logs = self.db.query_items("consumer_id", consumer_id)
        
        # Aggregate statistics
        total_accesses = len(logs)
        unique_content = len(set(log.get("content_id", "") for log in logs))
        access_types = {}
        publishers = {}
        
        for log in logs:
            # Count access types
            access_type = log.get("access_type", "VIEW")
            access_types[access_type] = access_types.get(access_type, 0) + 1
            
            # Count publishers
            publisher_id = log.get("publisher_id", "UNKNOWN")
            publishers[publisher_id] = publishers.get(publisher_id, 0) + 1

        return {
            "consumer_id": consumer_id,
            "total_accesses": total_accesses,
            "unique_content": unique_content,
            "access_types": access_types,
            "publishers": publishers,
            "recent_logs": logs[:10]  # Return 10 most recent logs
        }

    def export_usage_logs(self, export_params: Dict) -> Dict:
        """Export logs to S3 in JSONL format for audit/reporting"""
        from_date = export_params.get("from_date")
        to_date = export_params.get("to_date")
        format_type = export_params.get("format", "jsonl")
        region_filter = export_params.get("region")

        logger.info("Exporting usage logs from %s to %s", from_date, to_date)

        # Get all logs (in production, you'd want to add date filtering)
        # For now, we'll get all logs and filter client-side
        all_logs = self.db.scan_table()
        
        # Filter by date range if provided
        filtered_logs = []
        for log in all_logs:
            log_time = log.get("access_time", "")
            if from_date and to_date:
                if from_date <= log_time <= to_date:
                    if not region_filter or log.get("region") == region_filter:
                        filtered_logs.append(log)
            else:
                if not region_filter or log.get("region") == region_filter:
                    filtered_logs.append(log)

        # Convert to JSONL format
        jsonl_data = "\n".join(json.dumps(log) for log in filtered_logs)
        
        # Generate S3 key
        current_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        date_folder = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        s3_key = self.s3.generate_export_key("usage-logs", date_folder, current_time, format_type)
        
        # Upload to S3
        s3_url = self.s3.upload_data_as_json(jsonl_data, s3_key)
        
        return {
            "message": "Usage logs exported successfully",
            "export_location": s3_url,
            "total_records": len(filtered_logs),
            "format": format_type,
            "date_range": {
                "from": from_date,
                "to": to_date
            }
        }

    def get_log_by_id(self, log_id: str) -> Optional[Dict]:
        """Get a specific usage log by ID"""
        logger.info("Fetching usage log for log_id: %s", log_id)
        return self.db.get_item({"log_id": log_id})
