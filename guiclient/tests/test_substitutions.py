import pytest
import re
from core import substitute_variables


# Pytest Mock & Fixtures

class MockAppVars:
    """A simple mock class to simulate global_app_vars."""
    def __init__(self, data):
        self._variables = data

    def get_variable(self, var_name):
        return self._variables.get(var_name)

@pytest.fixture
def app_vars():
    """Provides a populated MockAppVars instance for the tests."""
    return MockAppVars({
        "var01": "apple",
        "var02": 42,          # Testing non-string returns
        "name": "Stewart"
    })


# Test Cases

@pytest.mark.parametrize(
    "input_text, expected_text, expected_changed",
    [
        # 1. No variables present
        ("Hello world", "Hello world", False),
        
        # 2. Single valid variable
        ("Value is {var01}", "Value is apple", True),
        
        # 3. Multiple valid variables
        ("User {name} has {var02} items", "User Stewart has 42 items", True),
        
        # 4. Missing variable (should remain unmodified)
        ("Missing {var03}", "Missing {var03}", False),
        
        # 5. Mixed valid and missing variables
        ("Found {var01} but not {missing}", "Found apple but not {missing}", True),
        
        # 6. Adjacent variables with no spaces
        ("{var01}{var02}", "apple42", True),
        
        # 7. Variables that appear multiple times
        ("{var01} and {var01}", "apple and apple", True),
        
        # 8. Empty string
        ("", "", False),
        
        # 9. Invalid variable formats (should be ignored by regex)
        ("Empty {} and space { }", "Empty {} and space { }", False),
    ]
)
def test_substitute_variables(app_vars, input_text, expected_text, expected_changed):
    """Tests variable substitution across various string scenarios."""
    result_text, changed = substitute_variables(input_text, app_vars)
    
    assert result_text == expected_text
    assert changed == expected_changed