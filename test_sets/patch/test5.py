#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A pure Python Code 128-B barcode generator and ASCII renderer.

This program generates a Code 128-B barcode from a given input string,
renders it in the terminal using ASCII characters and ANSI color codes,
and includes a test suite to verify its correctness.
"""

import sys
import unittest

# Architecture:
# 1. CONSTANTS: A data structure (CODE_SET_B) holds the Code 128 character set B
#    definitions, mapping each character to its value and binary pattern.
# 2. Code128BGenerator (Class): The core logic unit.
#    - __init__: Initializes with the input string.
#    - _char_to_value: Converts a character to its Code 128 value.
#    - _value_to_pattern: Converts a Code 128 value to its binary bar/space pattern.
#    - _calculate_checksum: Computes the checksum for the input data.
#    - generate_binary_pattern: Assembles the full barcode binary sequence (Start + Data + Checksum + Stop).
#    - render: Converts the binary pattern into a multi-line, colored ASCII string.
# 3. TestBarcodeGenerator (unittest.TestCase): A suite of tests.
#    - Tests checksum calculation, pattern generation for individual characters,
#      and the full binary sequence for a known string ("Code 128") to ensure correctness.
# 4. main (Function): The entry point of the application.
#    - Parses command-line arguments.
#    - Handles the --test flag to run the unit tests.
#    - Instantiates the generator and prints the final barcode.

# --- Constants ---

def _pattern_to_binary(pattern_str: str) -> str:
    """Converts a Code 128 width pattern (e.g., '211214') to a binary string."""
    binary = []
    is_bar = True
    for width in pattern_str:
        char = '1' if is_bar else '0'
        binary.append(char * int(width))
        is_bar = not is_bar
    return "".join(binary)

# The Code 128 character set B table.
# Maps character -> (value, width_pattern)
CODE_SET_B = {
    ' ': (0, '212222'), '!': (1, '222122'), '"': (2, '222221'), '#': (3, '121223'),
    '$': (4, '121322'), '%': (5, '131222'), '&': (6, '122213'), "'": (7, '122312'),
    '(': (8, '132212'), ')': (9, '221213'), '*': (10, '221312'), '+': (11, '231212'),
    ',': (12, '112232'), '-': (13, '122132'), '.': (14, '122231'), '/': (15, '113222'),
    '0': (16, '123122'), '1': (17, '123221'), '2': (18, '223211'), '3': (19, '221132'),
    '4': (20, '221231'), '5': (21, '213212'), '6': (22, '223112'), '7': (23, '312131'),
    '8': (24, '311222'), '9': (25, '321122'), ':': (26, '321221'), ';': (27, '312212'),
    '<': (28, '322112'), '=': (29, '322211'), '>': (30, '212123'), '?': (31, '212321'),
    '@': (32, '232121'), 'A': (33, '111323'), 'B': (34, '131123'), 'C': (35, '131321'),
    'D': (36, '112313'), 'E': (37, '132113'), 'F': (38, '132311'), 'G': (39, '211313'),
    'H': (40, '231113'), 'I': (41, '231311'), 'J': (42, '112133'), 'K': (43, '112331'),
    'L': (44, '132131'), 'M': (45, '113123'), 'N': (46, '113321'), 'O': (47, '133121'),
    'P': (48, '313121'), 'Q': (49, '211331'), 'R': (50, '231131'), 'S': (51, '213113'),
    'T': (52, '213311'), 'U': (53, '213131'), 'V': (54, '311123'), 'W': (55, '311321'),
    'X': (56, '331121'), 'Y': (57, '312113'), 'Z': (58, '312311'), '[': (59, '332111'),
    '\\': (60, '314111'), ']': (61, '221411'), '^': (62, '431111'), '_': (63, '111224'),
    '`': (64, '111422'), 'a': (65, '121124'), 'b': (66, '121421'), 'c': (67, '141122'),
    'd': (68, '141221'), 'e': (69, '112214'), 'f': (70, '112412'), 'g': (71, '122114'),
    'h': (72, '122411'), 'i': (73, '142112'), 'j': (74, '142211'), 'k': (75, '241211'),
    'l': (76, '221114'), 'm': (77, '413111'), 'n': (78, '241112'), 'o': (79, '134111'),
    'p': (80, '111242'), 'q': (81, '121142'), 'r': (82, '121241'), 's': (83, '114212'),
    't': (84, '124112'), 'u': (85, '124211'), 'v': (86, '411212'), 'w': (87, '421112'),
    'x': (88, '421211'), 'y': (89, '212141'), 'z': (90, '214121'), '{': (91, '412121'),
    '|': (92, '111143'), '}': (93, '111341'), '~': (94, '131141'),
    # Special characters
    'START_B': (104, '211214'), 'STOP': (106, '2331112')
}

# --- Barcode Generator Class ---

class Code128BGenerator:
    """
    Generates and renders a Code 128-B barcode.

    This class encapsulates the logic for encoding a string, calculating
    the checksum, generating the full binary pattern, and rendering it
    to a terminal-friendly ASCII format.
    """
    def __init__(self, data: str):
        """
        Initializes the generator with the input data string.
        Args:
            data: The string to encode.
        Raises:
            ValueError: If the data contains characters not in Code 128 Set B.
        """
        if not all(c in CODE_SET_B for c in data):
            unsupported = {c for c in data if c not in CODE_SET_B}
            raise ValueError(f"Input data contains characters not supported by Code 128-B: {unsupported}")
        self.data = data
        self._value_map = {v[0]: k for k, v in CODE_SET_B.items()}

    def _char_to_value(self, char: str) -> int:
        """Gets the Code 128 integer value for a character."""
        return CODE_SET_B[char][0]

    def _value_to_pattern(self, value: int) -> str:
        """Gets the binary pattern for a Code 128 integer value."""
        char = self._value_map[value]
        pattern_str = CODE_SET_B[char][1]
        return _pattern_to_binary(pattern_str)

    def _calculate_checksum(self) -> int:
        """Calculates the checksum value for the barcode."""
        start_b_value = self._char_to_value('START_B')
        total = start_b_value
        for i, char in enumerate(self.data, 1):
            total += self._char_to_value(char) * i
        return total % 103

    def generate_binary_pattern(self) -> str:
        """
        Generates the full binary pattern for the barcode.
        The pattern includes Start B, data, checksum, and stop characters.
        """
        # 1. Start B
        pattern = [_pattern_to_binary(CODE_SET_B['START_B'][1])]
        # 2. Data
        for char in self.data:
            pattern.append(_pattern_to_binary(CODE_SET_B[char][1]))
        # 3. Checksum
        checksum_value = self._calculate_checksum()
        pattern.append(self._value_to_pattern(checksum_value))
        # 4. Stop
        pattern.append(_pattern_to_binary(CODE_SET_B['STOP'][1]))
        pattern.append('11') # Add the 2-module terminator bar
        return "".join(pattern)

    def render(self, height: int = 12, quiet_zone: int = 10) -> str:
        """
        Renders the barcode as a multi-line ASCII string.
        Args:
            height: The number of lines for the barcode height.
            quiet_zone: The number of white spaces for the start/stop fields.
        Returns:
            A string containing the rendered barcode with ANSI color codes.
        """
        binary_pattern = self.generate_binary_pattern()

        # Mapping from binary pairs to ASCII characters
        mapping = {'00': ' ', '11': '█', '01': '▌', '10': '▐'}

        # Process in pairs
        ascii_line = "".join(mapping[binary_pattern[i:i+2]] for i in range(0, len(binary_pattern) & ~1, 2))

        # The total number of modules for a valid Code 128 barcode can be even or odd
        # depending on the data length. If odd, the last module cannot be paired.
        # We handle it by padding with a '0' (space) to form a valid pair.
        if len(binary_pattern) % 2 != 0:
            last_module = binary_pattern[-1]
            if last_module == '1':
                ascii_line += '▐'  # A single '1' is padded with a '0' to form '10' (▐)
            else:  # last_module == '0'
                ascii_line += ' '  # A single '0' is padded with a '0' to form '00' ( )

        # ANSI escape codes for black text on a white background
        white_bg = "\x1b[47m"
        black_fg = "\x1b[30m"
        reset = "\x1b[0m"

        zone_str = ' ' * quiet_zone
        full_line = f"{zone_str}{ascii_line}{zone_str}"
        colored_line = f"{white_bg}{black_fg}{full_line}{reset}"
        return "\n".join([colored_line] * height)

# --- Unit Tests ---

class TestBarcodeGenerator(unittest.TestCase):
    """Test suite for the Code128BGenerator."""

    def test_checksum_calculation(self):
        """Verify checksum calculation for a known string."""
        # For "Agentic AI"
        # Values: A(33) g(71) e(69) n(78) t(84) i(73) c(67) ' '(0) A(33) I(41)
        # Sum = 104 + 33*1 + 71*2 + 69*3 + 78*4 + 84*5 + 73*6 + 67*7 + 0*8 + 33*9 + 41*10
        # Sum = 104 + 33 + 142 + 207 + 312 + 420 + 438 + 469 + 0 + 297 + 410 = 2832
        # 2832 % 103 = 51. Value 51 corresponds to 'S'.
        generator = Code128BGenerator("Agentic AI")
        self.assertEqual(generator._calculate_checksum(), 51)

    def test_pattern_conversion(self):
        """Verify the binary pattern for a known character."""
        self.assertEqual(_pattern_to_binary('212222'), '11011001100')
        self.assertEqual(_pattern_to_binary('211214'), '11010010000')

    def test_full_barcode_pattern_scannability(self):
        """
        Verify the full binary pattern against a known correct sequence.
        This acts as a proxy for a scannability test.
        Input: "Code 128"
        """
        generator = Code128BGenerator("Code 128")
        # Checksum for "Code 128" is 64 (`)
        self.assertEqual(generator._calculate_checksum(), 64)
        
        # Expected sequence: START_B, C, o, d, e, ' ', 1, 2, 8, ` (checksum), STOP
        expected_pattern = "".join([
            _pattern_to_binary(CODE_SET_B['START_B'][1]), # START_B
            _pattern_to_binary(CODE_SET_B['C'][1]),
            _pattern_to_binary(CODE_SET_B['o'][1]),
            _pattern_to_binary(CODE_SET_B['d'][1]),
            _pattern_to_binary(CODE_SET_B['e'][1]),
            _pattern_to_binary(CODE_SET_B[' '][1]),
            _pattern_to_binary(CODE_SET_B['1'][1]),
            _pattern_to_binary(CODE_SET_B['2'][1]),
            _pattern_to_binary(CODE_SET_B['8'][1]),
            _pattern_to_binary(CODE_SET_B['%'][1]),      # Checksum char
            _pattern_to_binary(CODE_SET_B['STOP'][1]),
        ])
        self.assertEqual(generator.generate_binary_pattern(), expected_pattern)

    def test_invalid_character_input(self):
        """Ensure the generator raises an error for unsupported characters."""
        with self.assertRaises(ValueError):
            Code128BGenerator("Test\n") # Newline is not in Set B

    def test_empty_string(self):
        """Test that an empty string generates a valid barcode."""
        generator = Code128BGenerator("")
        # Checksum for empty string is START_B value % 103 = 104 % 103 = 1
        self.assertEqual(generator._calculate_checksum(), 1)
        expected_pattern = "".join([
            _pattern_to_binary(CODE_SET_B['START_B'][1]),
            _pattern_to_binary(CODE_SET_B['!'][1]), # Checksum char for value 1
            _pattern_to_binary(CODE_SET_B['STOP'][1]),
        ]) + '11'
        self.assertEqual(generator.generate_binary_pattern(), expected_pattern)

    def test_render_method_even_length(self):
        """Verify the rendered ASCII output for an even-length binary pattern."""
        # "A" results in an even-length binary pattern (46 modules).
        generator = Code128BGenerator("A")
        binary_pattern = generator.generate_binary_pattern()
        self.assertEqual(len(binary_pattern) % 2, 0)

        # Manually render the binary pattern
        mapping = {'00': ' ', '11': '█', '01': '▌', '10': '▐'}
        expected_ascii = "".join(mapping[binary_pattern[i:i+2]] for i in range(0, len(binary_pattern), 2))

        # Get the rendered output without color codes and quiet zones
        raw_render = generator.render(height=1, quiet_zone=0)
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        actual_ascii = ansi_escape.sub('', raw_render)

        self.assertEqual(actual_ascii, expected_ascii)

    def test_render_method_odd_length(self):
        """Verify rendered ASCII for an odd-length binary pattern."""
        generator = Code128BGenerator("Code 128")
        binary_pattern = generator.generate_binary_pattern()
        self.assertEqual(len(binary_pattern) % 2, 1) # Should be odd

        # Manually render
        mapping = {'00': ' ', '11': '█', '01': '▌', '10': '▐'}
        expected_ascii = "".join(mapping[binary_pattern[i:i+2]] for i in range(0, len(binary_pattern) - 1, 2))
        expected_ascii += '▐' # Last module for "Code 128" pattern is '1'

        # Get actual rendered output
        raw_render = generator.render(height=1, quiet_zone=0)
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        actual_ascii = ansi_escape.sub('', raw_render)

        self.assertEqual(actual_ascii, expected_ascii)

    def test_long_string_handling(self):
        """Test that a long string is handled without errors."""
        long_string = "This is a very long string to test the barcode generator's performance and stability."
        generator = Code128BGenerator(long_string)
        barcode = generator.render()
        self.assertTrue(barcode)
        self.assertEqual(len(barcode.split('\n')), 12)

# --- Main Application Logic ---

def main():
    """
    Main function to parse arguments and run the barcode generator.
    """
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    run_tests = '--test' in sys.argv

    if run_tests:
        print("--- Running Unit Tests ---")
        # Create a TestSuite using the modern TestLoader to avoid deprecation warnings
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestBarcodeGenerator)
        runner = unittest.TextTestRunner()
        result = runner.run(suite)
        if result.wasSuccessful():
            print("\n--- All tests passed successfully ---\n")
        else:
            print("\n--- Some tests failed ---\n")
            # Optionally exit if tests fail
            # sys.exit(1)
        
        # Also print the default barcode as required
        print("--- Default Barcode for 'Agentic AI' ---")
        input_str = "Agentic AI"
    else:
        input_str = args[0] if args else "Agentic AI"

    try:
        generator = Code128BGenerator(input_str)
        barcode = generator.render()
        print(f"Generating barcode for: '{input_str}'")
        print(barcode)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()