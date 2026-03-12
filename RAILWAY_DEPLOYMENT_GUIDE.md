# Railway Deployment Guide - Rubik's Cube Solver

Follow these steps to deploy your Rubik's Cube Solver web application to Railway.

## Step 1: Push the project to GitHub
1. Ensure all your changes are committed.
2. If you haven't already, create a new repository on GitHub.
3. Push your local code to the GitHub repository:
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

## Step 2: Create a Railway account
1. Go to [railway.app](https://railway.app/).
2. Sign up using your GitHub account for the easiest integration.

## Step 3: Connect the GitHub repository
1. Once logged in, click on **"New Project"**.
2. Select **"Deploy from GitHub repo"**.
3. If this is your first time, you may need to authorize Railway to access your GitHub repositories.

## Step 4: Create a new project in Railway
1. After connecting GitHub, search for and select your `rubiks-cube-solver` repository.
2. Click **"Deploy Now"**.

## Step 5: Deploy from the GitHub repository
1. Railway will automatically detect the `Procfile` and `requirements.txt`.
2. It will start the build process using the official Python buildpack.
3. Wait for the build and deployment to complete.

## Step 6: Verify the deployment logs
1. In your Railway dashboard, click on the service for your repository.
2. Go to the **"Logs"** tab.
3. You should see Gunicorn starting up and listening on the port provided by Railway.
   *Example:* `[INFO] Listening at: http://0.0.0.0:xxxx`

## Step 7: Access the live HTTPS URL
1. In the **"Settings"** tab of your service, look for the **"Networking"** section.
2. Railway provides a default `xxx.up.railway.app` domain with HTTPS enabled.
3. Click on the link to open your live application.

## Step 8: Test the camera functionality in the deployed site
1. Open the live URL on a device with a camera (a smartphone is recommended for better cube scanning).
2. Grant camera permissions when prompted.
3. Verify that the real-time scanner and "Capture" functionality work correctly.
4. Ensure the solution is generated successfully.

---
### Troubleshooting
* **ModuleNotFoundError**: Ensure all packages (e.g., `pycuber`, `numpy`, `opencv-python-headless`) are listed in `requirements.txt`.
* **Port Issues**: Ensure `app.py` reads `os.environ.get("PORT")`.
* **Camera Access**: Camera access requires HTTPS. Railway provides this by default on their `*.up.railway.app` domains.
