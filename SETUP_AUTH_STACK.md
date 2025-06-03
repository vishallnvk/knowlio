# Quick Setup Guide for AuthStack

## 1. Activate Virtual Environment
```bash
source .venv/bin/activate
```

## 2. Set Google OAuth Credentials
You need to set these environment variables before deployment:

```bash
export GOOGLE_OAUTH_CLIENT_ID="your-google-client-id"
export GOOGLE_OAUTH_CLIENT_SECRET="your-google-client-secret"
```

## 3. Test Configuration
Run the test script to verify everything is set up correctly:
```bash
python3 test_auth_stack.py
```

## 4. Deploy the Stack
Once the test passes, deploy the AuthStack:
```bash
cdk deploy AuthStack --profile knowlio-dev
```

Or deploy all stacks:
```bash
cdk deploy --all --profile knowlio-dev
```

## Important Notes:
1. The Cognito domain prefix has been fixed to handle uppercase letters (converts to lowercase)
2. Make sure to update the Google OAuth redirect URI after deployment to:
   ```
   https://authstack-knowlio-auth.auth.us-west-2.amazoncognito.com/oauth2/idpresponse
   ```
   (The exact URL will be shown in the deployment output)

## Troubleshooting:
- If you get "No module named 'aws_cdk'" error, make sure the virtual environment is activated
- If deployment fails due to missing credentials, ensure the environment variables are exported in your current shell
