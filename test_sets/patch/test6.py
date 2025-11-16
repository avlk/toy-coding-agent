import argparse
import unittest
import re

# --- Constants ---
# ASCII characters for barcode rendering
BINARY_PAIR_TO_CHAR = {
    '00': ' ',  # Space
    '11': '█',  # Full block (black)
    '01': '▌',  # Left half block
    '10': '▐'   # Right half block
}
# ANSI escape codes for terminal colors (black text on white background)
# \033[30m sets text color to black
# \033[47m sets background color to white
# \033[0m resets all attributes
COLOR_BLACK_ON_WHITE = "\033[30m\033[47m"
COLOR_RESET = "\033[0m"

# Barcode dimensions and padding (for Code 128-B, not strictly UPC-A)
BARCODE_HEIGHT = 12
BORDER_WIDTH = 10

# Code 128-B character set and encoding
# This mapping is a simplified representation for digits in Code 128-B.
# A full Code 128-B implementation is significantly more complex and includes
# multiple character sets (A, B, C), shift functions, and FNC characters.
# For UPC-A, only digits are relevant. This mapping provides a binary representation
# for each digit, along with start and stop sequences.
CODE128B_ENCODING = {
    'START_CODE_A': '110100011101',  # Start code for Code 128-B (simplified)
    'STOP_CODE': '110001110101',     # Stop code for Code 128-B
    '0': '0011101100', '1': '0100100011', '2': '0100101100', '3': '0100110001',
    '4': '0111100010', '5': '0111101000', '6': '0111010001', '7': '0101110001', '8': '0101110010', '9': '0101110100',
    'A': '1100010010', 'B': '1100100001', 'C': '1100100100', 'D': '1100111001', 'E': '1101110001', 'F': '1101110100',
    'G': '1101001110', 'H': '1111000010', 'I': '1111001000', 'J': '1111010001', 'K': '1111110001', 'L': '1111110100',
    'M': '1110001110', 'N': '1110011100', 'O': '1110111000', 'P': '1111011100', 'Q': '1111101100', 'R': '1110001011',
    'S': '1100011101', 'T': '1101000101', 'U': '1101010100', 'V': '1101100100', 'W': '1101101101', 'X': '1110100101',
    'Y': '1110101100', 'Z': '1111000101',
}

# --- Helper Functions ---

def text_to_binary(text):
    """Converts text to a binary string based on Code 128-B mapping."""
    # For simplicity and to meet the prompt's constraints, we'll use a single character set (B)
    # and assume the input is compatible. A full Code 128-B implementation is complex.
    binary_string = CODE128B_ENCODING.get('START_CODE_A') # Using START_CODE_A as per original code, though START_CODE_B is more common for alphanumeric
    if not binary_string:
        raise ValueError("Start code not found in encoding map.")

    for char in text.upper(): # Code 128-B is case-insensitive for alphanumeric
        encoding = CODE128B_ENCODING.get(char)
        if encoding:
            binary_string += encoding
        else:
            # If a character is not found, it's an error for this simplified implementation.
            raise ValueError(f"Character '{char}' is not supported in the current Code 128-B mapping.")

    stop_code = CODE128B_ENCODING.get('STOP_CODE')
    if not stop_code:
        raise ValueError("Stop code not found in encoding map.")
    binary_string += stop_code
    return binary_string

def binary_to_barcode_rows(binary_string):
    """Converts a binary string to barcode rows using BINARY_PAIR_TO_CHAR."""
    row_chars = []
    for i in range(0, len(binary_string), 2):
        pair = binary_string[i:i+2]  # Each character in barcode_data represents 2 bits
        row_chars.append(BINARY_PAIR_TO_CHAR.get(pair, ' '))  # Default to space if pair not found
    return "".join(row_chars)

def render_barcode(barcode_data):
    """Renders the barcode data into a string format suitable for terminal output."""
    barcode_lines = []
    barcode_content_width = len(barcode_data) # This is the width of the rendered characters, not bits

    # Add top border
    # The border should be a solid line of the background color (white)
    # For terminal, we use black characters on white background. So border is black.
    border_char = BINARY_PAIR_TO_CHAR['11'] # Use full block for border
    border_line = border_char * (barcode_content_width + 2 * BORDER_WIDTH)
    barcode_lines.append(COLOR_BLACK_ON_WHITE + border_line + COLOR_RESET)

    # Add barcode rows with side borders
    # The barcode content itself should be BARCODE_HEIGHT lines tall.
    for _ in range(BARCODE_HEIGHT): # Use BARCODE_HEIGHT for content rows
        row_str = border_char * BORDER_WIDTH  # Left border
        for char in barcode_data:
            row_str += char
        row_str += border_char * BORDER_WIDTH  # Right border
        barcode_lines.append(COLOR_BLACK_ON_WHITE + row_str + COLOR_RESET)

    # Add bottom border
    barcode_lines.append(COLOR_BLACK_ON_WHITE + border_line + COLOR_RESET) # Use the same border line as top

    return "\\n".join(barcode_lines)

# --- Main Barcode Generation Logic ---

def generate_barcode_string(input_string="Agentic AI"):
    """Generates the barcode string representation for the given input."""
    if not input_string: # Handle empty string case explicitly
        input_string = "Agentic AI"
    
    # Basic validation for UPC-A compatibility (digits only, specific length)
    # The prompt specifies UPC-A but also Code 128-B. Code 128-B is more versatile.
    # We will proceed with Code 128-B encoding for the given string,
    # as a true UPC-A generator would require checksum calculation and specific length constraints.
    # The input string is assumed to be compatible with Code 128-B.
    # Code 128-B supports alphanumeric characters.
    # The error handling for unsupported characters is still relevant.
    try:
        binary_representation = text_to_binary(input_string)
        # barcode_data will be a string of characters like ' ', '█', '▌', '▐'
        barcode_data = binary_to_barcode_rows(binary_representation)
    except ValueError as e:
        print(f"Error generating barcode: {e}", file=sys.stderr)
        return ""  # Return empty string on error
    return render_barcode(barcode_data)

# --- Unit Tests ---
class TestBarcodeGenerator(unittest.TestCase):

    def test_default_input(self):
        """Test barcode generation with default input."""
        barcode_output = generate_barcode_string()
        self.assertIn(BINARY_PAIR_TO_CHAR['11'], barcode_output) # Check for presence of barcode elements
        self.assertIn(BINARY_PAIR_TO_CHAR['00'], barcode_output) # Check for presence of barcode elements
        self.assertIn(COLOR_BLACK_ON_WHITE, barcode) # Check for color codes
        self.assertIn(COLOR_RESET, barcode) # Check for color reset code.

    def test_custom_input(self):
        """Test barcode generation with a custom input string."""
        custom_string = "12345" # Shorter string for testing
        barcode = generate_barcode_string(custom_string)
        self.assertIn(COLOR_BLACK_ON_WHITE, barcode)
        self.assertIn(COLOR_RESET, barcode)

    def test_barcode_height_and_border(self):
        """Test if the barcode has the correct height and border width."""
        barcode = generate_barcode_string("123") # Short string to test structure
        lines = barcode.split('\n')
        # The total height should be BARCODE_HEIGHT (content) + 2 * BORDER_WIDTH (top/bottom borders)
        expected_total_height = BARCODE_HEIGHT + 2 * BORDER_WIDTH
        self.assertEqual(len(lines), expected_total_height, f"Expected height {expected_total_height}, got {len(lines)}")

        # Check if lines have the expected width including borders
        # Calculate the expected width based on the binary representation of "123"
        binary_repr_123 = text_to_binary("123") # This is the bit string
        # Each 2 bits of binary string maps to one character in barcode_data (rendered chars)
        expected_content_width = len(binary_repr_123) // 2
        expected_width = expected_content_width + 2 * BORDER_WIDTH # Content width + left border + right border
        for line in lines:
            # Remove ANSI escape codes for accurate length check
            cleaned_line = re.sub(r'\x1b\[[0-9;]*m', '', line) # More robust way to remove ANSI codes
            # The border characters are also part of the width calculation.
            self.assertEqual(len(cleaned_line), expected_width, f"Line width incorrect. Expected {expected_width}, got {len(cleaned_line)}")
            self.assertTrue(cleaned_line.startswith(border_char * BORDER_WIDTH), "Left border is incorrect.")
            self.assertTrue(cleaned_line.endswith(border_char * BORDER_WIDTH), "Right border is incorrect.")

    def test_scannability_structure(self):
        """ A basic structural check for scannability.
        A true scannability test would involve:
        1. Rendering the barcode to an image file.
        2. Using a barcode scanning library (e.g., python-zxing, pyzbar) to read the image.
        3. Verifying the decoded data matches the input.
        This is beyond the scope of a simple terminal output and requires external tools/libraries.
        For this exercise, we'll check if the output *structure* is plausible for a barcode.
        """
        input_str = "12345678901" # A typical UPC-A length (11 digits + checksum)
        barcode_output = generate_barcode_string(input_str) # This is the rendered string
        binary_repr = text_to_binary(input_str) # This is the bit string
        barcode_rows_data = binary_to_barcode_rows(binary_repr) # This is the string of rendering chars

        # Basic structural checks for scannability:
        # 1. Ensure all four rendering characters are present in the barcode data. (Excluding borders)
        # Check within the actual barcode content part of the output string, not the borders
        # Find the content part by removing borders and ANSI codes
        lines = barcode_output.split('\n')
        if len(lines) > 2: # Ensure there are content lines
            content_line = re.sub(r'\x1b\[[0-9;]*m', '', lines) # Get first content line and remove ANSI codes
            content_part = content_line[BORDER_WIDTH:-BORDER_WIDTH] # Extract only the barcode data part
            self.assertIn(BINARY_PAIR_TO_CHAR['00'], content_part, "Missing space character ('00') in barcode content.")
            self.assertIn(BINARY_PAIR_TO_CHAR['11'], content_part, "Missing full block character ('11') in barcode content.")
            self.assertIn(BINARY_PAIR_TO_CHAR['01'], content_part, "Missing left half block character ('01') in barcode content.")
            self.assertIn(BINARY_PAIR_TO_CHAR['10'], content_part, "Missing right half block character ('10') in barcode content.")

        # 2. Check for the presence of start and stop codes in the binary representation.
        # These are crucial for scanners to identify the barcode.
        self.assertTrue(binary_repr.startswith(CODE128B_ENCODING['START_CODE_A']), f"Barcode does not start with the correct start code. Expected: {CODE128B_ENCODING['START_CODE_A']}, Got: {binary_repr[:len(CODE128B_ENCODING['START_CODE_A'])]}")
        self.assertTrue(binary_repr.endswith(CODE128B_ENCODING['STOP_CODE']), f"Barcode does not end with the correct stop code. Expected: {CODE128B_ENCODING['STOP_CODE']}, Got: {binary_repr[-len(CODE128B_ENCODING['STOP_CODE']):]}")

# --- Command Line Interface ---
def main():
    parser = argparse.ArgumentParser(description="Generate UPC-A barcodes using Code 128-B symbology for terminal output.")
    parser.add_argument("input_string", nargs='?', default="Agentic AI", help="The string to encode into a barcode (defaults to 'Agentic AI').")
    parser.add_argument("--test", action="store_true", help="Run unit tests.")

    args = parser.parse_args()

    if args.test:
        # Run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestBarcodeGenerator)
        runner = unittest.TextTestRunner()
        result = runner.run(suite)  # Run tests
        sys.exit(not result.wasSuccessful()) # Exit with 0 if tests pass, 1 otherwise
    else: # Generate and print barcode
        # Generate and print barcode
        barcode_output = generate_barcode_string(args.input_string)
        print(barcode_output)

if __name__ == "__main__":
    main()