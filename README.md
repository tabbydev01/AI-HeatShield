# 🔥 AI HeatShield

## Hyperlocal Heat Risk & Urban Decision Intelligence Platform

AI HeatShield is a hyperlocal urban heat intelligence and decision-support platform built for FortyGuard Hackathon'26.

Instead of only displaying temperature, AI HeatShield transforms spatial heat information into actionable intelligence by combining:

Hyperlocal heat mapping

Explainable heat-risk scoring

Urban hotspot detection

Environmental risk-driver analysis

12-hour scenario-based heat-risk outlook

Historical comparison

Population vulnerability analysis

Action recommendations

Urban cooling intervention simulation

The platform is designed to help cities, campuses, communities, outdoor operations, and urban planners understand:

Where is heat risk highest, why is it happening, who may be most affected, what could happen next, and what actions could reduce the risk?

# 1. Problem

Extreme urban heat is becoming an increasingly important challenge for cities.

Traditional weather applications generally provide city-level values such as:

Temperature

Humidity

Weather conditions

Forecast

However, heat exposure can vary significantly within a small geographic area.

Different locations may experience different thermal conditions because of:

Building density

Road surfaces

Solar exposure

Vegetation

Tree canopy

Shade availability

Urban geometry

Surface materials

A single city-wide temperature therefore does not always provide enough information for local decision-making.

The bigger challenge is not simply:

"What is the temperature?"

The more useful questions are:

Where are the dangerous heat hotspots?

What environmental factors are driving the risk?

Which population groups may require greater attention?

How could the risk change over the next several hours?

What interventions could potentially reduce the risk?

AI HeatShield is designed around these questions.

# 2. Solution

AI HeatShield converts hyperlocal heat information into a complete urban heat decision-intelligence pipeline.


Heat Data

   ↓

Spatial Normalization

   ↓

Heat Risk Engine

   ↓

Hotspot Detection

   ↓

Explainable Risk Drivers

   ↓

Forecast Intelligence

   ↓

Historical Comparison

   ↓

Population Vulnerability Analysis

   ↓

Action Recommendations

   ↓

Urban Intervention Simulation

   ↓

Interactive Decision Dashboard


The objective is to move from:


Raw Heat Data


to:


Actionable Urban Decisions


# 3. Core Features

## 3.1 Hyperlocal Heat Map

AI HeatShield displays the analysis area as interactive spatial heat cells.

Each cell can contain information such as:

Temperature

Heat index

Relative humidity

Wet-bulb temperature

Solar radiation

Heat-risk score

Heat-risk category

Users can click a heat cell to analyze that specific zone.

The dashboard then updates the associated:

Risk score

Risk drivers

Forecast

Recommendations

Historical comparison

Vulnerability assessment

Intervention scenarios

## 3.2 Multi-Layer Spatial Visualization

The interactive map supports multiple analytical views.

### Risk Layer

Displays relative heat-risk severity.

### Temperature Layer

Displays spatial temperature variation.

### Heat Index Layer

Displays variation in perceived thermal conditions.

This allows users to understand how environmental conditions vary across the analysis area.

# 4. Explainable Heat-Risk Engine

AI HeatShield uses an explainable weighted risk model.

The current model considers:

| Factor | Weight |

|---|---:|

| Temperature | 30% |

| Heat Index | 25% |

| Wet-Bulb Temperature | 15% |

| Relative Humidity | 10% |

| Solar Radiation | 20% |

The resulting score is normalized between:


0 – 100


Risk categories are:

| Score | Risk Level |

|---|---|

| 0–25 | LOW |

| 26–50 | MODERATE |

| 51–70 | HIGH |

| 71–85 | VERY HIGH |

| 86–100 | CRITICAL |

Because the system retains individual factor contributions, the dashboard can explain which environmental variables contribute most strongly to the calculated risk.

This makes the model more interpretable than a simple unexplained risk number.

# 5. Explainable Risk Drivers

For every selected zone, AI HeatShield ranks environmental contributors to the calculated heat risk.

Examples include:


Temperature

Heat Index

Solar Radiation

Wet Bulb

Humidity


The dashboard identifies:


Primary Risk Driver

Secondary Risk Driver


and visualizes individual factor contributions.

This helps answer:

Why is this location currently considered risky?

# 6. Heat Hotspot Detection

AI HeatShield analyzes all spatial cells and ranks them according to their heat-risk score.

The dashboard highlights the highest-risk zones as priority hotspots.

For each hotspot, the system provides information including:

Rank

Zone ID

Temperature

Risk score

Risk category

Risk-factor contributions

This can help decision-makers prioritize limited cooling or emergency-response resources.

# 7. 12-Hour Risk Outlook

AI HeatShield includes a short-term heat-risk forecasting layer.

The current prototype evaluates scenario checkpoints at:


Now

+3 Hours

+6 Hours

+9 Hours

+12 Hours


For each point it estimates:

Temperature

Heat index

Solar radiation

Heat-risk score

Risk category

This allows users to see whether conditions may:


Improve

Remain Elevated

Become More Dangerous


### Demo Forecast Transparency

These forecast points are scenario-generated projections used to demonstrate the decision-support workflow, including when the primary heatmap source is LIVE. They are not observed future FortyGuard or Open-Meteo measurements and should not be interpreted as an operational meteorological forecast. FortyGuard's Create Heatmap capability can support future timestamps within its documented forecast window; integrating those future heatmaps is a planned upgrade.

# 8. Historical Heat Comparison

AI HeatShield includes a historical comparison module.

The dashboard compares current conditions with an estimated baseline using:

Temperature

Heat index

Risk score

The system classifies the relative trend as:


WARMING

COOLING

STABLE


It also displays a recent historical-style risk progression for visualization.

### Historical Data Transparency

The current demonstration historical values are generated from an estimated baseline.

They are used to demonstrate the historical-comparison workflow and must not be interpreted as observed FortyGuard historical measurements.

The production architecture can replace this layer with actual historical observations when available.

# 9. Population Vulnerability Intelligence

The same thermal conditions may affect different groups differently.

AI HeatShield therefore includes a heuristic population-vulnerability decision-support layer.

Current demonstration personas include:


Outdoor Worker

Elderly

Child

General Public


The system adjusts the base environmental risk using persona-specific sensitivity assumptions and relevant environmental conditions.

For each persona the dashboard provides:

Adjusted risk score

Risk category

Sensitivity multiplier

Primary reason

Recommended action

### Important Disclaimer

Persona vulnerability scores are heuristic decision-support estimates.

They are not medical, clinical, diagnostic, or individual health-risk predictions.

# 10. Recommendation Engine

AI HeatShield converts heat-risk intelligence into practical actions.

Depending on environmental conditions, recommendations may include:

### Human Safety


Restrict peak-hour outdoor exposure


### Urban Design


Increase temporary or permanent shade


### Hydration


Deploy hydration points


### Vulnerable Population Protection


Prioritize high-risk groups


### Operations


Move strenuous outdoor activity to cooler hours


This transforms the platform from a monitoring dashboard into a decision-support system.

# 11. Urban Intervention Simulator

One of the key features of AI HeatShield is its urban cooling intervention simulator.

The current system evaluates scenarios including:


Shade Structures

Tree Canopy

Cool / Reflective Surface

Combined Cooling Strategy


For every scenario, the dashboard shows:


Current Risk Score

        ↓

Estimated New Risk Score

        ↓

Risk Reduction


Example:


Current Risk: 82

Tree Canopy Scenario

        ↓

Estimated Risk: 69

Estimated Reduction: 13 points


This can help planners compare possible mitigation strategies before deciding where further investigation or investment may be useful.

### Intervention Transparency

Intervention results are scenario-based decision-support estimates.

They are not validated causal predictions and should not be interpreted as guaranteed real-world outcomes.

# 12. FortyGuard Integration Architecture

AI HeatShield includes an adapter architecture for integrating FortyGuard heat intelligence.

The deployed FortyGuard flow is:


User selects an area

        ↓

AI HeatShield Backend

        ↓

FortyGuard Heatmap API

        ↓

Asynchronous Activity

        ↓

Activity Status Polling

        ↓

Heatmap Result

        ↓

Normalization Layer

        ↓

AI HeatShield Risk Engine

        ↓

Decision Intelligence

        ↓

Interactive Dashboard


The integration layer supports the asynchronous workflow where a heatmap request returns an activity identifier and the application polls for completion. The integration uses POST /v1/heatmap to create a heatmap task and GET /v1/status/{activity_id} to retrieve completion/results, with the API key supplied in the api-key header.

FortyGuard + Open-Meteo Data Fusion

FortyGuard remains the primary and central spatial heat source. The deployed live path uses FortyGuard hyperlocal temperature cells as the spatial field. Because the selected tcm heatmap response supplies temperature but not every environmental variable used by the prototype risk engine, AI HeatShield enriches the same location/date/hour with Open-Meteo Historical Weather API context.

Variable

Source / Method

Spatial role

Hyperlocal temperature

FortyGuard Heatmap API

Primary per-cell spatial signal

Relative humidity

Open-Meteo historical reanalysis/context

Area-level contextual input

Wet-bulb temperature

Open-Meteo historical reanalysis/context

Area-level contextual input

Solar radiation

Open-Meteo historical reanalysis/context

Area-level contextual input

Heat index

Calculated from FortyGuard temperature + contextual humidity

Derived per heat cell

Open-Meteo values are contextual weather-grid/reanalysis data and are not presented as FortyGuard hyperlocal measurements. Spatial variation in the live heatmap continues to come from FortyGuard temperature cells.

# 13. API-Efficient Heatmap Caching

Interactive dashboards can generate many frontend requests when users click different spatial cells.

Creating a new upstream heatmap task for every click would be inefficient.

AI HeatShield therefore maintains a backend heatmap cache.

Current cache duration:


15 minutes


Flow:


First Analysis Request

        ↓

Load Heatmap

        ↓

Cache Heatmap

        ↓

User Selects Another Cell

        ↓

Reuse Cached Heatmap

        ↓

Run Local Decision Analysis


This reduces unnecessary upstream requests and improves dashboard responsiveness.

# 14. Data Source Transparency

AI HeatShield explicitly tracks the source of the active dataset.

The backend supports three source states.

## LIVE


LIVE


The heatmap was successfully retrieved through the FortyGuard API. In the hackathon demo, LIVE means a live API integration fetching real FortyGuard data; it does not mean that the displayed timestamp is current real-time weather.

## DEMO


DEMO


The application is intentionally using the bundled synthetic demonstration dataset.

## DEMO_FALLBACK


DEMO_FALLBACK


A live request was attempted but failed, so the application safely returned demonstration data instead.

This distinction prevents fallback data from being presented as successful live observations.

# 15. Demo Mode

AI HeatShield can operate without an external API key.

If no FortyGuard API key is configured, the application automatically runs using the bundled Phoenix demonstration dataset.

The demo dataset contains approximately:


210 hyperlocal heat cells


around Phoenix, Arizona.

The dataset is deterministic and was generated specifically for product demonstration.

It is synthetic data and must not be interpreted as real FortyGuard observations.

Demo mode allows:

Development without API dependency

Reliable hackathon demonstrations

UI testing

Risk-engine testing

Offline product demonstrations

# 16. Live Mode

When a valid FortyGuard API key is configured, the adapter requests FortyGuard heatmap data through the live API integration. The verified hackathon deployment uses a deterministic New York City historical request (2024-07-15 at 14:00 local time) so the demo remains reproducible.

Environment configuration:


FORTYGUARD_API_KEY=your_api_key_here

FORTYGUARD_BASE_URL=https://api.fortyguard.com

DEMO_MODE=false


API keys must never be committed to Git.

The repository should contain only:


.env.example


while the real:


.env


remains ignored.

# 17. System Architecture


┌─────────────────────────────────────────────┐

│                 USER                        │

│          Urban Planner / Analyst            │

└─────────────────────┬───────────────────────┘

                      │

                      ▼

┌─────────────────────────────────────────────┐

│             NEXT.JS FRONTEND                │

│                                             │

│  Dashboard                                  │

│  Interactive Leaflet Map                    │

│  Risk Visualization                         │

│  Forecast                                   │

│  Historical Intelligence                    │

│  Vulnerability Intelligence                 │

│  Recommendations                            │

│  Intervention Simulator                     │

└─────────────────────┬───────────────────────┘

                      │

                      │ REST API

                      ▼

┌─────────────────────────────────────────────┐

│             FASTAPI BACKEND                 │

│                                             │

│  Unified Analysis API                       │

│  Data Source Tracking                       │

│  Heatmap Cache                              │

└─────────────────────┬───────────────────────┘

                      │

        ┌─────────────┴─────────────┐

        ▼                           ▼

┌───────────────────┐       ┌─────────────────┐

│ FortyGuard Adapter│       │ Demo Data Layer │

│                   │       │                 │

│ Heatmap Request   │       │ Synthetic       │

│ Status Polling    │       │ Phoenix Dataset │

│ Normalization     │       │                 │

└─────────┬─────────┘       └────────┬────────┘

          │                          │

          └────────────┬─────────────┘

                       ▼

┌─────────────────────────────────────────────┐

│          DECISION INTELLIGENCE              │

│                                             │

│  Risk Engine                                │

│  Hotspot Detection                          │

│  Risk Explainability                        │

│  Recommendation Engine                      │

│  Forecast Engine                            │

│  Historical Comparison                      │

│  Vulnerability Engine                       │

│  Intervention Simulator                     │

└─────────────────────────────────────────────┘


# 18. Technology Stack

## Frontend


Next.js 16

React 19

TypeScript

Tailwind CSS

Leaflet

React Leaflet


## Backend


Python

FastAPI

Pydantic

HTTPX

Uvicorn


## External Heat Intelligence


FortyGuard API Adapter


## Mapping


Leaflet

OpenStreetMap

CARTO basemap


## Development


Git

GitHub

VS Code

Python Virtual Environment

npm


# 19. Project Structure


AI-HeatShield/

│

├── backend/

│   │

│   ├── app/

│   │   ├── schemas/

│   │   ├── services/

│   │   ├── api.py

│   │   ├── config.py

│   │   └── main.py

│   │

│   ├── demo_data/

│   │   └── phoenix_heatmap.json

│   │

│   ├── scripts/

│   │   └── generate_demo_heatmap.py

│   │

│   ├── .env

│   └── .env.example

│

├── frontend/

│   │

│   ├── app/

│   │   ├── page.tsx

│   │   └── globals.css

│   │

│   ├── components/

│   │   ├── HeatMap.tsx

│   │   └── HeatMapLoader.tsx

│   │

│   ├── .env.local

│   └── .env.example

│

├── ml/

├── data/

├── docs/

├── demo/

├── notebooks/

│

├── .gitignore

└── README.md


# 20. Backend Setup

Move to the backend:


cd backend


Create a virtual environment:


python -m venv .venv


Activate it:


.\\.venv\Scripts\Activate.ps1


Install dependencies:


pip install fastapi "uvicorn[standard]" httpx python-dotenv pydantic-settings


Create:


backend/.env


Example:


FORTYGUARD_API_KEY=

FORTYGUARD_BASE_URL=https://api.fortyguard.com

DEMO_MODE=false


If the API key is empty, AI HeatShield automatically operates in demo mode.

Start the backend:


uvicorn app.main\:app --reload


Backend:


http://127.0.0.1:8000


API documentation:


http://127.0.0.1:8000/docs


Analysis endpoint:


http://127.0.0.1:8000/api/analyze


# 21. Frontend Setup

Open another terminal.

Move to:


cd frontend


Install dependencies:


npm install


Create:


frontend/.env.local


Add:


NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000


Start the frontend:


npm run dev


Open:


http://localhost:3000


# 22. Production Build

Before deployment, verify the frontend production build:


npm run build


Then production mode can be started using:


npm start


# 23. Main Backend Endpoint


GET /api/analyze


Optional selected heat cell:


GET /api/analyze?tile_id=\<tile_id>


Example response structure:


{

  "project": "AI HeatShield",

  "mode": "DEMO",

  "location": {

    "city": "Phoenix",

    "state": "Arizona",

    "country": "USA"

  },

  "statistics": {},

  "selected_zone": {},

  "map_tiles": [],

  "hotspots": []

}


# 24. Unified Analysis Response

One analysis request can provide the frontend with:


Location

↓

Spatial Heat Cells

↓

Risk Scores

↓

Selected Zone

↓

Risk Drivers

↓

Hotspots

↓

Forecast

↓

Historical Comparison

↓

Vulnerability Analysis

↓

Recommendations

↓

Intervention Scenarios


This keeps the frontend architecture simple while the backend coordinates the analytical services.

# 25. Example User Journey

A city planner opens AI HeatShield.

### Step 1

The dashboard displays the heat landscape.

### Step 2

The planner identifies a high-risk area.

### Step 3

They select the heat cell.

### Step 4

AI HeatShield calculates:


Risk Score: 84

Risk Level: VERY HIGH


### Step 5

The system explains the major drivers.


Temperature

Solar Radiation

Heat Index


### Step 6

The system evaluates population vulnerability.


Outdoor Worker → highest relative risk

Elderly → elevated risk

Child → elevated risk

General Public → baseline risk


### Step 7

The recommendation engine proposes actions.


Increase shade

Deploy hydration points

Adjust outdoor work schedules

Protect vulnerable populations


### Step 8

The planner evaluates interventions.


Shade

Tree Canopy

Cool Surface

Combined Cooling


The platform estimates how each scenario could change the calculated risk.

# 26. Potential Real-World Users

AI HeatShield could support decision-making for:

### Municipal Governments

Urban heat mitigation and hotspot prioritization.

### Smart-City Teams

Climate resilience monitoring.

### Universities and Campuses

Outdoor student and staff safety.

### Construction Companies

Outdoor workforce heat-risk planning.

### Event Organizers

Outdoor event safety.

### Logistics Operations

Driver and delivery-worker heat exposure planning.

### Public Health Teams

Community heat-response prioritization.

### Urban Planners

Evaluating potential cooling strategies.

# 27. What Makes AI HeatShield Different?

Many weather applications answer:

How hot is the city?

AI HeatShield is designed to answer:


WHERE is heat risk highest?

        ↓

WHY is the risk high?

        ↓

WHO may be more vulnerable?

        ↓

WHAT may happen next?

        ↓

WHAT action should be considered?

        ↓

HOW could an intervention change the risk?


This moves the product from:


Weather Visualization


toward:


Urban Heat Decision Intelligence


# 28. Responsible AI & Data Transparency

AI HeatShield clearly separates:


External / Retrieved Data


from:


Estimated / Scenario / Synthetic Data


The platform follows several transparency principles:

1. Synthetic demonstration data is labeled as synthetic.

2. Live data and demo data use different source states.

3. API fallback is labeled DEMO_FALLBACK.

4. Historical demo baselines are labeled estimated.

5. Forecast demo values are labeled scenario-generated.

6. Intervention simulations are labeled estimates.

7. Vulnerability scores are labeled heuristic decision-support.

8. Vulnerability outputs are not presented as medical predictions.

These distinctions are important for responsible climate decision-support systems.

# 29. Current Limitations

The hackathon prototype currently has several limitations.

### Demonstration Dataset

Without a configured external API key, the system uses synthetic Phoenix heat data.

### Forecast Model

The current demo forecast uses deterministic scenario assumptions rather than a trained operational forecasting model.

### Historical Comparison

Historical demo values are estimated rather than observed measurements.

### Intervention Model

Cooling impacts are scenario-based estimates and are not validated causal predictions.

### Vulnerability Model

Persona sensitivity uses heuristic assumptions rather than individual medical or epidemiological models.

### Environmental Parameter Availability

The deployed FortyGuard tcm heatmap provides the primary hyperlocal temperature field. Humidity, wet-bulb temperature, and solar radiation are currently aligned Open-Meteo historical contextual values, while heat index is derived from FortyGuard temperature plus contextual humidity. These contextual variables do not have FortyGuard's hyperlocal cell resolution.

These limitations are intentionally disclosed rather than hidden.

# 30. Future Development

Future versions of AI HeatShield could include:


FortyGuard Environmental Parameters endpoint integration

Real historical heat retrieval

Operational forecast normalization

Satellite imagery

Street-view urban segmentation

Tree-canopy detection

Building-density analysis

Machine-learning heat forecasting

Automated heat alerts

GIS layer import

Cooling-center locations

Hospital / emergency infrastructure overlays

Population-density integration

Mobile alerts

Multi-city dashboards

PDF heat-risk reports

Intervention cost-benefit analysis


# 31. Future ML Architecture

A future machine-learning forecasting pipeline could use:


Historical Temperature

\+

Heat Index

\+

Humidity

\+

Wet-Bulb Temperature

\+

Solar Radiation

\+

Time Features

\+

Spatial Features

\+

Urban Characteristics

        ↓

Feature Engineering

        ↓

Forecast Model

        ↓

Future Heat Conditions

        ↓

AI HeatShield Risk Engine

        ↓

Future Risk Probability


Possible models include:


XGBoost

LightGBM

Random Forest

LSTM

Temporal Transformer

Spatiotemporal Neural Networks


Model selection should depend on available data quality, spatial resolution, forecast horizon, and validation performance.

# 32. Hackathon Demonstration Flow

Recommended demo sequence:


1\. Open AI HeatShield dashboard

2\. Explain that city-wide temperature hides

   hyperlocal heat differences

3\. Show the spatial heat map

4\. Switch between:

   Risk

   Temperature

   Heat Index

5\. Select a high-risk cell

6\. Show the risk score

7\. Explain the primary and secondary drivers

8\. Show the priority hotspots

9\. Show the 12-hour outlook

10\. Show historical comparison

11\. Compare population personas

12\. Show recommended actions

13\. Open the intervention simulator

14\. Compare:

    Shade

    Tree Canopy

    Cool Surface

    Combined Cooling

15\. Explain LIVE / DEMO / DEMO_FALLBACK

    transparency

16\. Finish with the core message:


AI HeatShield transforms hyperlocal heat data into explainable, actionable urban heat decisions.

# 33. 30-Second Pitch

Cities already know that extreme heat is dangerous, but city-wide weather readings do not tell decision-makers which street, block, campus area, or outdoor zone requires attention first.

AI HeatShield transforms hyperlocal heat information into urban decision intelligence.

It identifies heat hotspots, calculates explainable risk scores, analyzes environmental drivers, estimates short-term risk, compares population vulnerability, recommends actions, and simulates potential cooling interventions such as shade, tree canopy, and reflective surfaces.

Instead of simply asking:

"How hot is it?"

AI HeatShield helps decision-makers ask:

"Where should we act first, why, and what could we do about it?"

**# Live Deployment & Verified Hackathon Result

Live dashboard: https://ai-heatshield.vercel.app

Production API health: https://ai-heatshield.fastapicloud.dev/api/health

Production analysis endpoint: https://ai-heatshield.fastapicloud.dev/api/analyze

GitHub: https://github.com/tabbydev01/AI-HeatShield

Verified deployed demo result:

FortyGuard source mode: LIVE

Analysis location: New York City, New York, USA

FortyGuard heat cells normalized and visualized: 150

Verified temperature range: 31.89°C – 33.14°C

Verified mean temperature: 32.26°C

Interactive selection updates risk, drivers, hotspots, recommendations, vulnerability and intervention views without generating a new upstream heatmap for every click because the heatmap is cached.

The verified demo uses real FortyGuard historical heatmap data fetched through the live API integration. It should not be described as current real-time weather.

34. Hackathon**

Built for:


FortyGuard Hackathon'26


Project:


AI HeatShield


Category:


Climate Technology

Urban Heat Intelligence

Decision Support

Smart Cities


# 35. Final Vision

AI HeatShield is designed around a simple idea:

Heat data becomes significantly more valuable when it helps people make better decisions.

The long-term vision is a platform capable of combining hyperlocal environmental intelligence, spatial analytics, forecasting, explainable risk models, population vulnerability, and urban intervention planning into one climate-resilience decision system.

## AI HeatShield

### From Heat Data → Risk Intelligence → Action