import re

# This is a utility module for parsing Markdown content.
# It provides functions to extract code blocks and other elements from Markdown text.

def extract_code_blocks(markdown_text):
    # This function extracts all code blocks from the given Markdown text.
    # It returns them as a dict of lists, where the keys are the programming languages.
    # Each list entry is one code block of that language.
    
    # Code blocks are defined by triple backticks ```lang ... ```, quadruple backticks or tildes.
    # The language is optional.
    # We use a regex to find a starting delimiter, an optional language specifier, the code content, and the matching ending delimiter.
    # The regex has to reference the same delimiter at start and end.
    
    code_block_pattern = re.compile(
        r'(```|````|~~~|~~~~)(\w+)?\n(.*?)\n(\1)', re.DOTALL
    )
    code_blocks = {}
    for match in code_block_pattern.finditer(markdown_text):
        lang = match.group(2) if match.group(2) else 'plaintext'
        code = match.group(3)
        if lang not in code_blocks:
            code_blocks[lang] = []
        code_blocks[lang].append(code)
    return code_blocks

if __name__ == "__main__":
    # Go through the files in solutions/*_debug_response_text*.json and extract code blocks for testing
    import os
    import json
    import fnmatch
    
    base_dir = "solutions"
    filename_wildcard = "*_debug_response_text*.json"

    for filename in os.listdir(base_dir):
        if fnmatch.fnmatch(filename, filename_wildcard):
            with open(os.path.join(base_dir, filename), "r") as f:
                markdown_text = f.read()
                code_blocks = extract_code_blocks(markdown_text)
                # print number of code blocks found
                print(f"Found code blocks in {filename}: { {k: len(v) for k, v in code_blocks.items()} }")
                # Print number of lines for first python or diff code block if exists
                if 'python' in code_blocks:
                    code = code_blocks['python'][0]
                    # count number of lines in code
                    num_lines = len(code.splitlines())
                    print(f" {num_lines} lines of Python code from {filename}.")
                    with open(f"solutions/{filename}_code.py", "w") as out_f:
                        out_f.write(code)
                elif 'diff' in code_blocks:
                    code = code_blocks['diff'][0]
                    # count number of lines in code
                    num_lines = len(code.splitlines())
                    print(f" {num_lines} lines of diff code from {filename}.")
                    with open(f"solutions/{filename}_code.diff", "w") as out_f:
                        out_f.write(code)
