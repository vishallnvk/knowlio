# Knowlio Cognito Authentication Stack

This document describes the Cognito authentication stack implementation for the Knowlio web application.

## Overview

The AuthStack creates AWS Cognito resources to handle user authentication with support for:
- Email-based sign-in
- Google OAuth integration
- Authorization code flow for frontend applications
- Cognito hosted UI

## Stack Components

### 1. **Cognito User Pool** (`knowlio-user-pool`)
- Email as username alias
- Email verification required
- Password policy: 8+ characters, uppercase, lowercase, digits
- Account recovery via email only

### 2. **Google Identity Provider**
- Integrates with Google OAuth
- Maps Google profile attributes to Cognito user attributes
- Requires Google OAuth client credentials

### 3. **User Pool App Client** (`knowlio-web-app-client`)
- No client secret (for frontend usage)
- Authorization code grant flow
- OAuth scopes: openid, email, profile
- Callback URL: http://localhost:3000/
- Logout URL: http://localhost:3000/

### 4. **Cognito Domain** (`knowlio-auth`)
- Provides hosted UI for authentication
- Domain prefix: `knowlio-auth`

## Prerequisites

Before deploying the stack, you need to:

1. **Create a Google OAuth Application**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs:
     ```
     https://<stack-name>-knowlio-auth.auth.<region>.amazoncognito.com/oauth2/idpresponse
     ```

2. **Set Environment Variables**
   ```bash
   export GOOGLE_OAUTH_CLIENT_ID="your-google-client-id"
   export GOOGLE_OAUTH_CLIENT_SECRET="your-google-client-secret"
   ```

## Deployment

1. **Synthesize the CDK app**
   ```bash
   cdk synth
   ```

2. **Deploy the AuthStack**
   ```bash
   cdk deploy AuthStack --profile knowlio-dev
   ```
   
   Or to deploy all stacks:
   ```bash
   cdk deploy --all --profile knowlio-dev
   ```

## Stack Outputs

After deployment, the stack exports the following values:

- **UserPoolId**: The Cognito User Pool ID
- **UserPoolClientId**: The App Client ID for frontend integration
- **CognitoDomain**: The Cognito domain name
- **AuthDomainUrl**: Full URL for the Cognito hosted UI
- **LoginUrl**: Complete OAuth login URL
- **LogoutUrl**: Complete logout URL
- **CallbackUrls**: Configured callback URLs
- **LogoutUrls**: Configured logout URLs
- **GoogleIdpName**: Name of the Google identity provider

## Frontend Integration

### 1. **Login Flow**
Use the exported `LoginUrl` or construct it manually:
```
https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/authorize?
  client_id=<client-id>&
  response_type=code&
  scope=openid+email+profile&
  redirect_uri=http://localhost:3000/
```

### 2. **Handle Callback**
After successful authentication, Cognito redirects to your callback URL with an authorization code:
```
http://localhost:3000/?code=<authorization-code>
```

Exchange this code for tokens using the token endpoint:
```
https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/token
```

### 3. **Logout**
Use the exported `LogoutUrl` or construct it manually:
```
https://<cognito-domain>.auth.<region>.amazoncognito.com/logout?
  client_id=<client-id>&
  logout_uri=http://localhost:3000/
```

## Configuration

All configuration is centralized in `infrastructure/config/knowlio_auth_config.py`. Modify this file to:
- Change password policies
- Update OAuth scopes
- Modify callback/logout URLs
- Adjust user pool settings

## Development vs Production

The current configuration is optimized for development:
- RemovalPolicy.DESTROY is set (resources will be deleted on stack deletion)
- Localhost URLs are used for callbacks

For production:
1. Change RemovalPolicy to RETAIN
2. Update callback/logout URLs to production domains
3. Consider using AWS Secrets Manager instead of environment variables for Google credentials
4. Enable MFA and advanced security features

## Troubleshooting

1. **"Google OAuth credentials not found" error**
   - Ensure environment variables are set before running `cdk deploy`

2. **"Domain already exists" error**
   - The Cognito domain prefix must be globally unique
   - Modify the prefix in `knowlio_auth_config.py` if needed

3. **Google sign-in not working**
   - Verify the redirect URI in Google Console matches the Cognito domain
   - Check that Google+ API is enabled in your Google project

## Security Considerations

1. **Client Credentials**: Store Google OAuth credentials securely, preferably in AWS Secrets Manager
2. **CORS**: Configure appropriate CORS settings for your production domain
3. **Token Storage**: Implement secure token storage in your frontend (avoid localStorage for sensitive tokens)
4. **HTTPS**: Always use HTTPS in production
