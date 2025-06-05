"""
Stack for Amazon OpenSearch Serverless resources.

This stack is separate from the main KnowlioStack to improve maintainability 
and separation of concerns.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_iam as iam,
)
from constructs import Construct

from infrastructure.app_constructs.opensearch_serverless_construct import (
    OpenSearchServerlessConstruct,
    OpenSearchServerlessProps
)


class OpenSearchServerlessStack(Stack):
    """CDK Stack for OpenSearch Serverless resources."""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create OpenSearch Serverless Collection with fixed name and RETAIN policy
        opensearch_props = OpenSearchServerlessProps(
            collection_name="knowlio-search",  # Fixed collection name for better consistency
            index_name="content-index",  # Main index for content searching
            removal_policy=RemovalPolicy.RETAIN  # Retain for production to prevent accidental deletion
        )
        
        # Create the OpenSearch Serverless Construct
        self.opensearch = OpenSearchServerlessConstruct(self, "OpenSearchServerless", opensearch_props)
        
        # Add outputs for important resources
        CfnOutput(
            self, "OpenSearchEndpoint",
            value=self.opensearch.collection_endpoint,
            description="OpenSearch Serverless Collection Endpoint",
            export_name="OpenSearchServerlessEndpoint"
        )
        
        CfnOutput(
            self, "OpenSearchDashboardUrl",
            value=f"https://{self.opensearch.collection_endpoint}/_dashboards/",
            description="OpenSearch Serverless Dashboard URL",
            export_name="OpenSearchServerlessDashboardUrl"
        )
        
        CfnOutput(
            self, "OpenSearchCollectionName",
            value=self.opensearch.collection_name,
            description="OpenSearch Serverless Collection Name",
            export_name="OpenSearchServerlessCollectionName"
        )
        
        CfnOutput(
            self, "OpenSearchCollectionArn",
            value=self.opensearch.collection_arn,
            description="OpenSearch Serverless Collection ARN",
            export_name="OpenSearchServerlessCollectionArn"
        )
    
    @property
    def collection_endpoint(self) -> str:
        """Get the OpenSearch Serverless collection endpoint."""
        return self.opensearch.collection_endpoint
    
    @property
    def collection_name(self) -> str:
        """Get the OpenSearch Serverless collection name."""
        return self.opensearch.collection_name
    
    @property
    def collection_arn(self) -> str:
        """Get the OpenSearch Serverless collection ARN."""
        return self.opensearch.collection_arn
