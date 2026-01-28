import re
import Levenshtein
from pathlib import Path
from enum import Enum
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationMode(Enum):
    """Mode for applying a hunk: modify existing file, create new file, or delete file."""
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"

# Hunk header for a normal unified diff
UNIFIED_DIFF_HUNK_HEADER_REGEX = r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@'
# Hunk header for a unified diff with no line counts like @@ ... @@
UNIFIED_DIFF_HUNK_HEADER_NO_COUNTS_REGEX = r'@@ \.\.\. @@'

def is_unified_diff(patch: list[str]) -> bool:
    # Check if the patch contains unified diff hunk headers
    for line in patch:
        if re.match(UNIFIED_DIFF_HUNK_HEADER_REGEX, line):
            return True
        if re.match(UNIFIED_DIFF_HUNK_HEADER_NO_COUNTS_REGEX, line):
            return True
    return False

def is_unified_diff_no_counts(patch: list[str]) -> bool:
    # Check if the patch contains unified diff hunk headers without line counts
    for line in patch:
        if re.match(UNIFIED_DIFF_HUNK_HEADER_NO_COUNTS_REGEX, line):
            return True
    return False

class Hunk:
    MAX_STARTING_CONTEXT = 3
    MAX_TRAILING_CONTEXT = 3

    def __init__(self, header: str, lines: list[str], filename: str = None, application_mode: ApplicationMode = ApplicationMode.MODIFY):
        # Extract original header info
        match = re.match(UNIFIED_DIFF_HUNK_HEADER_REGEX, header)
        if match:
            self.start_original = int(match.group(1))
            self.start_new = int(match.group(3))
        else:
            self.start_original = 0
            self.start_new = 0
        
        self.filename = filename
        self.application_mode = application_mode
        self.match = []
        self.replace = []

        for line in lines:
            if not line:
                print("Empty line in hunk, truncating hunk context")
                break

            if line.startswith('+'):
                line_content = line[1:]  # Skip the first character (+, -, or space)
                self.replace.append(line_content)
            elif line.startswith('-'):
                line_content = line[1:]  # Skip the first character (+, -, or space)
                self.match.append(line_content)
            else:
                if line[0].isspace():
                    line_content = line[1:]
                else:
                    line_content = line # Fix for faulty LLM patch
                self.match.append(line_content)
                self.replace.append(line_content)

        # Adjust starting and trailing context, and trim match/replace lists accordingly
        # LLMs may add too much context, but it can also create pairs of +/- lines that do not differ
        # We will keep at most MAX_STARTING_CONTEXT lines of context at the start and MAX_TRAILING_CONTEXT lines at the end
        # To do this, we match actual self.match and self.replace lines from the start and end
        # and trim the rest
        actual_start = 0
        # count actual matching context lines from the start
        for i in range(min(len(self.match), len(self.replace))):
            if self.match[i] == self.replace[i]:
                actual_start += 1
            else:
                break
        if actual_start > self.MAX_STARTING_CONTEXT:
            trim_amount = actual_start - self.MAX_STARTING_CONTEXT
            logger.debug(f"Trimming {trim_amount} starting context lines")
            self.match = self.match[trim_amount:]
            self.replace = self.replace[trim_amount:]

        if not self.match or not self.replace:
            return

        actual_end = 0
        # count actual matching context lines from the end
        for i in range(1, min(len(self.match), len(self.replace)) + 1):
            if self.match[-i] == self.replace[-i]:
                actual_end += 1
            else:
                break
        if actual_end > self.MAX_TRAILING_CONTEXT:
            trim_amount = actual_end - self.MAX_TRAILING_CONTEXT
            if trim_amount > 0:
                logger.debug(f"Trimming {trim_amount} trailing context lines")
                self.match = self.match[:-trim_amount]
                self.replace = self.replace[:-trim_amount]

    def empty(self) -> bool:
        # A hunk is not empty if it's for a new file with content to add
        if self.application_mode == ApplicationMode.CREATE and self.replace_count() > 0:
            return False
        # A hunk is not empty if it's for a file deletion with content to remove
        if self.application_mode == ApplicationMode.DELETE and self.match_count() > 0:
            return False
        return self.match_count() == 0 

    def match_count(self) -> int:
        return len(self.match)
    
    def replace_count(self) -> int:
        return len(self.replace)

    def trim_comment(self, line):
        # Remove trailing whitespace
        line = line.rstrip()
        # Remove python comment if there is a python comment
        # For example: "  code # comment" -> "  code"
        # But not: "  print('#')" as it is not a comment
        
        # Regex to match # that's not inside quotes
        # This pattern matches strings and skips # inside them
        pattern = r'''(?:[^'"#]|"[^"]*"|'[^']*')*?(?=#|$)'''
        match = re.match(pattern, line)
        if match:
            return match.group(0).rstrip()
        return line    
        
    def matches_code(self, code_lines: list[str], start_line: int, fuzziness: int) -> bool:
        # Check if the hunk matches the code lines starting at start_line (0-based)
        for i in range(self.match_count()):
            code_index = start_line + i
            if code_index >= len(code_lines):
                return False

            code_line = code_lines[code_index]
            patch_line = self.match[i]

            if fuzziness == 0:
                # With no fuzziness, lines must match exactly
                # If there is a mismatch, return False
                if code_line != patch_line:
                    return False

            if fuzziness > 0:
                # With fuzziness, trim comments and trailing whitespace before comparing
                code_line = self.trim_comment(code_line)
                patch_line = self.trim_comment(patch_line)

            if fuzziness == 1:
                # With fuzziness 1, ignore leading/trailing whitespace and still require exact match of the remaining content
                if code_line != patch_line:
                    return False

            if fuzziness >= 2:
                # With fuzziness 2, match even if a couple of characters differ
                if Levenshtein.distance(code_line, patch_line) > 3:
                    return False

        return True

    def match_code(self, code_lines: list[str], fuzziness: int) -> int:
        # Try to match the hunk to code lines starting at start_line (0-based)
        # Return the line where it matches, or None if no match
        for i in range(0, len(code_lines) - self.match_count() + 1):
            if self.matches_code(code_lines, i, fuzziness):
                return i
        return None

    def __repr__(self) -> str:
        return f"(start_original={self.start_original}, start_new={self.start_new}, match_count={self.match_count()}, replace_count={self.replace_count()})"


def parse_patch_cmd(line: str) -> tuple[str | None, str | None]:
    """
    Parse a unified diff command line.
    
    Args:
        line: A line from a unified diff
    
    Returns:
        A tuple (cmd, arg) where:
        - For '---' lines: ('---', normalized_filename_or_/dev/null)
        - For '+++' lines: ('+++', normalized_filename_or_/dev/null)
        - For '@@' lines: ('@@', content_between_@@_markers)
        - For other lines: (None, None)
    """
    # Handle --- and +++ lines (file markers)
    if line.startswith('---') or line.startswith('+++'):
        cmd = line[:3]
        
        parts = line.split(None, 1)
        if len(parts) > 1:
            filename = parts[1]
            # Remove any prefix unless the path starts with / (like /dev/null)
            if not filename.startswith('/') and '/' in filename:
                filename = filename.split('/', 1)[1]
            return (cmd, filename)
        return (cmd, None)
    
    elif line.startswith('@@'):
        # Extract content between @@ markers
        # Format is typically: @@ -start,count +start,count @@ optional context
        # We want to extract everything between the first and second @@
        if '@@' in line[2:]:
            end_pos = line.index('@@', 2)
            content = line[2:end_pos].strip()
            return ('@@', content)
        return ('@@', line[2:].strip())
    
    return (None, None)


def extract_hunks(patch: list[str]) -> list[Hunk]:
    # Go through the unified diff lines and fix the hunk headers
    # For each hunk header line starting with @@, count the number of added, removed, and unchanged lines
    # The hunk header format is @@ -start,count +start,count @@
    # The hunk ends with another @@, ---, +++, or end of file
    # The header may have incorrect line counts, so we need to recalculate them
    
    def save_current_hunk(last_index: int):
        """Helper to save any pending hunk to the list."""
        nonlocal current_hunk_start
        if current_hunk_start is not None:
            h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:last_index], current_filename, current_mode)
            hunks.append(h)
            current_hunk_start = None
    
    # Identify all hunks and add them to the list
    hunks = []
    current_hunk_start = None
    current_filename = None
    current_mode = ApplicationMode.MODIFY
    
    for i, line in enumerate(patch):
        cmd, arg = parse_patch_cmd(line)
        
        # When we see ---, we're starting a new file section
        if cmd == '---':
            save_current_hunk(i)
                    
            # Detect file creation: --- /dev/null
            if arg == '/dev/null':
                current_mode = ApplicationMode.CREATE
                current_filename = None
            else:
                # Else extract filename from --- line (for normal edits and deletions)
                current_mode = ApplicationMode.MODIFY # Default to MODIFY, may change on +++ line
                current_filename = arg
        # Detect file deletion or get filename for normal edits
        elif cmd == '+++':
            # Check for file deletion
            if arg == '/dev/null':
                current_mode = ApplicationMode.DELETE
            elif current_mode == ApplicationMode.CREATE:
                # Filename for CREATE op
                current_filename = arg
        
        # When we see @@, start recording a new hunk
        elif cmd == '@@':
            save_current_hunk(i)
            current_hunk_start = i

    # Don't forget the last hunk
    save_current_hunk(len(patch))

    return hunks

def apply_hunks_to_code(code_lines: list[str], hunks: list[Hunk], fuzziness: int) -> int:
    """
    Match and apply hunks to code lines.
    
    Args:
        code_lines: List of code lines to modify (modified in place)
        hunks: List of hunks to apply
        fuzziness: Level of fuzzy matching (0=exact, 1=ignore whitespace, 2=allow small differences)
    
    Returns:
        Number of hunks that failed to apply
    """
    application_list = []
    failed_hunks = 0
    
    for hunk in hunks:
        if hunk.empty():
            logger.info("[SKIP] Useless hunk")
            continue
        
        # For file creation, apply at position 0 without matching
        if hunk.application_mode == ApplicationMode.CREATE:
            application_list.append((0, hunk))
            continue
        
        hunk_start = None
        for fuzziness_level in range(fuzziness + 1):
            hunk_start = hunk.match_code(code_lines, fuzziness_level)
            if hunk_start is not None:
                if fuzziness_level > 0:
                    logger.info(f"[WARNING] Hunk {hunk} applied with fuzziness {fuzziness_level}")
                break
        
        if hunk_start is None:
            logger.error(f"[FAIL] Can't apply hunk {hunk}")
            # print the hunk for debugging
            logger.debug("Hunk content:")
            for line in hunk.match:
                logger.debug(line)
            failed_hunks += 1
        else:
            application_list.append((hunk_start, hunk))
    
    # Sort application_list by start position
    application_list.sort(key=lambda x: x[0])
    
    # Apply hunks
    source_offset = 0
    for hunk_start, hunk in application_list:
        start = hunk_start + source_offset
        code_lines[start:start + hunk.match_count()] = hunk.replace
        source_offset += hunk.replace_count() - hunk.match_count()
    
    return failed_hunks

def patch_project(project_dir: Path, patch_lines: list[str], fuzziness: int = 0) -> dict[str, int]:
    """
    Apply a patch to a project directory.
    
    Args:
        project_dir: Root directory of the project (Path object)
        patch_lines: Lines of the unified diff patch
        fuzziness: Level of fuzzy matching (0=exact, 1=ignore whitespace, 2=allow small differences)
    
    Returns:
        Dictionary mapping filename to number of failed hunks for that file.
        Empty dict if all hunks were applied successfully.
    """
    project_dir = project_dir.resolve()  # Get absolute path
    hunk_list = extract_hunks(patch_lines)
    
    # Group hunks by filename
    hunks_by_file = {}
    for hunk in hunk_list:
        if hunk.filename is None:
            logger.warning(f"Hunk without filename: {hunk}")
            continue
        if hunk.filename not in hunks_by_file:
            hunks_by_file[hunk.filename] = []
        hunks_by_file[hunk.filename].append(hunk)
    
    logger.info(f"Extracted {len(hunk_list)} hunks for {len(hunks_by_file)} files")
    
    failures = {}
    
    # Process each file
    for filename, file_hunks in hunks_by_file.items():
        logger.info(f"\nProcessing file: {filename}")
        
        # Construct and validate file path
        file_path = (project_dir / filename).resolve()
        
        # Security check: ensure file is within project directory
        try:
            file_path.relative_to(project_dir)
        except ValueError:
            logger.error(f"File path {file_path} is outside project directory {project_dir}")
            failures[filename] = len(file_hunks)
            continue
        
        # Check if this is a file deletion operation
        delete_op = any(hunk.application_mode == ApplicationMode.DELETE for hunk in file_hunks)
        create_op = any(hunk.application_mode == ApplicationMode.CREATE for hunk in file_hunks)
        
        if delete_op:
            if not file_path.exists():
                logger.warning(f"File {file_path} does not exist (already deleted?)")
                # Consider this a success - file is already gone
                continue
            
            logger.info(f"[DELETE] Deleting file {file_path}")
            try:
                file_path.unlink()
                logger.info(f"[DELETED] {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")
                failures[filename] = len(file_hunks)
            continue
        elif create_op:
            if file_path.exists():
                logger.warning(f"File {file_path} already exists (can't overwrite)")
                failures[filename] = len(file_hunks)
                continue

            logger.info(f"[CREATE] Creating new file {file_path}")
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Start with empty file content
            code_lines = []
        else:
            # Load file content
            try:
                with open(file_path, 'r') as f:
                    code_lines = f.read().splitlines()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                failures[filename] = len(file_hunks)
                continue
        
        # Apply hunks to code lines
        failed_hunks = apply_hunks_to_code(code_lines, file_hunks, fuzziness)
        
        # Report results for this file
        if failed_hunks > 0:
            logger.error(f"Failed to apply {failed_hunks}/{len(file_hunks)} hunks for {filename}")
            failures[filename] = failed_hunks
        else:
            logger.info(f"[OK] Successfully applied {len(file_hunks)} hunks for {filename}")
            
            # Save the modified file
            try:
                with open(file_path, 'w') as f:
                    f.write('\n'.join(code_lines))
                logger.info(f"[SAVED] {file_path}")
            except Exception as e:
                logger.error(f"Failed to save {file_path}: {e}")
                failures[filename] = len(file_hunks)
    
    if not failures:
        logger.info(f"\n✓ Patch application complete. All hunks applied successfully.")
    else:
        logger.error(f"\n✗ Patch application failed. Some hunks could not be applied.")
    
    return failures


def pattern_replace(code_lines: list[str], pattern: str, replacement: str, is_regex: bool = False) -> int:
    """
    Find and replace a pattern in all lines of code.
    
    This function searches for a pattern (substring or regex) in each line
    and replaces all occurrences. Works on individual lines only (not multi-line).
    
    Args:
        code_lines: List of code lines to modify (modified in place)
        pattern: Pattern to search for (substring or regex depending on is_regex)
        replacement: String to replace matches with
        is_regex: If True, treat pattern as regex; if False, treat as literal substring
    
    Returns:
        Total number of replacements made across all lines
    """
    if not pattern:
        logger.warning("Empty pattern provided")
        return 0
    
    total_replacements = 0
    
    for i, line in enumerate(code_lines):
        if is_regex:
            # Count matches before replacement
            matches = re.findall(pattern, line)
            match_count = len(matches)
            # Use regex substitution
            new_line = re.sub(pattern, replacement, line)
        else:
            # Count occurrences for substring
            match_count = line.count(pattern)
            # Use simple string replacement
            new_line = line.replace(pattern, replacement)
        
        # Update line if modified
        if new_line != line:
            code_lines[i] = new_line
            total_replacements += match_count
            logger.debug(f"Replaced {match_count} occurrence(s) in line {i}")
    
    if total_replacements > 0:
        logger.info(f"Made {total_replacements} replacement(s)")
    else:
        logger.info("No matches found")
    
    return total_replacements


def multiline_replace(code_lines: list[str], s_str: list[str], r_str: list[str], only_around_line: int | None = None) -> int:
    """
    Search for all occurrences of a sequence of strings and replace them.
    
    This function finds ALL matches first, then applies all replacements at once
    to avoid recursive matching issues (e.g., searching for {b} and replacing 
    with {a,b} would otherwise match infinitely).
    
    Args:
        code_lines: List of code lines to modify (modified in place)
        s_str: Sequence of strings to search for
        r_str: Sequence of strings to replace with
        only_around_line: If not None, only replace the match closest to this line number (0-based)
    
    Returns:
        Number of replacement operations performed
    """
    if not s_str:
        logger.warning("Empty search string provided")
        return 0
    
    # Find all non-overlapping matches
    matches = []
    search_len = len(s_str)
    i = 0
    
    while i <= len(code_lines) - search_len:
        # Check if sequence matches at position i
        match = True
        for j in range(search_len):
            if code_lines[i + j] != s_str[j]:
                match = False
                break
        
        if match:
            matches.append(i)
            logger.debug(f"Found match at line {i}")
            # Skip past this match to avoid overlapping matches
            i += search_len
        else:
            i += 1
    
    if not matches:
        logger.info("No matches found")
        return 0
    
    logger.info(f"Found {len(matches)} match(es)")
    
    # If only_around_line is specified, find the closest match
    if only_around_line is not None:
        closest_match = min(matches, key=lambda pos: abs(pos - only_around_line))
        matches = [closest_match]
        logger.info(f"Selected closest match at line {closest_match} (target line was {only_around_line})")
    
    # Apply all replacements in reverse order to maintain correct positions
    # Going backwards means earlier replacements don't affect later positions
    for match_pos in reversed(matches):
        code_lines[match_pos:match_pos + search_len] = r_str
    
    logger.info(f"Applied {len(matches)} replacement(s)")
    return len(matches)


def spaceless_distance(a: str, b: str) -> int:
    """Calculate Levenshtein distance ignoring leading/trailing spaces and space number differences."""
    a_nospace = a.strip()
    b_nospace = b.strip()
    a_nospace = re.sub(r'\s+', ' ', a_nospace)
    b_nospace = re.sub(r'\s+', ' ', b_nospace)
    return Levenshtein.distance(a_nospace, b_nospace)

def fuzzy_multiline_replace(code_lines: list[str], s_str: list[str], r_str: list[str], start_range: range) -> int | None:
    """
    Find a close match for sequence of strings around specified position and replace them.
    
    This function finds a match to s_str close to around_line, then applies the replacement (r_str).
    The match allows for some differences (fuzziness).

    Args:
        code_lines: List of code lines to modify (modified in place)
        s_str: Sequence of strings to do an approximate match for
        r_str: Sequence of strings to replace with
        start_range: Range of line numbers to search for a match starting position
    
    Returns:
        True matching line number where a replacement was made, None otherwise
    """
    if not s_str:
        logger.warning("Empty search string provided")
        return None
    
    # Maximum summary Levenshtein distance error: 5 errors + 1 error per line in s_str
    MAX_DISTANCE = 5 + len(s_str)

    # Starting line boundaries
    search_len = len(s_str)

    start_range = range(start_range[0], min(start_range[-1], len(code_lines) - search_len) + 1)

    match_index = -1
    match_distance = MAX_DISTANCE + 1

    # Find all non-overlapping matches
    for i in start_range:
        # Check if sequence matches at position i
        distance = sum(spaceless_distance(code_lines[i + j], s_str[j]) for j in range(search_len))
        
        if distance <= MAX_DISTANCE:
            logger.debug(f"Found match at line {i} with distance {distance}")
            if distance < match_distance:
                match_distance = distance
                match_index = i
    
    if match_index == -1:
        logger.info("No matches found")
        return None
    
    logger.info(f"Found match at line {match_index} with distance {match_distance}")
        
    # Apply all replacements in reverse order to maintain correct positions
    # Going backwards means earlier replacements don't affect later positions
    code_lines[match_index:match_index + search_len] = r_str
    
    logger.info(f"Applied 1 replacement at line {match_index}")
    return match_index

def patch_code(code_lines: list[str], patch_lines: list[str], fuzziness: int = 0):
    hunk_list = extract_hunks(patch_lines)
    logger.info(f"Extracted {len(hunk_list)} hunks:")
    
    failed_hunks = apply_hunks_to_code(code_lines, hunk_list, fuzziness)
    
    if failed_hunks > 0:
        logger.error(f"Patch application failed. {failed_hunks}/{len(hunk_list)} hunks failed to apply.")
    else:
        logger.info(f"Patch application complete. All {len(hunk_list)} hunks applied successfully.")
    return failed_hunks == 0


if __name__ == "__main__":

    for n in range(1,7):
        original_file_name = f"test_sets/patch/test{n}.py"
        patch_file_name = f"test_sets/patch/test{n}.patch"

        print(f"--- Testing patching {original_file_name} with {patch_file_name} ---")
        with open(original_file_name, 'r') as original_file:
            original_content = original_file.read()

        with open(patch_file_name, 'r') as patch_file:
            patch_content = patch_file.read()

        code_lines = original_content.splitlines()
        patch_lines = patch_content.splitlines()
        patch_code(code_lines, patch_lines, fuzziness=2)
        # save the file to 
        with open(f"solutions/patched_file_v{n+1}.py", "w") as f:
            f.write("\n".join(code_lines))
        print("-" * 40)
    
