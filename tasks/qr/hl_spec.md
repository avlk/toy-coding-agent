Write a code to generate QR codes. The code shall integrate text or URL.

QR code size shall be adjustable with the length of it's payload. 

The code shall be printed out in ASCII characters and shall be readable with smartphone. 
As the code is displayed with white characters on black background, black areas shall be displayed with spaces and white with printable characters.
A border of one pixel shall be provided around the ASCII image to provide correct contrast field and make the QR code readable from the screen.
Take into account that console characters have 2:1 height to width ratio.

Take a reasonable assumption on the maximum payload length.

Create a set of unit tests to check the functionality. 

The program shall print the QR code for the string that is provided to the input, or "Agentic AI" if nothing is provided.

When run with --tests parameter, it prints the default QR code and runs all tests. 

The use of external libraries to render a QR code (like qrcode) is not allowed for the task completion.
