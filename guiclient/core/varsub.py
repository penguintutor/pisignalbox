''' Standard functions used for substituting in variables
This allows multiple variable substitions within a string
eg. used within the notify messages to the user'''

import re

def substitute_variables(text, app_vars):
    substitution_count = 0
    
    def replacer(match):
        nonlocal substitution_count
        
        # match.group(1) extracts just the variable name (e.g., 'var01' from '{var01}')
        var_name = match.group(1) 
      
        # Fetch the value using global_app_var.get_variable() method
        value = app_vars.get_variable(var_name)
        
        if value is not None:
            substitution_count += 1
            return str(value)
        
        # If the variable doesn't exist (returns None), return the original 
        # placeholder unmodified (e.g., "{var03}"). 
        # Note: Change this to 'return ""' if you prefer to erase missing variables.
        return match.group(0)

    # The regex r'\{(\w+)\}' matches curly braces containing alphanumeric characters or underscores
    processed_text = re.sub(r'\{(\w+)\}', replacer, text)
    
    # Check if one or more substitutions were made
    substitutions_made = substitution_count > 0
    
    return processed_text, substitutions_made

