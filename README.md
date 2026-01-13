# SDA V2 Learning Management System

## Requirements

1. Install uv
2. Install Docker
3. Clone

    ```bash
    git clone git@ssh.dev.azure.com:v3/maternityfoundationv2/sda_v2/utilities
    ```

4. Get database/docker-compose.yml

5. run

    ```bash
    docker compose -f database/docker-compose.yml up -d
    ```

6. Install packages

    ```bash
    make install
    ```

7. Run dev environment

     ```bash
    make run-dev
    ```
