# Route planner for DAF Navigation System
A Route Planner is an assistant for truck drivers. The Route Planner defines stopping points for the truck driver so that the driver can follow a healthy schedule of work and rest. Additionally, the Route Planner suggests cafes and hotels that are located near these points. The solution is described in detail in the [presentation for hackathon](/presentation/presentation.pdf).

## Content

[Context](#context)

[Example](#example)

[Team](#team)

[Files](#files)

[How to run](#how-to-run)

## Context 
The Route Planner was developed as part of the **DAF Hackathon** which took place on the 8th of June, 2024. The Route Planner is intended to be an extension for the existing DAF navigation system. Now it works as an independent web app, examples of which you can see below.

## Example

![Example](/presentation/example1.jpg)

## Team
* [Danila Solodennikov](https://github.com/Master-sniffer)
* [Aleksandr Vardanian](https://github.com/alex8399)
* [Aleksandr Nikolaev](https://github.com/Allex-Nik)
* [Aleksandr Raudvee](https://github.com/AlexRaudvee)

## Files

- `API_` - folder with code which extracts the data through api
- `app` - file where we create the framework
- `data` - folder in which we store needed data from apis or external datasets
- `presentation` - folder that contains the presentation material for the route planner
- `config.py` - configuration file
- `requirements.txt` - file which stores all used libraries

## How to run

### Prerequisites

1. **Python 3.10+**: Ensure you have Python 3.10 or later installed.
2. **API Key**: Obtain an API key for the Google Maps API and update the `config.py` file.

### Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/alex8399/daf-hackathon.git
    cd daf_hackathon
    ```

2. **Create and activate a virtual environment** (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required packages**:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1. **API Key**: Ensure your `config.py` file contains your Google Maps API key:
    ```python
    # config.py
    API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY'
    ```

### Running the Application

1. **Run the Streamlit app**:
    ```bash
    streamlit run app/main.py  
    ```

2. **Access the app**: Open your web browser and go to `http://localhost:8501`.

### Usage

1. **Enter the Origin and Destination**: Use the sidebar to input the origin and destination of your route.
2. **View the Route**: The app will display the best route on a map.
