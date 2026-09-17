# static source code tests
# eg. looking for missing templates

import ast
from pathlib import Path

def test_all_templates_exist():
    """Statically scan all Python files for render_template calls and verify the HTML file exists."""
    # Resolve the base vlcbserver directory (adjust if your test folder is located elsewhere)
    base_dir = Path(__file__).resolve().parent.parent 
    templates_dir = base_dir / 'templates'
    
    missing_templates = []

    # Walk through all python files in the project
    for py_file in base_dir.rglob('*.py'):
        # Skip test files and virtual environments
        if 'tests' in py_file.parts or 'venv' in py_file.parts:
            continue
            
        with open(py_file, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read(), filename=str(py_file))
            except SyntaxError:
                continue

        # Walk the AST to find function calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if the function being called is render_template
                if isinstance(node.func, ast.Name) and node.func.id == 'render_template':
                    # Extract the first string argument (the template path)
                    if node.args and isinstance(node.args[0], ast.Constant):
                        template_name = node.args[0].value
                        template_path = templates_dir / template_name
                        
                        if not template_path.exists():
                            missing_templates.append(f"'{template_name}' referenced in {py_file.name}")

    # The test fails if the list is not empty, printing out exactly which templates are missing
    assert not missing_templates, f"Found missing template files: {', '.join(missing_templates)}"