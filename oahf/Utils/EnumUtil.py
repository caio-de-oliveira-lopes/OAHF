from enum import Enum
from typing import Type, Dict, Optional, Iterable, Any

class EnumUtil:
    @staticmethod
    def get_description(value: Enum) -> Optional[str]:
        """
        Retrieve the 'description' attribute of a given enum value, if it exists.
        
        Args:
            value (Enum): The enum value to inspect.

        Returns:
            Optional[str]: The 'description' attribute if present, otherwise None.
        """
        # Get the enum field corresponding to the given value's name
        field = value.__class__.__dict__.get(value.name)
        
        # If field is not found, attempt to use the default enum value
        if field is None:
            value = EnumUtil.get_default_enum_value(type(value))
            field = value.__class__.__dict__.get(value.name)
        
        # Return the 'description' attribute if it exists
        if field is not None:
            return getattr(field, "description", None)            
        return None
    
    @staticmethod
    def get_default_enum_value(enum_class: Type[Enum]) -> Enum:
        """
        Get the first declared value in an enum class, used as a default.

        Args:
            enum_class (Type[Enum]): The enum class from which to fetch the default value.

        Returns:
            Enum: The first declared enum value.
        """
        return list(enum_class)[0]

    @staticmethod
    def get_enum_from_string(enum_type: Type[Enum], value: str) -> Enum:
        """
        Convert a string representation to the corresponding enum value.

        Args:
            enum_type (Type[Enum]): The enum class to search.
            value (str): The string representation of the enum value.

        Returns:
            Enum: The matching enum value if found, or the first enum value as a default.

        Raises:
            ValueError: If the enum type is invalid or doesn't contain the specified string.
        """
        # Iterate over all items in the enum and match by name (case-insensitive)
        for item in enum_type:
            if item.name.upper() == value.upper():
                return item
        
        # Return the first enum value as the default
        return EnumUtil.get_default_enum_value(enum_type)

    @staticmethod
    def get_values(enum_type: Type[Enum]) -> Iterable[Enum]:
        """
        Retrieve all enum values from a specified enum class.

        Args:
            enum_type (Type[Enum]): The enum class from which to retrieve the values.

        Returns:
            Iterable[Enum]: An iterable containing all enum values in the class.

        Raises:
            ValueError: If the provided enum_type is not a subclass of Enum.
        """
        # Ensure the type provided is a valid enum
        if not issubclass(enum_type, Enum):
            raise ValueError("enum_type must be an enum type")
        
        # Return all values of the enum class
        return enum_type

    @staticmethod
    def convert_enums_to_str(dictionary: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Convert all enum instances within a dictionary to their string representations.

        Args:
            dictionary (Dict[Any, Any]): The dictionary to convert, possibly containing enum instances.

        Returns:
            Dict[Any, Any]: A new dictionary with enum instances converted to strings.
        """
        converted_dict: Dict[Any, Any] = {}
        
        # Iterate over all items in the dictionary
        for key, value in dictionary.items():
            # Convert key if it's an Enum instance
            if isinstance(key, Enum):
                key = key.name
            
            # Convert value if it's an Enum instance
            if isinstance(value, Enum):
                value = value.name
            
            # Recursively handle nested dictionaries
            if isinstance(value, Dict):
                value = EnumUtil.convert_enums_to_str(value)
            
            # Populate the new dictionary with converted keys/values
            converted_dict[key] = value
        
        return converted_dict
