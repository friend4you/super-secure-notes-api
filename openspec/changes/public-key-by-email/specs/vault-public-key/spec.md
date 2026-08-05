## ADDED Requirements

### Requirement: Authenticated public key lookup by email

The system SHALL expose `GET /v1/users/public-key` with a required `email` query parameter. The caller MUST be authenticated. The system SHALL resolve the user by case-insensitive email match and return the identity public key denormalized from their vault header.

#### Scenario: Successful lookup

- **WHEN** an authenticated user requests `GET /v1/users/public-key?email=bob@example.com` and a user with email `bob@example.com` exists with a vault header containing an identity public key
- **THEN** the system returns `200 OK` with JSON body `{ "publicKey": "<base64, 32 bytes>", "algorithmId": 1 }`

#### Scenario: Case-insensitive email match

- **WHEN** an authenticated user requests `GET /v1/users/public-key?email=Bob@Example.com` and a user is registered with email `bob@example.com`
- **THEN** the system returns `200 OK` with the same public key as a request using `bob@example.com`

#### Scenario: User not found

- **WHEN** an authenticated user requests `GET /v1/users/public-key?email=unknown@example.com` and no user exists with that email
- **THEN** the system returns `404` with error `user_not_found`

#### Scenario: Public key not found

- **WHEN** an authenticated user requests `GET /v1/users/public-key?email=bob@example.com`, the user exists, but they have no vault header or no stored public key
- **THEN** the system returns `404` with error `public_key_not_found`

#### Scenario: Missing or invalid email

- **WHEN** an authenticated user requests `GET /v1/users/public-key` without an `email` query parameter, or with an invalid email value
- **THEN** the system returns `400` with error `validation_error`

#### Scenario: Unauthenticated request

- **WHEN** a request to `GET /v1/users/public-key?email=bob@example.com` has no valid access token
- **THEN** the system returns `401` with error `unauthorized`

## REMOVED Requirements

### Requirement: Public key lookup by user ID

**Reason**: Share flow only has recipient email at wrap time; UUID-based lookup is unused and inconsistent with share/revoke endpoints that use email.

**Migration**: Replace `GET /v1/users/{userId}/public-key` with `GET /v1/users/public-key?email=<recipientEmail>`.
