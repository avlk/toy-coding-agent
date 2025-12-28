import re
import Levenshtein
from pathlib import Path
from enum import Enum

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
            print(f"Trimming {trim_amount} starting context lines")
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
                print(f"Trimming {trim_amount} trailing context lines")
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


def extract_hunks(patch: list[str]) -> list[Hunk]:
    # Go through the unified diff lines and fix the hunk headers
    # For each hunk header line starting with @@, count the number of added, removed, and unchanged lines
    # The hunk header format is @@ -start,count +start,count @@
    # The hunk ends with another @@, ---, +++, or end of file
    # The header may have incorrect line counts, so we need to recalculate them
    
    # Identify all hunks and add them to the list
    hunks = []
    current_hunk_start = None
    current_filename = None
    current_mode = ApplicationMode.MODIFY
    
    for i, line in enumerate(patch):
        # When we see ---, we're starting a new file section
        # Reset state and prepare to determine file operation type
        if line.startswith('---'):
            # First, save any pending hunk
            if current_hunk_start is not None:
                h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:i], current_filename, current_mode)
                hunks.append(h)
                current_hunk_start = None
            
            # Reset state for new file section
            current_mode = ApplicationMode.MODIFY
            current_filename = None
            
            # Detect file creation: --- /dev/null or --- a/dev/null
            parts = line.split(None, 1)
            if len(parts) > 1:
                if '/dev/null' in parts[1]:
                    current_mode = ApplicationMode.CREATE
                else:
                    # Extract filename from --- line (for normal edits and deletions)
                    filename = parts[1]
                    if filename.startswith('a/'):
                        filename = filename[2:]
                    if '/dev/null' not in filename:
                        current_filename = filename
        
        # Detect file deletion or get filename for normal edits
        elif line.startswith('+++'):
            # Save any pending hunk (shouldn't normally happen here)
            if current_hunk_start is not None:
                h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:i], current_filename, current_mode)
                hunks.append(h)
                current_hunk_start = None
            
            parts = line.split(None, 1)
            if len(parts) > 1:
                if '/dev/null' in parts[1]:
                    # This is a file deletion
                    current_mode = ApplicationMode.DELETE
                    # Filename should already be set from --- line
                else:
                    # Normal file or new file
                    filename = parts[1]
                    if filename.startswith('b/'):
                        filename = filename[2:]
                    if '/dev/null' not in filename:
                        current_filename = filename
        
        # When we see @@, start recording a new hunk
        elif line.startswith('@@'):
            # Save any pending hunk first
            if current_hunk_start is not None:
                h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:i], current_filename, current_mode)
                hunks.append(h)
            
            current_hunk_start = i

    # Don't forget the last hunk
    if current_hunk_start is not None:
        h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:], current_filename, current_mode)
        hunks.append(h)

    return hunks

def patch_project(project_dir: Path, patch_lines: list[str], fuzziness: int = 0) -> bool:
    """
    Apply a patch to a project directory.
    
    Args:
        project_dir: Root directory of the project (Path object)
        patch_lines: Lines of the unified diff patch
        fuzziness: Level of fuzzy matching (0=exact, 1=ignore whitespace, 2=allow small differences)
    
    Returns:
        True if all hunks were applied successfully, False otherwise
    """
    project_dir = project_dir.resolve()  # Get absolute path
    hunk_list = extract_hunks(patch_lines)
    
    # Group hunks by filename
    hunks_by_file = {}
    for hunk in hunk_list:
        if hunk.filename is None:
            print(f"[WARNING] Hunk without filename: {hunk}")
            continue
        if hunk.filename not in hunks_by_file:
            hunks_by_file[hunk.filename] = []
        hunks_by_file[hunk.filename].append(hunk)
    
    print(f"Extracted {len(hunk_list)} hunks for {len(hunks_by_file)} files")
    
    all_success = True
    
    # Process each file
    for filename, file_hunks in hunks_by_file.items():
        print(f"\nProcessing file: {filename}")
        
        # Construct and validate file path
        file_path = (project_dir / filename).resolve()
        
        # Security check: ensure file is within project directory
        try:
            file_path.relative_to(project_dir)
        except ValueError:
            print(f"[ERROR] File path {file_path} is outside project directory {project_dir}")
            all_success = False
            continue
        
        # Check if this is a file deletion operation
        delete_op = any(hunk.application_mode == ApplicationMode.DELETE for hunk in file_hunks)
        create_op = any(hunk.application_mode == ApplicationMode.CREATE for hunk in file_hunks)
        
        if delete_op:
            if not file_path.exists():
                print(f"[WARNING] File {file_path} does not exist (already deleted?)")
                # Consider this a success - file is already gone
                continue
            
            print(f"[DELETE] Deleting file {file_path}")
            try:
                file_path.unlink()
                print(f"[DELETED] {file_path}")
            except Exception as e:
                print(f"[ERROR] Failed to delete {file_path}: {e}")
                all_success = False
            continue
        elif create_op:
            if file_path.exists():
                print(f"[WARNING] File {file_path} already exists (can't overwrite)")
                all_success = False
                continue

            print(f"[CREATE] Creating new file {file_path}")
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
                print(f"[ERROR] Failed to read {file_path}: {e}")
                all_success = False
                continue
        
        # Build application list for this file
        application_list = []
        failed_hunks = 0
        
        for hunk in file_hunks:
            if hunk.empty():
                print("[SKIP] Useless hunk")
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
                        print(f"[WARNING] Hunk {hunk} applied with fuzziness {fuzziness_level}")
                    break
            
            if hunk_start is None:
                print(f"[FAIL] Can't apply hunk {hunk}")
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
        
        # Report results for this file
        if failed_hunks > 0:
            print(f"[ERROR] Failed to apply {failed_hunks}/{len(file_hunks)} hunks for {filename}")
            all_success = False
        else:
            print(f"[OK] Successfully applied {len(file_hunks)} hunks for {filename}")
            
            # Save the modified file
            try:
                with open(file_path, 'w') as f:
                    f.write('\n'.join(code_lines))
                print(f"[SAVED] {file_path}")
            except Exception as e:
                print(f"[ERROR] Failed to save {file_path}: {e}")
                all_success = False
    
    if all_success:
        print(f"\n✓ Patch application complete. All hunks applied successfully.")
    else:
        print(f"\n✗ Patch application failed. Some hunks could not be applied.")
    
    return all_success


def patch_code(code_lines: list[str], patch_lines: list[str], fuzziness: int = 0):
    hunk_list = extract_hunks(patch_lines)
    failed_hunks = 0
    print(f"Extracted {len(hunk_list)} hunks:")
    # identify all hunks to apply
    application_list = []
    for hunk in hunk_list:
        if hunk.empty():
            print("[SKIP] Useless hunk")
            continue
        # print("Hunk", hunk)
        hunk_start = None
        for fuzziness_level in range(fuzziness + 1):
            hunk_start = hunk.match_code(code_lines, fuzziness)
            if hunk_start:
                if fuzziness_level > 0:
                    print(f"[WARNING] Hunk {hunk} applied with fuzziness {fuzziness_level}")
                break
        if hunk_start is None:
            print(f"[FAIL] Can't apply hunk {hunk}")
            failed_hunks += 1
        else:
            # print("[OK] Applying hunk at", hunk_start)
            application_list.append((hunk_start, hunk))
        
    # Sort application_list by start
    application_list.sort(key=lambda x: x[0])

    source_offset = 0
    for hunk_start, hunk in application_list:
        # print(f"Replacing lines {start_index} to {start_index + hunk.source_length} with {len(new_lines)} new lines.")
        start = hunk_start + source_offset
        code_lines[start:start + hunk.match_count()] = hunk.replace
        source_offset += hunk.replace_count() - hunk.match_count()
    
    if failed_hunks > 0:
        print(f"Patch application failed. {failed_hunks}/{len(hunk_list)} hunks failed to apply.")
    else:
        print(f"Patch application complete. All {len(hunk_list)} hunks applied successfully.")
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
    
