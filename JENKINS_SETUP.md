# Jenkins Setup For This Repo

## What Jenkins Does

Think of Jenkins like a small robot helper.

- When you push code, Jenkins wakes up.
- It picks up your project.
- It checks if the backend is healthy.
- It checks if the frontend can be packed nicely.
- If something is broken, it tells you before you deploy.

For this repository, Jenkins will:

- run FastAPI tests in `fastapi/`
- build the React app in `react/`
- save the React build files
- show backend test results in Jenkins

## What I Added

- `Jenkinsfile`: the recipe Jenkins reads
- this guide: the step-by-step setup

## Before You Start

Your Jenkins machine needs these tools installed:

- Git
- Python 3.10 or newer
- Node.js 20 or newer
- npm

Useful Jenkins plugins:

- Pipeline
- Git
- JUnit

## Step By Step

### 1. Put your code in GitHub or another Git server

Jenkins pulls code from a Git repository, so your project should be pushed to a branch like `main`.

### 2. Open Jenkins

Open your Jenkins URL in the browser and log in.

### 3. Create a new pipeline job

1. Click `New Item`.
2. Type a name like `ecom-ci`.
3. Pick `Pipeline`.
4. Click `OK`.

### 4. Connect the Git repository

In the job configuration:

1. Go to `Pipeline`.
2. Choose `Pipeline script from SCM`.
3. Choose `Git`.
4. Paste your repository URL.
5. Pick your branch, for example `*/main`.
6. Keep the script path as `Jenkinsfile`.

This tells Jenkins: "Please read the recipe from the file sitting in my repo."

### 5. Save and run it

1. Click `Save`.
2. Click `Build Now`.

Jenkins will now follow the steps from the `Jenkinsfile`.

## What The Pipeline Does

### Stage 1: Check Tools

Jenkins asks:

- "Do I have Python?"
- "Do I have Node?"
- "Do I have npm?"

If one is missing, Jenkins stops early.

### Stage 2: Backend Test

Jenkins goes into `fastapi/` and:

1. makes a Python virtual environment
2. installs backend packages
3. runs `pytest`
4. saves the test report so Jenkins can show green/red results

Before running tests, the pipeline also sets:

- `APP_ENV=test`
- `DEBUG=false`
- `JWT_SECRET_KEY=test-secret-key`

This is done so Jenkins uses a clean test setup and does not get confused by random machine settings.

### Stage 3: Frontend Build

Jenkins goes into `react/` and:

1. installs packages with `npm ci`
2. runs `npm run build`
3. saves the built frontend files from `react/dist/`

## Very Simple Picture

You can imagine Jenkins doing this:

1. "Fetch the toy box."
2. "Test the API toy."
3. "Pack the React toy."
4. "Tell me if the toys are okay."

## How To Run On Every Push

If you want Jenkins to start automatically after every push, choose one of these:

- GitHub webhook to Jenkins
- Poll SCM in Jenkins

Webhook is better because Jenkins runs only when code actually changes.

## GitHub Webhook Steps

### In Jenkins

1. Open the job.
2. Click `Configure`.
3. In `Build Triggers`, enable `GitHub hook trigger for GITScm polling`.
4. Save.

### In GitHub

1. Open your repository.
2. Go to `Settings`.
3. Open `Webhooks`.
4. Click `Add webhook`.
5. Payload URL should be:

```text
http://YOUR-JENKINS-URL/github-webhook/
```

6. Content type: `application/json`
7. Choose `Just the push event`
8. Save

Now every push can tap Jenkins on the shoulder and say, "Wake up, there is new code."

## If Build Fails

### Backend test fails

This usually means:

- a test is broken
- a dependency did not install
- Python version is too old

### Frontend build fails

This usually means:

- Node version is too old
- a package install failed
- the React code has a build error

## Common Fixes

- Make sure Jenkins agent has `python3`, `node`, and `npm`
- Make sure Jenkins can access your Git repo
- Make sure the branch name is correct
- If using private GitHub repos, add credentials in Jenkins

## Important Note About Deployment

This pipeline is CI first. That means it checks and builds the project.

It does not deploy your app to a server yet.

If you want, the next step can be:

- deploy backend after tests pass
- deploy frontend after build passes
- build Docker images

## Files To Look At

- `Jenkinsfile`
- `fastapi/requirements-dev.txt`
- `react/package.json`
