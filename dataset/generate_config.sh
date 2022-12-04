echo "Type API Key"
read -r api_key

echo "Type API Key Secret"
read -r secret_key

echo "Type Access Token"
read -r token

echo "Type Access Token Secret"
read -r secret_token

echo "Type Bearer Token"
read -r bearer_token

echo "api_key: $api_key
api_key_secret: $secret_key
access_key: $token
access_key_secret: $secret_token
bearer_token: $bearer_token" >> access_config.yaml
