# Variables
APP_NAME = sda-python-skeleton
VENV_NAME = .venv
PACKAGE_MANAGER = uv
PYTHON = $(PACKAGE_MANAGER) run python
UVICORN = $(PACKAGE_MANAGER) run uvicorn
TEST_DIR = tests
APP_DIR = app
DOCKER = docker

# Install dependencies
install:
	$(PACKAGE_MANAGER) sync

# Run app in dev mode
dev-run:
	$(PACKAGE_MANAGER) run fastapi dev --host 0.0.0.0 --port 8004 

# Run app in production mode make sure postgress credentials are set via .env
prod-run:
	make build && docker run -p 8004:8004 -d $(APP_NAME) 

# This to be run in a docker container
build:
	$(DOCKER) build -t $(APP_NAME) .

# Run tests
test:
	$(PACKAGE_MANAGER) run pytest $(TEST_DIR) --maxfail=1 --disable-warnings -q

# Format code with black
format:
	$(PACKAGE_MANAGER) run black $(APP_DIR) $(TEST_DIR)
	$(PACKAGE_MANAGER) run isort $(APP_DIR) $(TEST_DIR)

# Lint code with flake8
lint:
	$(PACKAGE_MANAGER) run flake8 $(APP_DIR) $(TEST_DIR)

# Clean up environment (remove virtualenv)
clean:
	rm -rf $(VENV_NAME)

# Install development dependencies, optionally with a package
dev-add:
	$(PACKAGE_MANAGER) add --dev $(package); \
	

# Install production dependencies
prod-add:
	$(PACKAGE_MANAGER) add $(package); \
	