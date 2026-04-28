# Denny's KPI Restaurant Health Scorecard

This Streamlit app cleans the Denny's Main Table CSV, removes total rows, calculates a revised restaurant health score, assigns quintiles, and creates an interactive dashboard.

## Project Folder

Put these files in your local folder:

```bash
dennys_kpi_project/
├── app.py
├── scoring_model.py
├── requirements.txt
```

Your terminal already shows:

```bash
MacBook-Pro:dennys_kpi_project amroosman$
```

So place the files directly inside that folder.

## Step 1: Open your project folder

```bash
cd ~/dennys_kpi_project
```

If your folder is somewhere else, type `cd ` and drag the folder into Terminal.

## Step 2: Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3: Install requirements

```bash
pip install -r requirements.txt
```

## Step 4: Run the app

```bash
streamlit run app.py
```

## Step 5: Upload files in the dashboard

Upload:

1. `Main Table (40).csv`
2. Optional: `Weekly Sales and Missing & Incorrect Data for 2026M03.csv`

The app automatically removes:
- owner-level `Total` rows
- blank rows
- Power BI filter-note rows

## Scoring Model

The final restaurant health score uses these weights:

| Category | Weight |
|---|---:|
| Sales / Demand | 30% |
| Guest Experience | 25% |
| Operational Execution | 30% |
| Training / Readiness | 15% |

Raw AUV and Weekly AUV are not included in the score. They are used as context only.

## Quintile Logic

- Quintile 1 = strongest restaurants
- Quintile 5 = highest support need

## Notes

The report period is:

```text
Rolling 12 Months as of 4/1/2026
```

Google Rating L90D and BBI L90D remain last-90-day metrics because the source columns are labeled L90D.

Missing & Incorrect % is treated as an off-premise execution KPI.


## Push to GitHub

Target repo:

```text
https://github.com/Amro2023/dennys-kpi-project
```

From your local folder:

```bash
cd ~/dennys_kpi_project

git init
git branch -M main
git remote add origin https://github.com/Amro2023/dennys-kpi-project.git

git add .
git commit -m "Initial Denny's KPI Streamlit dashboard"
git push -u origin main
```

If the repo already has files and Git rejects the push, run:

```bash
git pull origin main --allow-unrelated-histories
git add .
git commit -m "Add Denny's KPI Streamlit dashboard"
git push -u origin main
```

If `remote origin already exists`, run:

```bash
git remote set-url origin https://github.com/Amro2023/dennys-kpi-project.git
git push -u origin main
```
