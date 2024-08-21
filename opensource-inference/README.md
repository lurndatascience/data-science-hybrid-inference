# LLaMA 3 API Deployment

## Overview

This repository provides a setup for deploying the LLaMA 3 API using Docker. The deployment leverages the `llama-cpp-python` package to serve the LLaMA model and is configured to dynamically adjust based on the system's resources.

## Features

- **Dynamic Resource Management**: The setup automatically configures batch size and CPU threads based on the available hardware.
- **Model Download and Management**: Automatically downloads the specified LLaMA model if it's not already available.
- **Flexible Configuration**: Environment variables are used to set up model parameters and download URLs, allowing for easy customization.
- **Dockerized Deployment**: The API is containerized using Docker, ensuring a consistent environment and easy deployment.

## Getting Started

### Prerequisites

- Docker installed on your machine
- Basic knowledge of shell scripting and Docker

### Installation

#### Clone the Repository

### Prepare the Environment

Ensure that the environment variables `MODEL` and `MODEL_DOWNLOAD_URL` are set. These variables define the path to the model and its download URL.

You can set these environment variables in your shell or include them in a `.env` file:

**Setting Environment Variables in Shell:**

   ```bash
   export MODEL_NAME="Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
   export MODEL_DOWNLOAD_URL="https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf?download=true"

