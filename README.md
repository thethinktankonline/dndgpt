# D&D GPT - AI-Powered Dungeons & Dragons Assistant

A Django-based web application that provides AI-powered assistance for Dungeons & Dragons gameplay, using OpenAI's GPT models and LangChain for enhanced functionality.

This project utilizes the D&D 5th Edition System Reference Document (SRD), which is available under the Creative Commons Attribution 4.0 International License. The SRD content is provided by Wizards of the Coast and can be found at: https://www.dndbeyond.com/srd?srsltid=AfmBOorj-vF3ByjLOFxGjRyQ4OuJ0vulRSK7mdSRRBGCevHvPOt2uj8W

## Version

0.2.0

## Features

- AI-powered D&D assistant
- PDF processing capabilities
- Image processing with Pillow
- Django REST API
- OpenAI GPT integration
- LangChain for advanced AI workflows

## Requirements

- Python 3.10+
- UV package manager

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd dndgpt_v2
```

2. Install UV (if not already installed):

```bash
pip install uv
```

3. Create and activate virtual environment:

```bash
uv venv
```

4. Activate the virtual environment:

```bash
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

5. Install dependencies:

```bash
uv pip install -e .
```

6. Install development dependencies (optional):

```bash
uv pip install -e ".[dev]"
```

7. Set up Django:

```bash
python manage.py migrate
python manage.py collectstatic
```

8. Create a superuser (optional):

```bash
python manage.py createsuperuser
```

## Running the Application

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
OPENAI_API_KEY=your-openai-api-key
```

## Development

### Code Formatting

```bash
black .
```

### Linting

```bash
flake8 .
```

### Type Checking

```bash
mypy .
```

### Testing

```bash
pytest
```

## License

Copyright (c) 2025 ThinkTank, LLC. All rights reserved.

### D&D Content License

This project utilizes content from the Dungeons & Dragons 5th Edition System Reference Document (SRD) v5.2.1, which is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0). 

- **D&D SRD Content**: Licensed under CC BY 4.0 by Wizards of the Coast
- **Source**: [D&D Beyond SRD](https://www.dndbeyond.com/srd)
- **License**: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)

The SRD content includes rules, spells, monsters, and other game mechanics that are freely available for use under the Creative Commons license. All D&D-related content in this project is derived from or references this open-source material.
