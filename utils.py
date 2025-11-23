"""
Utility functions for the coding agent.

This module contains general-purpose utilities that don't depend on
LLM or agent-specific logic.
"""

import re
import random
from pathlib import Path


# --- String/List Conversion Helpers ---

def to_lines(text) -> list:
    """
    Convert text to list of lines.
    
    Args:
        text: Either a string (will be split on newlines) or already a list
    
    Returns:
        List of strings (lines)
    """
    if text is None:
        return []
    if isinstance(text, list):
        return text
    return text.splitlines()


def to_string(lines) -> str:
    """
    Convert lines to string.
    
    Args:
        lines: Either a list of strings (will be joined with newlines) or already a string
    
    Returns:
        String with lines joined by newlines
    """
    if lines is None:
        return ""
    if isinstance(lines, str):
        return lines
    return '\n'.join(lines)

def select_variant(lines: list[str], variant: str) -> list[str]:
    """
    Filters lines and for the lines that start with "?{variant} " prefix, select only those lines with the correct variant.
    Args:
        lines: List of strings (lines)
        variant: Variant string to filter on (e.g., "a", "b", etc.)
    Returns:
        Filtered list of strings (lines)
    """
    selected_lines = []
    prefix = f"?{variant} "
    for line in lines:
        if line.startswith(prefix):
            selected_lines.append(line[len(prefix):])
        elif not line.startswith("?"):
            selected_lines.append(line)
    return selected_lines

def format_goals(goals) -> str:
    """
    Format goals list for display/LLM prompts.
    
    Args:
        goals: Either a list of goal strings or already formatted string
    
    Returns:
        Formatted string with bullet points (e.g., "\n- goal1\n- goal2")
    """
    goals_list = to_lines(goals)
    # Iterate over goals_list and add list bullet (-) if it is not there
    for i in range(len(goals_list)):
        if not goals_list[i].strip().startswith("-"):
            goals_list[i] = "- " + goals_list[i]

    return "\n".join(goals_list)


# --- File I/O Functions ---

def load_file(filepath: str) -> str:
    """Load file contents as string."""
    with open(filepath, "r") as f:
        return f.read()


def load_file_lines(filepath: str) -> list:
    """Load file contents as list of lines."""
    with open(filepath, "r") as f:
        return f.read().splitlines()


def save_to_file(filename: str, content, content_name="output") -> str:
    """
    Save content to a file in the solutions directory.
    
    Args:
        filename: Name of the file to save
        content: Either a string or a list of strings (will be joined with newlines)
    
    Returns:
        Absolute path to the saved file
    """
    if not content:
        return
 
    filepath = Path.cwd() / "solutions" / filename
    
    # Convert list to string if needed
    if isinstance(content, list):
        text = '\n'.join(content)
    else:
        text = content
    
    with open(filepath, "w") as f:
        f.write(text)
    print(f"💾 Saved {content_name} to: {filepath}")
    return str(filepath)


# --- Text Processing Functions ---

def clean_code_block(code) -> list:
    """
    Remove code block markers (``` or ~~~) from beginning and end.
    Also removes empty lines in sequences if there are more than 2 consecutive empty lines.
    
    Args:
        code: Either a string or list of lines
    
    Returns:
        List of lines with markers removed and trailing empty lines trimmed
    """
    lines = to_lines(code)
    
    # Remove code block markers (both ``` and ~~~)
    if lines and (lines[0].strip().startswith("```") or lines[0].strip().startswith("~~~")):
        lines = lines[1:]
    if lines and (lines[-1].strip() == "```" or lines[-1].strip() == "~~~"):
        lines = lines[:-1]
    
    # Trim empty lines if there are more than 2
    empty_line_count = 0
    new_lines = []
    for line in lines:
        if line.strip() == "":
            empty_line_count += 1
            if empty_line_count <= 2:
                new_lines.append(line)
        else:
            empty_line_count = 0
            new_lines.append(line)
    lines = new_lines
    return lines


def code_quality_gate(code) -> bool:
    """
    Returns True if the code meets quality standards, False otherwise
    """
    lines = to_lines(code)

    max_line_length = 2048 # model often returns very long lines with no meaning, repeating same one or two characters
    max_same_lines = 100 # model often hallucinates, returning the same line until MAX_TOKENS

    # Return False if there are too long lines or there are more than X consecutive lines with the same content
    same_line_count = 0
    for i, line in enumerate(lines):
        if len(line) > max_line_length:
            print(f"❌ Line {i+1} exceeds max length ({max_line_length})")
            return False
        if i > 0 and line == lines[i-1]:
            same_line_count += 1
            if same_line_count > max_same_lines:
                print(f"❌ Line {i+1} is a duplicate of the previous line ({same_line_count} times)")
                return False
        else:
            same_line_count = 0

    return True

def find_code_blocks(markdown_text, delimiter="~~~", language="python"):
    """ 
        The function extracts code blocks from the given Markdown text.  
        The code blocks start with delimiter + language and end 
        with the same delimiter or the end of the text.
        Returns a list of code blocks found.
    """
    pattern = re.compile(
        rf'{re.escape(delimiter)}{language}\n(.*?)(?:\n{re.escape(delimiter)}|$)',
        re.DOTALL
    )
    code_blocks = pattern.findall(markdown_text)
    return code_blocks

