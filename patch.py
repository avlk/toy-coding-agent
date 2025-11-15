import re

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

    def __init__(self, header: str, lines: list[str]):
        # Extract original header info
        match = re.match(UNIFIED_DIFF_HUNK_HEADER_REGEX, header)
        if match:
            self.start_original = int(match.group(1))
            self.start_new = int(match.group(3))
        else:
            self.start_original = 0
            self.start_new = 0
        
        self.fuzzy_match = False
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
        # LLM's may add too much context, but it can also create pairs of +/- lines that do not differ
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
        
    def matches_code(self, code_lines: list[str], start_line: int) -> bool:
        # Check if the hunk matches the code lines starting at start_line (0-based)
        for i in range(self.match_count()):
            code_index = start_line + i
            if code_index >= len(code_lines):
                return False

            code_line = code_lines[code_index]
            patch_line = self.match[i]

            if self.fuzzy_match:
                code_line = self.trim_comment(code_line)
                patch_line = self.trim_comment(patch_line)

            if code_line != patch_line:
                if i > 3:
                    print(f"Matched {i}/{self.match_count()} lines starting from {start_line+1}, broke at line {code_index+1}")
                    print(f" src: {code_line}$")
                    print(f"diff: {patch_line}$")
                return False
        return True

    def match_code(self, code_lines: list[str], start_line: int) -> int:
        # Try to match the hunk to code lines starting at start_line (0-based)
        # Return the line where it matches, or None if no match
        for i in range(start_line, len(code_lines) - self.match_count() + 1):
            if self.matches_code(code_lines, i):
                return i
        return None

    def set_fuzzy_match(self, fuzzy: bool):
        self.fuzzy_match = fuzzy

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
    for i, line in enumerate(patch):
        if line.startswith('@@') or line.startswith('+++') or line.startswith('---'):
            if current_hunk_start is not None:
                h = Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:i])
                hunks.append(h)
            current_hunk_start = None

        if line.startswith('@@'):
            current_hunk_start = i

    if current_hunk_start is not None:
        hunks.append(Hunk(patch[current_hunk_start], patch[current_hunk_start + 1:]))

    return hunks

def patch_code(code_lines: list[str], patch_lines: list[str]):
    hunk_list = extract_hunks(patch_lines)
    print(f"Extracted {len(hunk_list)} hunks:")
    # identify all hunks to apply
    application_list = []
    for hunk in hunk_list:
        if hunk.empty():
            print("[SKIP] Useless hunk")
            continue
        print("Hunk", hunk)
        hunk_start = hunk.match_code(code_lines, 0)
        if hunk_start is None:
            print("[WARNING] Can't apply hunk, retrying with fuzzy matching")
            hunk.set_fuzzy_match(True)
            hunk_start = hunk.match_code(code_lines, 0)

        if hunk_start is None:
            print("[ERROR] Still can't apply hunk", hunk)
        else:
            print("[OK] Applying hunk at", hunk_start)
            application_list.append((hunk_start, hunk))

    # Sort application_list by start
    application_list.sort(key=lambda x: x[0])

    source_offset = 0
    for hunk_start, hunk in application_list:
        # print(f"Replacing lines {start_index} to {start_index + hunk.source_length} with {len(new_lines)} new lines.")
        start = hunk_start + source_offset
        code_lines[start:start + hunk.match_count()] = hunk.replace
        source_offset += hunk.replace_count() - hunk.match_count()
    
if __name__ == "__main__":

    for n in range(1,6):
        original_file_name = f"test_sets/patch/test{n}.py"
        patch_file_name = f"test_sets/patch/test{n}.patch"

        print(f"--- Testing patching {original_file_name} with {patch_file_name} ---")
        with open(original_file_name, 'r') as original_file:
            original_content = original_file.read()

        with open(patch_file_name, 'r') as patch_file:
            patch_content = patch_file.read()

        code_lines = original_content.splitlines()
        patch_lines = patch_content.splitlines()
        patch_code(code_lines, patch_lines)
        # save the file to 
        with open(f"solutions/patched_file_v{n+1}.py", "w") as f:
            f.write("\n".join(code_lines))
        print("-" * 40)
    
