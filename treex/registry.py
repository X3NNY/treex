from typing import Type, Dict, TypeVar
from .nodes import CommandNode

# Create a type variable for CommandNode or its subclasses
T = TypeVar('T', bound=CommandNode)

class CommandRegistry:
    """Registry for command handlers."""
    
    def __init__(self) -> None:
        """Initialize the command registry."""
        self.special_handlers: Dict[str, Type[CommandNode]] = {}
        self.default_handler: Type[CommandNode] = CommandNode
    
    def register_handler(self, command_name: str, handler_class: Type[T]) -> None:
        """
        Register a special command handler.
        
        Args:
            command_name: The command name or prefix (supports wildcard with '*')
            handler_class: The handler class to register for this command
        """
        # Support wildcard registration
        if command_name.endswith('*'):
            base_name = command_name.rstrip('*')
            self.special_handlers[base_name] = handler_class
        else:
            self.special_handlers[command_name] = handler_class
    
    def create_command_node(self, command_name: str) -> CommandNode:
        """
        Create a command node using registered specialized class or default class.
        
        Args:
            command_name: The name of the command to create a node for
            
        Returns:
            A new command node instance
        """
        # Check for exact match
        if command_name in self.special_handlers:
            return self.special_handlers[command_name](command_name)
        
        # Check for wildcard match
        base_name = command_name.rstrip('*')
        if base_name in self.special_handlers:
            return self.special_handlers[base_name](command_name)
        
        # Default handling
        return self.default_handler(command_name)