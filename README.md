# [<img src="/frontend/src/assets/metis.svg" alt="Logo of Metis">](https://metis.scads.ai)

[**Metis**](https://metis.scads.ai) is a chatbot with the goal of providing students support in many aspects of their studies.
It is designed to be modular and support many different types of bots with different underlying architectures.
Metis aims to assist the user based on their learning type (sensing, feeling, intuitive, thinking).

**Check Metis out [here](https://metis.scads.ai)**

This project is maintained by the research group [KI_FEM](https://tu-dresden.de/ing/informatik/ai/mci/forschung/nachwuchsforschungsgruppe-bedarfsorientiertes-ai-coaching-fuer-studierende-naic/ki-basiertes-coaching-studierender) at ScaDS.AI.

## Installation

- Clone the repository
- We use `uv` for managing Python versions and packages. Follow the installation guide: https://docs.astral.sh/uv/getting-started/installation/
- `uv` will automatically install the correct Python version and packages when you first run the backend server

### Create the .env environment file

- Go to /backend and /frontend, duplicate the `.env.example` file and rename it to `.env`
- Fill in the values as described in the file

## Start the services

### Backend

1. **Go to the src directory**

   ```sh
   cd backend/src
   ```

2. **Run FastAPI using uv**

    ```sh
    uv run fastapi dev
    ```

    uv will install the Python version, create a virtual environment and install the packages required to run the backend API. Then, Fastapi will start the backend on <http://localhost:8000> and reload automatically when changes in the files are detected.

### Frontend

Make sure you have the following installed on your machine:

- [Node.js 22](https://nodejs.org/)
- [npm 10.8.3](https://www.npmjs.com/)

1. **Open a new tab in your console and go to the frontend directory:**

   ```sh
   cd frontend
   ```

2. **Install dependencies:**

   ```sh
   npm i
   ```

3. **Start the development server**

   ```sh
   npm run dev
   ```

    This will start the frontend on localhost: <http://localhost:5173/>

## LLMs

### Keys

Keys for the LLMs are set in the backend/.env file. Mainly, metis uses OpenAI-compatbile APIs.

### Local LLMs

When using the locally cached HuggingFace models, the model is dowloaded when you run the chatbot for the first time. It is stored in your cache folder (tyically `~/.cache`) on your local machine.

**Please note**: An internet connection is required to run the application and download the model.

## Database

We use a PostgreSQL database to manage content data. At the same time, we integrate the vector database using the pgvector extension into postgres.

### Set up development database

Use Docker to set up a PostgreSQL database. Use the following image to have the PGVector extensions installed automatically. Either type these commands in the terminal, or use Docker Desktop to run the container. Note, that you will have to manually enter the port and Environment Variable during container creation!

```sh
docker pull pgvector/pgvector:pg17
docker run --env=POSTGRES_PASSWORD=admin --env=PG_MAJOR=17 --env=PG_VERSION=17.4-1.pgdg120+2 --network=bridge -p 5432:5432 -d pgvector/pgvector:pg17
```

This pulls the pgvector image and runs it with the port 5432 forwarded to your machine. Then, the database connection URL should be `DATABASE_URL="postgresql://postgres:admin@localhost:5432/metis"`. Set this in the .env file.

### Create the data

After starting backend and frontend, head over to the admin page: http://localhost:5173/admin . Enter the admin key, set in the backend/.env. On the admin page, connect to the DB, create the schema, and then load the data. This will load the modules, books, embeddings, etc. into the DB. Here, you can also drop the schema if you want to clean the DB again.

IMPORTANT: For the open-source release of metis, all data from the database file has been removed. If you wish to host your own version of metis, add your data to the database manually or by editing the metis_data.sql file.

### Optional: View data in the DB

If you need to view the data in the DB, you could use the console to attach to the postgres docker container, but it's way easier if you use the pgadmin UI. For this, you can install pgadmin using Docker:

```sh
docker pull dpage/pgadmin4
docker run --env=PGADMIN_DEFAULT_EMAIL=admin@admin.com --env=PGADMIN_DEFAULT_PASSWORD=admin --env=PYTHONPATH=/pgadmin4 --network=bridge -p 8443:443 -p 8080:80 -d dpage/pgadmin4:latest
```

Then, go to http://localhost:8080/ and log in using username "admin@admin.com" and password "admin". Add a new server with the connection URL "host.docker.internal" (since pgadmin and postgres are both in Docker), port 5432, user name postgres and database "metis".

If set up correctly, you can view the schema, tables, data, execute queries and edit columns, data, etc.

## Tests

### Backend tests

Backend tests are performed by `pytest`. To run the tests, navigate into `/backend` and run

```sh
pytest [-v] [-vv]
```

To merge a PR, you also have to check that code quality checks succeed using:

```sh
ruff check src/
```

(if ruff is not installed yet, run `uv sync` and then `uv run ruff check src/`)

#### Creating new tests

New tests can be added by creating a new file in the `/backend/tests` folder named `test_[name]`. Follow the scheme of the other test files. It's best to sort the tests by the folder structure of the class you are trying to test.

### Frontend tests

TODO
