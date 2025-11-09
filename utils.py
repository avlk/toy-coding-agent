"""
Utility functions for the coding agent.

This module contains general-purpose utilities that don't depend on
LLM or agent-specific logic.
"""

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
    if isinstance(lines, str):
        return lines
    return '\n'.join(lines)


def format_goals(goals) -> str:
    """
    Format goals list for display/LLM prompts.
    
    Args:
        goals: Either a list of goal strings or already formatted string
    
    Returns:
        Formatted string with bullet points (e.g., "\n- goal1\n- goal2")
    """
    if isinstance(goals, str):
        # Already formatted
        return goals
    # Format list as bulleted items
    return "\n- " + "\n- ".join(goals)


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
    filepath = Path.cwd() / "solutions" / filename
    
    # Convert list to string if needed
    if isinstance(content, list):
        text = '\n'.join(content)
    else:
        text = content
    
    with open(filepath, "w") as f:
        f.write(text)
    print(f"✅ Saved {content_name} to: {filepath}")
    return str(filepath)


# --- Text Processing Functions ---

def clean_code_block(code) -> list:
    """
    Remove code block markers (```) from beginning and end.
    
    Args:
        code: Either a string or list of lines
    
    Returns:
        List of lines with markers removed
    """
    lines = to_lines(code)
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return lines


def normalize_output(text) -> list:
    """
    Normalize output by removing trailing spaces and empty lines at start/end.
    
    Args:
        text: Either a string or list of lines
    
    Returns:
        List of normalized lines
    """
    lines = to_lines(text)
    # remove trailing spaces
    lines = [line.rstrip() for line in lines]
    # remove starting empty lines
    while lines and lines[0] == "":
        lines = lines[1:]
    # remove ending empty lines
    while lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


