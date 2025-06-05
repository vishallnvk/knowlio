"""OpenSearch Serverless Construct for Knowlio"""

from aws_cdk import (
    aws_opensearchserverless as opensearchserverless,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput,
    Stack,
    Aws,
)
from constructs import Construct
from typing import Optional, List


class OpenSearchServerlessProps:
    def __init__(
        self,
        collection_name: str,
        index_name: str = "content-index",
        removal_policy: RemovalPolicy = RemovalPolicy.RETAIN,
        tags: Optional[dict] = None,
    ):
        self.collection_name = collection_name
        self.index_name = index_name  # The main search index name
        self.removal_policy = removal_policy
        self.tags = tags or {}


class OpenSearchServerlessConstruct(Construct):
    def __init__(self, scope: Construct, id: str, props: OpenSearchServerlessProps):
        super().__init__(scope, id)

        # Ensure collection name is lowercase and has no underscores for DNS compatibility
        collection_name = props.collection_name.lower().replace('_', '-')
        
        # Create OpenSearch Serverless Collection
        self.collection = opensearchserverless.CfnCollection(
            self,
            "Collection",
            name=collection_name,
            description="Knowlio full-text search collection",
            type="SEARCH"  # Using the SEARCH collection type for full-text search
            # collection_endpoints is not a valid parameter
        )
        
        # Generate short policy names - must be under 32 chars and match pattern ^[a-z][a-z0-9-]{2,31}$
        # Use a prefix and a hash of the collection name to ensure uniqueness while staying short
        prefix = "kn"
        name_hash = abs(hash(collection_name)) % 10000  # Get a short numeric hash
        policy_base = f"{prefix}-{name_hash}"
        
        # Create encryption policy (required)
        encryption_policy = opensearchserverless.CfnSecurityPolicy(
            self,
            "EncryptionPolicy",
            name=f"{policy_base}-enc",  # Short name: prefix + hash + type
            type="encryption",
            policy=f'{{"Rules":[{{"ResourceType":"collection","Resource":["collection/{collection_name}"]}}],"AWSOwnedKey":true}}',
            description="Default encryption policy using AWS owned keys"
        )
        
        # Create network policy - allow public access for development
        network_policy = opensearchserverless.CfnSecurityPolicy(
            self,
            "NetworkPolicy",
            name=f"{policy_base}-net",  # Short name: prefix + hash + type
            type="network",
            policy=f'[{{"Rules":[{{"ResourceType":"dashboard","Resource":["collection/{collection_name}"]}},{{"ResourceType":"collection","Resource":["collection/{collection_name}"]}}],"AllowFromPublic":true}}]',
            description="Network policy allowing public access for development"
        )
        
        # Create data access policy - full access for Lambda execution role
        # We need to use '*' for the root account to give full access during development
        account_id = Aws.ACCOUNT_ID
        data_policy = opensearchserverless.CfnAccessPolicy(
            self,
            "DataAccessPolicy",
            name=f"{policy_base}-data",  # Short name: prefix + hash + type
            type="data",
            policy=f'[{{"Description":"Access for Lambda role","Rules":[{{"ResourceType":"collection","Resource":["collection/{collection_name}"],"Permission":["aoss:*"]}}],"Principal":["arn:aws:iam::{account_id}:root"]}}]',
            description="Data access policy for Lambda execution role"
        )
        
        # Set dependencies to ensure policies are created before the collection
        self.collection.add_dependency(encryption_policy)
        self.collection.add_dependency(network_policy)
        self.collection.add_dependency(data_policy)
        
        # Set removal policy
        if props.removal_policy == RemovalPolicy.DESTROY:
            self.collection.apply_removal_policy(props.removal_policy)
            encryption_policy.apply_removal_policy(props.removal_policy)
            network_policy.apply_removal_policy(props.removal_policy)
            data_policy.apply_removal_policy(props.removal_policy)
        
        # Expose collection attributes
        self.collection_id = self.collection.attr_id
        self.collection_name = collection_name
        self.collection_arn = f"arn:aws:aoss:{Aws.REGION}:{Aws.ACCOUNT_ID}:collection/{self.collection_id}"
        
        # For OpenSearch Serverless, the endpoint is available as an attribute
        self.collection_endpoint = self.collection.attr_collection_endpoint
        
        # Output the collection endpoint
        CfnOutput(
            self, "CollectionEndpoint", 
            value=self.collection_endpoint,
            description="OpenSearch Serverless Collection Endpoint"
        )
        
        # Output the Dashboard URL
        dashboard_url = f"https://{self.collection_endpoint}/_dashboards/"
        CfnOutput(
            self, "DashboardURL",
            value=dashboard_url,
            description="OpenSearch Serverless Dashboard URL"
        )
