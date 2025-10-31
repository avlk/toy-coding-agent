import re
import unidiff

UNIFIED_DIFF_HUNK_HEADER_REGEX = r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@'

def is_unified_diff(patch: list[str]) -> bool:
    # Check if the patch contains unified diff hunk headers
    for line in patch:
        if re.match(UNIFIED_DIFF_HUNK_HEADER_REGEX, line):
            return True
    return False

def fix_patch(patch: list[str]) -> None:
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
                h = range(current_hunk_start, i)
                hunks.append(h)
            current_hunk_start = None

        if line.startswith('@@'):
            current_hunk_start = i

    if current_hunk_start is not None:
        hunks.append(range(current_hunk_start, len(patch)))

    print(f"Identified {len(hunks)} hunks in the patch.")

    # Process each hunk to fix the header
    for hunk in hunks:
        header_line = patch[hunk.start]
        # print(f"Processing hunk header: {header_line.strip()}")
        
        # Count lines
        removed = 0
        added = 0
        unmodified = 0
        for line in patch[hunk.start+1:hunk.stop]:
            if line.startswith('-'):
                removed += 1
            elif line.startswith('+'):
                added += 1
            else:
                unmodified += 1

        # Extract original header info
        match = re.match(UNIFIED_DIFF_HUNK_HEADER_REGEX, header_line)
        if match:
            old_start = int(match.group(1))
            new_start = int(match.group(3))
            
            # Create fixed header
            fixed_header = f"@@ -{old_start},{unmodified+removed} +{new_start},{unmodified+added} @@\n"
            if fixed_header != header_line:
                print(f"Fixed hunk header: {fixed_header.strip()}")
                patch[hunk.start] = fixed_header  # Update the original patch line
        else:
            # If the header line doesn't match, just keep it as is
            print(f"Warning: Hunk header did not match expected format: {header_line.strip()}")
    

def check_hunk_start(code_lines: list[str], hunk: unidiff.Hunk, start_line: int) -> bool:
    # Check if the hunk can be applied starting at start_line in code_lines
    hunk_line_index = 0
    code_line_index = start_line - 1  # Convert to 0-based index

    while hunk_line_index < len(hunk):
        hunk_line = hunk[hunk_line_index]
        if hunk_line.is_context:
            if code_line_index >= len(code_lines) or code_lines[code_line_index] != hunk_line.value:
                return False
            code_line_index += 1
        elif hunk_line.is_removed:
            if code_line_index >= len(code_lines) or code_lines[code_line_index] != hunk_line.value:
                return False
            code_line_index += 1
        # For added lines, we don't check against code_lines
        hunk_line_index += 1
    return True

def apply_hunk(code_lines: list[str], hunk: unidiff.Hunk, adjust_start: int) -> list[str]:
    # Apply the hunk to the code lines
    # Check that the hunk starts at the correct line by matching first context lines and removed lines
    # If the hunk does not start with the expected lines, try to find the correct starting position
    # code_lines are modified in place
    # the difference between added and removed lines is returned to be used as adjust_start for next hunk

    start_index = hunk.source_start # start_index is 1-based
    start_index += adjust_start
    
    hunk_match = check_hunk_start(code_lines, hunk, start_index)
    adjustment = 0
    if not hunk_match:
        # Create a list of possible offsets a 1,-1,2,-2,...5,-5, up to max_offset
        max_offset = 200
        offsets = []
        for i in range(1, max_offset + 1):
            offsets.append(i)
            offsets.append(-i)

        # Find the correct starting position
        for offset in offsets:
            test_start = start_index + offset
            if test_start < 1:
                continue
            hunk_match = check_hunk_start(code_lines, hunk, test_start)
            if hunk_match:
                print(f"Adjusted hunk start from line {start_index} to {test_start} (diff {test_start - start_index}, adjust_start {adjust_start})")
                adjustment = test_start - start_index
                start_index = test_start
                break
        if not hunk_match:
            print(f"Could not find matching start for hunk at line {start_index}. Skipping hunk.")
            return 0  # No changes made

    # Now apply the hunk
    # # Build the new lines from the hunk
    new_lines = [line.value for line in hunk if not line.is_removed]
    # Replace start_index to start_index + removed_lines with new_lines
    # print(f"Replacing lines {start_index} to {start_index + hunk.source_length} with {len(new_lines)} new lines.")
    code_lines[start_index-1:start_index + hunk.source_length-1] = new_lines

    added_lines = sum(1 for line in hunk if line.is_added)
    removed_lines = sum(1 for line in hunk if line.is_removed)
    # Adjust next line offset by difference of lines + hunk adjustment made
    return added_lines - removed_lines + adjustment

def patch_code(code: list[str], patch_lines: list[str]) -> None:
    patch_set = unidiff.PatchSet(patch_lines)
    adjust_start = 0
    for patched_file in patch_set:
        print(f"Patching file: {patched_file.path}")
        for hunk in patched_file:
            # print(f"Hunk from line {hunk.source_start} to {hunk.source_start + hunk.source_length} in original, "
            #     f"line {hunk.target_start} to {hunk.target_start + hunk.target_length} in patched.")
            adjust_start += apply_hunk(code, hunk, adjust_start)

if __name__ == "__main__":
    # original_file_name = "test_sets/patch/nqueens_6702_v1.py"
    # patch_file_name = "test_sets/patch/nqueens_6702_v2.py"
    original_file_name = "test_sets/patch/interp_5165_v1.py"
    patch_file_name = "test_sets/patch/interp_5165_v2.patch"

    with open(original_file_name, 'r') as original_file:
        original_content = original_file.read()

    with open(patch_file_name, 'r') as patch_file:
        patch_content = patch_file.read()

    code_lines = original_content.splitlines()
    patch_lines = patch_content.splitlines()

    fix_patch(patch_lines)
    # patch_set = unidiff.PatchSet(patch_lines)

    # adjust_start = 0
    # for patched_file in patch_set:
    #     print(f"Patching file: {patched_file.path}")
    #     for hunk in patched_file:
    #         print(f"Hunk from line {hunk.source_start} to {hunk.source_start + hunk.source_length} in original, "
    #             f"line {hunk.target_start} to {hunk.target_start + hunk.target_length} in patched.")
    #         adjust_start += apply_hunk(code_lines, hunk, adjust_start)
    #         # save intermediate result after each hunk
    #         with open(f"intermediate_patched_code{hunk.target_start}.py", 'w') as intermediate_file:
    #             intermediate_file.write('\n'.join(code_lines))
    patch_code(code_lines, patch_lines)

    patched_code = '\n'.join(code_lines)
    print("----- Patched Code -----")
    # print(patched_code)

