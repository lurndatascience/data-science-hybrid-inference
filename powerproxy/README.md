# PowerProxy-AOAI with Custom LLM Integration

## Overview

This repository showcases a scalable and customizable setup using [PowerProxy-AOAI](https://github.com/timoklimmer/powerproxy-aoai) alongside custom code for a hybrid AI infrastructure. The setup facilitates the deployment of both open-source and proprietary language models (LLMs) to handle requests seamlessly, leveraging smart load balancing and reverse proxy mechanisms.

## Features

- **Hybrid Infrastructure**: Integrates multiple LLMs, including OpenAI's GPT-4, GPT-4 Turbo, and open-source models like LLaMA 3.
- **Smart Load Balancing**: Uses a customized reverse proxy for intelligent routing and load management.
- **Scalability**: Supports both CPU and GPU configurations, making it adaptable to various computational resources.
- **Customizable**: The setup allows for easy integration of additional models and configurations, ensuring flexibility in deployment.

## Getting Started

### Prerequisites

- Docker installed on your machine
- Access to a terminal or command-line interface
- Optional: GPU support for enhanced performance

### Installation

1. **Clone the Repository:**
2. **Pull the Docker Image:**
    ```bash 
   docker pull gcr.io/your-gcr-repo/llama-cpu-python:latest```
3. **Set Up the Environment:**
   Configure the environment variables and model parameters as per your requirements. This setup supports both CPU and GPU configurations.

### Running the Setup

1. **Start the Docker Container:**

   ```bash
   docker-compose up
   ```
2. **Verify the Deployment:**
   Check that the container is up and running, and the models are properly loaded by inspecting the logs or using the monitoring tools.
3. **Test the Setup:**
   Run inference tasks through the reverse proxy by pointing to the appropriate endpoints. Below is an example of how to test with OpenAI and LLaMA models.
   ```bash
   python test/python/openai_test.py
   ```
   For opensource infering:
   ```bash
   python tests/python/test_llama_cpp.py
   ```


