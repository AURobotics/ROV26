"""
Example usage of factory methods for schema creation.

This demonstrates how factory methods simplify schema construction
compared to the verbose constructor approach.
"""

from abstract_schema import FieldSchema, FieldSchemaList
from abstract_schema_data_types import CustomDataType, DataType
from typing import Any, Dict, cast
from dataclasses import dataclass


# Example 1: Simple field creation with factory methods
def example_simple_fields():
    """Create simple fields using factory methods"""
    print("=" * 60)
    print("Example 1: Simple Field Creation")
    print("=" * 60)
    
    # Before: Verbose constructor
    # age_field = FieldSchema(name="age", data_type=DataType.INTEGER, value=25, min_value=0, max_value=120)
    
    # After: Clean factory method
    age_field = FieldSchema.integer("age", value=25, min_value=0, max_value=120)
    
    username_field = FieldSchema.string(
        "username",
        value="john_doe",
        pattern=r"^[a-zA-Z0-9_]{3,20}$",
        description="Username must be 3-20 alphanumeric characters"
    )
    
    email_field = FieldSchema.string(
        "email",
        value="john@example.com",
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    )
    
    score_field = FieldSchema.float_field(
        "score",
        value=95.5,
        min_value=0.0,
        max_value=100.0
    )
    
    is_active = FieldSchema.boolean("is_active", value=True)
    
    print(f"Age: {age_field.value}")
    print(f"Username: {username_field.value}")
    print(f"Email: {email_field.value}")
    print(f"Score: {score_field.value}")
    print(f"Active: {is_active.value}")
    print()


# Example 2: Enum/Choice fields
def example_choice_fields():
    """Create fields with allowed values"""
    print("=" * 60)
    print("Example 2: Choice Fields")
    print("=" * 60)
    
    status_field = FieldSchema.string(
        "status",
        value="active",
        allowed_values=["active", "inactive", "pending", "suspended"],
        description="User account status"
    )
    
    priority_field = FieldSchema.integer(
        "priority",
        value=2,
        allowed_values=[1, 2, 3, 4, 5],
        description="Priority level (1=lowest, 5=highest)"
    )
    
    print(f"Status: {status_field.value} (allowed: {status_field.allowed_values})")
    print(f"Priority: {priority_field.value} (allowed: {priority_field.allowed_values})")
    print()


# Example 3: Custom data type
@dataclass
class Address(CustomDataType):
    """Custom address data type"""
    street: str
    city: str
    zip_code: str
    country: str = "USA"
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'Address':
        return cls(
            street=config["street"],
            city=config["city"],
            zip_code=config["zip_code"],
            country=config.get("country", "USA")
        )
    
    def to_config(self) -> Dict[str, Any]:
        return {
            "street": self.street,
            "city": self.city,
            "zip_code": self.zip_code,
            "country": self.country
        }
    
    def validate(self) -> tuple[bool, str]:
        if not self.street:
            return False, "Street is required"
        if not self.city:
            return False, "City is required"
        if not self.zip_code or len(self.zip_code) != 5:
            return False, "ZIP code must be 5 digits"
        return True, ""


def example_custom_field():
    """Create a field with custom data type"""
    print("=" * 60)
    print("Example 3: Custom Data Type Field")
    print("=" * 60)
    
    address = Address(
        street="123 Main St",
        city="Springfield",
        zip_code="12345"
    )
    
    address_field = FieldSchema.custom(
        "address",
        value=address,
        description="User's mailing address"
    )
    
    print(f"Address: {address_field.value.street}, {address_field.value.city}")
    print()


# Example 4: Nested schema using FieldSchemaList.group()
def example_nested_schema():
    """Create nested schemas using factory methods"""
    print("=" * 60)
    print("Example 4: Nested Schema with FieldSchemaList.group()")
    print("=" * 60)
    
    # Create user profile group
    user_profile = FieldSchemaList.group(
        "user_profile",
        fields=[
            FieldSchema.string("username", value="alice_smith"),
            FieldSchema.string("email", value="alice@example.com"),
            FieldSchema.integer("age", value=28, min_value=13),
            FieldSchema.boolean("verified", value=True)
        ],
        description="User profile information"
    )
    
    # Create user settings group
    user_settings = FieldSchemaList.group(
        "settings",
        fields=[
            FieldSchema.boolean("email_notifications", value=True),
            FieldSchema.boolean("sms_notifications", value=False),
            FieldSchema.string(
                "theme",
                value="dark",
                allowed_values=["light", "dark", "auto"]
            ),
            FieldSchema.string(
                "language",
                value="en",
                allowed_values=["en", "es", "fr", "de"]
            )
        ],
        description="User preferences and settings"
    )
    
    # Create top-level schema with nested groups
    user_schema = FieldSchemaList.group(
        "user",
        fields=[user_profile, user_settings],
        description="Complete user data schema"
    )
    
    print(f"Schema: {user_schema.name}")
    print(f"  - {user_profile.name}: {len(user_profile.fields)} fields")
    print(f"  - {user_settings.name}: {len(user_settings.fields)} fields")
    
    # Access nested values
    print("\nProfile values:")
    for field in user_profile.fields:
        field = cast(FieldSchema, field)
        print(f"    {field.name}: {field.value}")
    
    print("\nSettings values:")
    for field in user_settings.fields:
        field = cast(FieldSchema, field)
        print(f"    {field.name}: {field.value}")
    print()


# Example 5: Configuration serialization
def example_serialization():
    """Demonstrate config serialization with factory methods"""
    print("=" * 60)
    print("Example 5: Configuration Serialization")
    print("=" * 60)
    
    # Create schema using factory methods
    config_schema = FieldSchemaList.group(
        "app_config",
        fields=[
            FieldSchema.string("app_name", value="MyApp"),
            FieldSchema.string("version", value="1.0.0"),
            FieldSchema.integer("max_connections", value=100, min_value=1),
            FieldSchema.integer("timeout_seconds", value=30, min_value=1),
            FieldSchema.boolean("debug_mode", value=False),
            FieldSchemaList.group(
                "database",
                fields=[
                    FieldSchema.string("host", value="localhost"),
                    FieldSchema.integer("port", value=5432, min_value=1, max_value=65535),
                    FieldSchema.string("database", value="myapp_db"),
                ]
            )
        ]
    )
    
    # Serialize to config
    config_dict = config_schema.to_config()
    print("Serialized config:")
    import json
    print(json.dumps(config_dict, indent=2))
    
    # Recreate from config
    recreated_schema = FieldSchemaList.create_from_config(config_dict)
    print(f"\nRecreated schema: {recreated_schema.name}")
    print(f"Fields: {len(recreated_schema.fields)}")
    print()


# Example 6: Validation and error handling
def example_validation():
    """Show validation in action"""
    print("=" * 60)
    print("Example 6: Validation and Error Handling")
    print("=" * 60)
    
    # Valid field
    try:
        valid_age = FieldSchema.integer("age", value=25, min_value=0, max_value=120)
        print(f"✓ Valid age: {valid_age.value}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Invalid: age out of range
    try:
        invalid_age = FieldSchema.integer("age", value=150, min_value=0, max_value=120)
        print(f"✓ Valid age: {invalid_age.value}")
    except ValueError as e:
        print(f"✗ Age validation error: {e}")
    
    # Invalid: pattern mismatch
    try:
        invalid_username = FieldSchema.string(
            "username",
            value="a!",  # Too short and contains special char
            pattern=r"^[a-zA-Z0-9_]{3,20}$"
        )
        print(f"✓ Valid username: {invalid_username.value}")
    except ValueError as e:
        print(f"✗ Username validation error: {e}")
    
    # Invalid: not in allowed values
    try:
        invalid_status = FieldSchema.string(
            "status",
            value="deleted",
            allowed_values=["active", "inactive", "pending"]
        )
        print(f"✓ Valid status: {invalid_status.value}")
    except ValueError as e:
        print(f"✗ Status validation error: {e}")
    
    print()


# Example 7: Dynamic value updates
def example_dynamic_updates():
    """Show how to update field values with validation"""
    print("=" * 60)
    print("Example 7: Dynamic Value Updates")
    print("=" * 60)
    
    temperature = FieldSchema.float_field(
        "temperature",
        value=20.0,
        min_value=-50.0,
        max_value=50.0,
        description="Temperature in Celsius"
    )
    
    print(f"Initial temperature: {temperature.value}°C")
    
    # Valid update
    try:
        temperature.set_value(25.5)
        print(f"Updated temperature: {temperature.value}°C")
    except ValueError as e:
        print(f"Error: {e}")
    
    # Invalid update (out of range)
    try:
        temperature.set_value(100.0)
        print(f"Updated temperature: {temperature.value}°C")
    except ValueError as e:
        print(f"Update failed (value preserved): {e}")
        print(f"Current temperature: {temperature.value}°C")
    
    print()


def main():
    """Run all examples"""
    example_simple_fields()
    example_choice_fields()
    example_custom_field()
    example_nested_schema()
    example_serialization()
    example_validation()
    example_dynamic_updates()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
