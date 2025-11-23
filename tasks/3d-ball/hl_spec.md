Write code to render an image of a ball with shadow into a text file with ASCII art. 
The output file is N lines each M characters wide.
N and M are commandline arguments, but have default values of 80 and 120 respectively.

The ball has N/2 diameter when measured vertically (lines count) and is in the middle of a picture.
As the characters are taller than they are wide, with the ratio of approximately 2:1 height to width, the printed ball diameter will be N/2 lines high and N characters wide, but will appear round on the screen. 

The ball is located slightly above an infinite horizontal plane, casting a shadow onto the plane. The shadow is partially beneath the ball. 
Horisontal plane in this picture is parallel to the lines of output, it starts at the bottom of the picture. The plane projects into infinite perspective with the horison located (2/3)*N from the bottom.

A light source is outside of the picture and projects light from the top left corner.
The shadow projects to the bottom right of the ball.

No colours are needed, the picture is rendered in shades of grey imitated with ASCII characters.
The ball is rendered so that more light in the picture renders to more dense characters. Unlighted areas of the ball are displayed with spaces or characters of low density. The shadow and the plane under the ball are not photorealistically rendered, but rather imitated with graphics: the shadow itself is rendered with medium-density characters, and the rest of the plane is rendered with spaces.

The program should print the image.
