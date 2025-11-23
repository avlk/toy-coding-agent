# 3D ASCII Ball

This is a medium-range task that asks the agent to render a ball with a shadow using ASCII characters. It does not require a lot of creativity and does not ask for any unit tests.

However, there were some hurdles before it worked correctly:

- The coder tends to locate the horizontal plane vertically, and it required some prompt fine-tuning to clearly explain what the plane looks like
- The goal/use case refiner tends to lose some important details when refining or invent details that were not there originally
- The reviewer is very picky about details (geometry, ASCII character selection) that do not contribute to image quality, making the agent continue for multiple improvement rounds with no perceivable picture change

It is solvable by the `gemini-2.5-flash` model and takes 4-10 iterations to complete.

## Tips

Run with `--no-refine-goals` parameter to preserve the original prompt

Try setting `gemini-3-pro-preview` as a **reviewer** model, and it will likely complete in fewer iterations. Having a more intelligent reviewer improves the feedback loop and makes the coder do less useless work. An intelligent reviewer is also less picky about meaningless details.
