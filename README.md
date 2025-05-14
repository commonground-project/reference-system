# Reference System

A system for generating comprehensive news summaries based on user comments and references, enhanced with web search data.

## Overview

This system takes user discussion data containing facts and references, processes this data to generate an initial summary, and then enriches that summary with additional context from web searches. The final result is a comprehensive news article that combines user-provided information with broader web context.

## Key Features

- **XML-based Data Processing**: Improved data structure using XML format for better clarity and organization
- **Web Search Integration**: Uses the `web-search-agent` package to enhance summaries with web search results
- **Asynchronous Processing**: Efficiently processes multiple issues concurrently
- **Docker-ready**: Packaged for easy deployment by the backend team

## Project Structure

```
reference-system/
├── config/                # Configuration files
│   └── example.env        # Example environment variables
├── data/                  # Data files for examples and testing
│   └── few_shot_example_xml.txt  # XML-formatted examples
├── src/                   # Source code
│   ├── main.py            # Main entry point
│   ├── output/            # Output results
│   └── utils/             # Utility modules
│       ├── api_client.py  # API client for fetching data
│       ├── data_processor.py  # Data formatting and processing
│       └── summary_generator.py  # Summary generation logic
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Getting Started

### Prerequisites

- Python 3.11.11 or higher
- OpenAI API key
- `web-search-agent` package

### Environment Setup

1. Copy `config/example.env` to `config/.env`
2. Add your OpenAI API key to `.env`:
   ```
   OPENAI_API_KEY="your-api-key-here"
   JWT_TOKEN="your-jwt-token-for-api-access"
   ```

### Installation

#### Local Development

```bash
# Install dependencies
poetry install

# Run the application
python src/main.py
```

#### Docker Deployment

```bash
# Build Docker image
docker build -t reference-system:latest .

# Run Docker container
docker run --env-file config/.env -v $(pwd)/src/output:/app/src/output reference-system:latest
```

## Configuration

### API Keys and Authentication

This application requires the following API keys and tokens to function properly:

1. **OpenAI API Key**: Required for language model functionality
2. **JWT Token**: Required for authentication with the backend API

To configure these credentials:

1. Copy the template configuration file:
   ```bash
   cp config/example.env config/.env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual API keys:
   ```
   # OpenAI API credentials 
   OPENAI_API_KEY="your-openai-api-key-here"

   # JWT token for API access
   JWT_TOKEN="your-jwt-token-here"
   
   # Other configuration values...
   ```

3. Save the file and keep it secure. Never commit this file to version control.

The application will automatically load these environment variables at runtime.

## Usage

The system processes news articles in the following way:

1. Fetches user discussion data from the API
2. Processes and formats data using XML structure
3. Generates an initial summary using LLM
4. Enhances the summary with web search results
5. Outputs the final article to `src/output/results.json`
6. (Optional) Updates the platform with the generated content

## Integration with Backend

This system is designed to integrate with the backend through a CI/CD pipeline:

1. AI team creates a feature branch
2. After passing tests, the feature is merged to `dev` branch
3. PR to `main` branch triggers integration tests with backend
4. After successful tests, merging to `main` triggers Docker image build
5. The image is published to GitHub Container Registry
6. Backend team is notified of the new image for deployment

## Contributing

Please follow these guidelines when contributing:

1. Create feature branches from `dev`
2. Use `ruff` and `black` for code formatting
3. Write unit tests for new functionality
4. Submit PRs to `dev` branch for review

