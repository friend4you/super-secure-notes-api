from dataclasses import dataclass

from app.parsers.buffer import ByteReader, ParseError

SSNV_MAGIC = b"SSNV"
SALT_LENGTH = 32
IDENTITY_PUBLIC_KEY_LENGTH = 32


@dataclass(frozen=True)
class VaultHeaderMetadata:
    format_version: int
    public_key: bytes | None
    algorithm_id: int | None


def parse_vault_header(data: bytes) -> VaultHeaderMetadata:
    if not data:
        raise ParseError("Empty vault header.")

    reader = ByteReader(data)
    reader.expect_magic(SSNV_MAGIC)

    version = reader.read_u8()
    if version not in (1, 2):
        raise ParseError(f"Unsupported vault format version: {version}.")

    reader.read_u8()  # kdf_id
    reader.read_fixed(SALT_LENGTH)
    reader.read_u32_be()  # iterations
    reader.read_length_prefixed_bytes()  # wrapped_udk_password
    reader.read_length_prefixed_bytes()  # wrapped_udk_recovery

    public_key: bytes | None = None
    algorithm_id: int | None = None

    if version == 2:
        algorithm_id = reader.read_u8()
        public_key = reader.read_fixed(IDENTITY_PUBLIC_KEY_LENGTH)
        reader.read_length_prefixed_bytes()  # wrapped_identity_private_key

    if not reader.at_end:
        raise ParseError("Vault header contains trailing bytes.")

    if version == 2 and (public_key is None or algorithm_id is None):
        raise ParseError("Vault v2 header is missing identity fields.")

    return VaultHeaderMetadata(
        format_version=version,
        public_key=public_key,
        algorithm_id=algorithm_id,
    )
