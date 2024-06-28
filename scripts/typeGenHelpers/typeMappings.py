type_mapping = {
    "uuid": "str",
    "timestamptz": "datetime",
    "timestamp": "datetime",
    "timestamp with time zone": "datetime",
    "timestamp without time zone": "datetime",
    "varchar": "str",
    "character varying": "str",
    "text": "str",
    "bool": "bool",
    "boolean": "bool",
    "int4": "int",
    "integer": "int",
    "int2": "int",
    "smallint": "int",
    "int8": "int",
    "bigint": "int",
    "real": "float",
    "float4": "float",
    "double precision": "float",
    "float8": "float",
    "numeric": "Decimal",
    "json": "dict",
    "jsonb": "dict",
    "date": "date",
    "inet": "IPv4Address",
    "interval": "timedelta",
    "bytea": "bytes",
    "char": "str",  # Single character
    '"char"': "str",  # Single character
    "name": "str",  # PostgreSQL internal name type, usually treated as text
    "oid": "int",  # Object identifier
    "xid": "int",  # Transaction ID
    # Array types
    "_aclitem": "List[str]",
    "_bool": "List[bool]",
    "_char": "List[str]",
    "_float4": "List[float]",
    "_float8": "List[float]",
    "_int2": "List[int]",
    "_name": "List[str]",
    "_oid": "List[int]",
    "_pg_statistic": "List[str]",  # Placeholder for complex type
    "_regtype": "List[str]",  # Placeholder for complex type
    "_text": "List[str]",
    "int2vector": "List[int]",
    "oidvector": "List[int]",
    # User-defined and other special types as generic types
    "anyarray": "List",  # Generic list
    "aal_level": "str",
    "code_challenge_method": "str",
    "factor_status": "str",
    "factor_type": "str",
    "key_status": "str",
    "key_type": "str",
    # Add placeholders for other specific or complex types
    "pg_dependencies": "str",
    "pg_lsn": "str",
    "pg_mcv_list": "str",
    "pg_ndistinct": "str",
    "pg_node_tree": "str",
    "regnamespace": "str",
    "regproc": "str",
    "regtype": "str",
}

# Note: For IP addresses, consider using 'IPv4Address' or 'IPv6Address' from the 'ipaddress' Python standard library,
# but these types are not directly supported by Pydantic without custom validators.
# You may use 'str' or 'Any' for types without a clear direct mapping, or implement custom Pydantic types for complex cases.
