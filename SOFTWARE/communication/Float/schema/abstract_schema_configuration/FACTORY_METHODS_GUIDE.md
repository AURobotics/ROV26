"""
FACTORY METHODS QUICK REFERENCE GUIDE
======================================

This guide provides quick reference for all factory methods added to the schema system.

FIELD FACTORY METHODS
---------------------

1. FieldSchema.string()
   Creates a string field with optional pattern matching and allowed values.
   
   Parameters:
   - name: str (required)
   - value: Any (default: None)
   - pattern: Optional[str] - regex pattern for validation
   - allowed_values: Optional[List[str]] - list of valid choices
   - description: str (default: "")
   
   Examples:
   ```python
   # Basic string
   name = FieldSchema.string("name", value="John Doe")
   
   # With regex pattern
   username = FieldSchema.string(
       "username",
       value="john_doe",
       pattern=r"^[a-zA-Z0-9_]{3,20}$"
   )
   
   # With allowed values (enum-like)
   status = FieldSchema.string(
       "status",
       value="active",
       allowed_values=["active", "inactive", "pending"]
   )
   ```

2. FieldSchema.integer()
   Creates an integer field with optional range constraints.
   
   Parameters:
   - name: str (required)
   - value: Any (default: None)
   - min_value: Optional[int] - minimum allowed value
   - max_value: Optional[int] - maximum allowed value
   - allowed_values: Optional[List[int]] - list of valid choices
   - description: str (default: "")
   
   Examples:
   ```python
   # Basic integer
   age = FieldSchema.integer("age", value=25)
   
   # With range
   age = FieldSchema.integer("age", value=25, min_value=0, max_value=120)
   
   # With allowed values
   rating = FieldSchema.integer(
       "rating",
       value=5,
       allowed_values=[1, 2, 3, 4, 5]
   )
   ```

3. FieldSchema.float_field()
   Creates a float field with optional range constraints.
   
   Parameters:
   - name: str (required)
   - value: Any (default: None)
   - min_value: Optional[float] - minimum allowed value
   - max_value: Optional[float] - maximum allowed value
   - description: str (default: "")
   
   Examples:
   ```python
   # Basic float
   price = FieldSchema.float_field("price", value=19.99)
   
   # With range
   temperature = FieldSchema.float_field(
       "temperature",
       value=20.5,
       min_value=-50.0,
       max_value=50.0
   )
   ```

4. FieldSchema.boolean()
   Creates a boolean field.
   
   Parameters:
   - name: str (required)
   - value: Any (default: None)
   - description: str (default: "")
   
   Examples:
   ```python
   is_active = FieldSchema.boolean("is_active", value=True)
   has_permission = FieldSchema.boolean("has_permission", value=False)
   ```

5. FieldSchema.json_field()
   Creates a JSON field that can hold dictionaries or JSON strings.
   
   Parameters:
   - name: str (required)
   - value: Any (default: None) - can be dict, list, or JSON string
   - description: str (default: "")
   
   Examples:
   ```python
   # With dict
   metadata = FieldSchema.json_field("metadata", value={"key": "value"})
   
   # With JSON string
   config = FieldSchema.json_field("config", value='{"setting": true}')
   ```

6. FieldSchema.custom()
   Creates a field with a custom data type.
   
   Parameters:
   - name: str (required)
   - value: CustomDataType (default: None)
   - description: str (default: "")
   
   Examples:
   ```python
   address = Address(street="123 Main St", city="NYC", zip_code="10001")
   address_field = FieldSchema.custom("address", value=address)
   ```

MAIN FIELD SCHEMA FACTORY METHODS
----------------------------------

1. FieldSchemaList.group()
   Creates a group/container for multiple fields or nested groups.
   
   Parameters:
   - name: str (required)
   - fields: list[Union[FieldSchemaList, FieldSchema]] (required)
   - description: str (default: "")
   
   Examples:
   ```python
   # Simple group
   user_profile = FieldSchemaList.group(
       "user_profile",
       fields=[
           FieldSchema.string("username", value="alice"),
           FieldSchema.integer("age", value=28),
           FieldSchema.boolean("verified", value=True)
       ]
   )
   
   # Nested groups
   user_schema = FieldSchemaList.group(
       "user",
       fields=[
           user_profile,  # nested group
           user_settings,  # another nested group
       ]
   )
   ```

COMPARISON: BEFORE vs AFTER
----------------------------

BEFORE (verbose constructor):
```python
age_field = FieldSchema(
    name="age",
    data_type=DataType.INTEGER,
    value=25,
    min_value=0,
    max_value=120,
    pattern=None,
    allowed_values=None,
    description="User's age"
)

user_group = FieldSchemaList(
    name="user",
    fields=[age_field, name_field, email_field],
    description="User information"
)
```

AFTER (factory methods):
```python
age_field = FieldSchema.integer(
    "age",
    value=25,
    min_value=0,
    max_value=120,
    description="User's age"
)

user_group = FieldSchemaList.group(
    "user",
    fields=[age_field, name_field, email_field],
    description="User information"
)
```

BENEFITS
--------

1. **Less Verbose**: No need to specify data_type or unused parameters
2. **Type-Specific**: Each factory method only exposes relevant parameters
3. **Better IDE Support**: Auto-completion shows only applicable parameters
4. **More Readable**: Intent is clearer (e.g., `.integer()` vs `data_type=DataType.INTEGER`)
5. **Fewer Errors**: Can't accidentally pass wrong parameter types

COMMON PATTERNS
---------------

Pattern 1: Configuration Schema
```python
config = FieldSchemaList.group(
    "app_config",
    fields=[
        FieldSchema.string("app_name", value="MyApp"),
        FieldSchema.integer("port", value=8080, min_value=1, max_value=65535),
        FieldSchema.boolean("debug", value=False),
        FieldSchemaList.group(
            "database",
            fields=[
                FieldSchema.string("host", value="localhost"),
                FieldSchema.integer("port", value=5432),
                FieldSchema.string("name", value="mydb")
            ]
        )
    ]
)
```

Pattern 2: User Profile Schema
```python
user_schema = FieldSchemaList.group(
    "user",
    fields=[
        FieldSchema.string("username", value="alice", pattern=r"^[a-z0-9_]{3,20}$"),
        FieldSchema.string("email", value="alice@example.com"),
        FieldSchema.integer("age", value=28, min_value=13),
        FieldSchema.string(
            "role",
            value="user",
            allowed_values=["admin", "user", "guest"]
        ),
        FieldSchema.boolean("is_verified", value=False)
    ]
)
```

Pattern 3: API Request Schema
```python
api_request = FieldSchemaList.group(
    "api_request",
    fields=[
        FieldSchema.string("endpoint", value="/api/users"),
        FieldSchema.string("method", value="GET", allowed_values=["GET", "POST", "PUT", "DELETE"]),
        FieldSchema.integer("timeout", value=30, min_value=1, max_value=300),
        FieldSchema.json_field("headers", value={"Content-Type": "application/json"}),
        FieldSchema.json_field("body", value={})
    ]
)
```

TIPS
----

1. Use descriptive names for your fields
2. Always set min/max values for numeric fields when you have business constraints
3. Use patterns for string validation (emails, usernames, etc.)
4. Use allowed_values for enum-like fields
5. Group related fields using FieldSchemaList.group()
6. Add descriptions for documentation and better error messages
7. Test validation by trying to create fields with invalid values

SEE ALSO
--------
- schema_factory_examples.py - Comprehensive examples
- abstract_schema.py - Full implementation
- abstract_schema_data_types.py - Base classes and data types
"""
