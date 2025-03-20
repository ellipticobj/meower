# Meower Project Guidance

## Build & Development Commands
- Build: `cd meow && ./build.sh`
- Run locally: `python meow/main.py`
- Install dependencies: `pip install -r requirements.txt`

## Code Style Guidelines
- **Imports**: Standard library first, then third-party (with # type: ignore), then local
- **Naming**: snake_case for functions/variables, PascalCase for classes, ALL_CAPS for constants
- **Type Hints**: Required for all function parameters and return values
- **Documentation**: Single-quote docstrings (`'''entry point'''`)
- **Error Handling**: Use try/except blocks with descriptive error messages using colorama
- **Command Structure**: Follow git-like command structure for CLI interface
- **Colors**: Use colorama for terminal formatting (Fore.COLOR, Style.BRIGHT)
- **Optimization**: Keep performance in mind, use Cython for critical paths

## Project Structure
- Core logic in `meow/core/`
- Commands in `meow/commands/`
- Utilities in `meow/utils/`