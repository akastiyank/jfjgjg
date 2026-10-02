# EduGenie - GitHub run/deployment instructions

## 1. Push the project

```bash
git add .
git commit -m "Fix GitHub Actions and application setup"
git push origin main
```

## 2. GitHub Actions

Open:

**GitHub → Actions → Python application**

The included workflow:
- uses Python 3.11
- installs `requirements.txt`
- performs a Python syntax check
- runs pytest when a `tests` directory exists

## 3. Secrets

Never commit API keys into the repository.

If the application uses Gemini, add the required API key under:

**Repository → Settings → Secrets and variables → Actions**

Use the exact environment variable name expected by the application code.

## 4. Running locally

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the application using the entry point documented by the project.

## Important

GitHub Actions checks/builds the repository. It does not by itself host a FastAPI/Django web application. For a live website, connect the GitHub repository to a web hosting platform and configure the required environment variables there.
