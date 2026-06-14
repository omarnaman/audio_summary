# Audio Summary

## Disclaimer
This repository was generated with the help of AI (Gemini 2.5 Pro)

## Overview

This is a Flask web application that uses the Google Gemini API to summarize audio files. It provides a simple interface to upload an audio file, and it will generate a markdown summary of the content.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

1.  **Clone the repository:**
    ```sh
    git clone <repository-url>
    cd audio_summary
    ```

2.  **Create a `.env` file:**
    This application requires a Google Gemini API key. Create a `.env` file in the root of the project and add your API key:
    ```
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

## Running the Application

Once you have completed the setup steps, you can run the application using Docker Compose.

1.  **Build and run the container:**
    ```sh
    docker-compose up --build
    ```
    This command will build the Docker image for the application and start the service. The `-d` flag can be added to run the container in detached mode.

2.  **Access the application:**
    Once the container is running, you can access the application in your web browser at:
    [http://localhost:5000](http://localhost:5000)

## Stopping the Application

To stop the application, run the following command in the project's root directory:
```sh
docker-compose down
```
This will stop and remove the containers defined in the `docker-compose.yml` file.




## TODO

- [ ]  Extend with callbacks to be able to post summaries to a different notes app, e.g. obsidian or onenote
