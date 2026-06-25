import gradio as gr
import pandas as pd
import numpy as np
import pickle
import socket
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
MODEL_CANDIDATES = [
    APP_DIR / "xgboost_regressor_r2_0_941_v1.pkl",
    Path(r"C:\Users\Rahmah Adnan\Desktop\Model") / "xgboost_regressor_r2_0_941_v1.pkl",
]
SCALER_CANDIDATES = [
    APP_DIR / "sc.pkl",
    Path(r"C:\Users\Rahmah Adnan\Desktop\Model") / "sc.pkl",
]


def _first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return paths[0]


MODEL_PATH = _first_existing(MODEL_CANDIDATES)
SCALER_PATH = _first_existing(SCALER_CANDIDATES)

model = None
sc = None
model_load_error = None

try:
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        raise FileNotFoundError(
            f"Missing model files. Expected:\n- {MODEL_PATH}\n- {SCALER_PATH}"
        )
    with open(MODEL_PATH, "rb") as model_file:
        model = pickle.load(model_file)
    with open(SCALER_PATH, "rb") as scaler_file:
        sc = pickle.load(scaler_file)
except Exception as exc:
    model_load_error = str(exc)


holiday_dic = {"No Holiday": 0, "Holiday": 1}
functioning_day_dic = {"Yes": 1, "No": 0}


def season_to_df(season):
    seasons_cols = ['Spring', 'Summer', 'Winter']
    data = np.zeros((1, len(seasons_cols)), dtype=int)

    df = pd.DataFrame(data, columns=seasons_cols)

    if season in seasons_cols:
        df[season] = 1

    return df


def days_df(weekday):
    days_names = [
        'Monday',
        'Saturday',
        'Sunday',
        'Thursday',
        'Tuesday',
        'Wednesday',
    ]

    data = np.zeros((1, len(days_names)), dtype=int)

    df = pd.DataFrame(data, columns=days_names)

    if weekday in days_names:
        df[weekday] = 1

    return df


def predict(
    date,
    hour,
    temperature,
    humidity,
    wind_speed,
    visibility,
    solar_radiation,
    rainfall,
    snowfall,
    season,
    holiday,
    functioning_day
):
    try:
        return _predict(
            date,
            hour,
            temperature,
            humidity,
            wind_speed,
            visibility,
            solar_radiation,
            rainfall,
            snowfall,
            season,
            holiday,
            functioning_day,
        )
    except Exception as exc:
        return f"Prediction failed: {exc}"


def _predict(
    date,
    hour,
    temperature,
    humidity,
    wind_speed,
    visibility,
    solar_radiation,
    rainfall,
    snowfall,
    season,
    holiday,
    functioning_day,
):
    if model is None or sc is None:
        return (
            "Model files could not be loaded. "
            f"Check that these files exist:\n- {MODEL_PATH}\n- {SCALER_PATH}\n"
            f"Error: {model_load_error}"
        )

    numeric_fields = {
        "Temperature": temperature,
        "Humidity": humidity,
        "Wind Speed": wind_speed,
        "Visibility": visibility,
        "Solar Radiation": solar_radiation,
        "Rainfall": rainfall,
        "Snowfall": snowfall,
    }
    missing = [name for name, value in numeric_fields.items() if value is None]
    if missing:
        return f"Please fill in all weather fields: {', '.join(missing)}"

    try:
        dt = datetime.strptime(date.strip(), "%d/%m/%Y")
    except ValueError:
        return "Invalid date. Use the format dd/mm/yyyy (for example, 25/12/2025)."

    day = dt.day
    month = dt.month
    year = dt.year
    weekday = dt.strftime("%A")

    user_data = [[
        hour,
        float(temperature),
        float(humidity),
        float(wind_speed),
        float(visibility),
        float(solar_radiation),
        float(rainfall),
        float(snowfall),
        holiday_dic[holiday],
        functioning_day_dic[functioning_day],
        day,
        month,
        year
    ]]

    columns = [
        'Hour',
        'Temperature(°C)',
        'Humidity(%)',
        'Wind speed (m/s)',
        'Visibility (10m)',
        'Solar Radiation (MJ/m2)',
        'Rainfall(mm)',
        'Snowfall (cm)',
        'Holiday',
        'Functioning Day',
        'Day',
        'Month',
        'Year'
    ]

    df_input = pd.DataFrame(user_data, columns=columns)

    df_season = season_to_df(season)
    df_weekday = days_df(weekday)

    final_df = pd.concat(
        [df_input, df_season, df_weekday],
        axis=1
    )

    if hasattr(sc, "feature_names_in_"):
        final_df = final_df[list(sc.feature_names_in_)]

    scaled_data = sc.transform(final_df)
    prediction = model.predict(scaled_data)[0]

    return f"Expected Bike Rentals: {round(prediction)}"


with gr.Blocks() as demo:

    gr.Markdown(
        """
        # 🚲 Bike Sharing Demand Predictor
        Predict the expected number of rented bikes.
        """
    )

    with gr.Row():
        date = gr.Textbox(
            label="Date",
            value="25/12/2025"
        )

        hour = gr.Slider(
            0,
            23,
            value=12,
            step=1,
            label="Hour"
        )

    with gr.Row():
        temperature = gr.Number(label="Temperature (°C)", value=25)
        humidity = gr.Number(label="Humidity (%)", value=50)

    with gr.Row():
        wind_speed = gr.Number(label="Wind Speed (m/s)", value=3)
        visibility = gr.Number(label="Visibility (10m)", value=200)

    with gr.Row():
        solar_radiation = gr.Number(label="Solar Radiation", value=0.5)
        rainfall = gr.Number(label="Rainfall (mm)", value=0)

    snowfall = gr.Number(label="Snowfall (cm)", value=0)

    with gr.Row():
        season = gr.Dropdown(
            ["Spring", "Summer", "Winter"],
            value="Summer",
            label="Season"
        )

        holiday = gr.Dropdown(
            ["No Holiday", "Holiday"],
            value="No Holiday",
            label="Holiday"
        )

        functioning_day = gr.Dropdown(
            ["Yes", "No"],
            value="Yes",
            label="Functioning Day"
        )

    btn = gr.Button("Predict")

    output = gr.Textbox(
        label="Prediction"
    )

    btn.click(
        predict,
        inputs=[
            date,
            hour,
            temperature,
            humidity,
            wind_speed,
            visibility,
            solar_radiation,
            rainfall,
            snowfall,
            season,
            holiday,
            functioning_day
        ],
        outputs=output
    )

def _find_free_port(preferred=8081, host="127.0.0.1"):
    for port in range(preferred, preferred + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    return 0


if __name__ == "__main__":
    if model is not None:
        print("Model loaded successfully.")
    else:
        print(f"Model not loaded: {model_load_error}")

    port = _find_free_port(8081)
    if port != 8081:
        print(f"Port 8081 is busy. Using port {port} instead.")

    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        theme=gr.themes.Soft(),
    )