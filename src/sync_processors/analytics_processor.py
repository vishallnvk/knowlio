from typing import Dict

from helpers.app_logic_helpers.analytics_helper import AnalyticsHelper
from helpers.common_helper.logger_helper import LoggerHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()

@ProcessorRegistry.register("analytics")
class AnalyticsProcessor(BaseProcessor):
    def __init__(self):
        self.helper = AnalyticsHelper()
        super().__init__({
            "log_content_access": self._log_content_access,
            "get_usage_report_by_content": self._get_usage_report_by_content,
            "get_usage_report_by_consumer": self._get_usage_report_by_consumer,
            "export_usage_logs": self._export_usage_logs,
        })

    def _log_content_access(self, payload: Dict) -> Dict:
        """Log content access by a consumer"""
        logger.info("Processing log_content_access request")
        return self.helper.log_content_access(payload)

    def _get_usage_report_by_content(self, payload: Dict) -> Dict:
        """Get usage report for a specific content item"""
        logger.info("Processing get_usage_report_by_content request")
        content_id = payload.get("content_id")
        if not content_id:
            raise ValueError("content_id is required for usage report")
        return self.helper.get_usage_report_by_content(content_id)

    def _get_usage_report_by_consumer(self, payload: Dict) -> Dict:
        """Get usage report for a specific consumer"""
        logger.info("Processing get_usage_report_by_consumer request")
        consumer_id = payload.get("consumer_id")
        if not consumer_id:
            raise ValueError("consumer_id is required for usage report")
        return self.helper.get_usage_report_by_consumer(consumer_id)

    def _export_usage_logs(self, payload: Dict) -> Dict:
        """Export usage logs to S3"""
        logger.info("Processing export_usage_logs request")
        return self.helper.export_usage_logs(payload)
