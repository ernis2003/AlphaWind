import pandas as pd
from tabulate import tabulate
from pandas.api.types import is_string_dtype, is_numeric_dtype
import matplotlib.pyplot as plt
from visualizations import DataVisualizer
import numpy as np
import seaborn as sns

root_folder = "data"

df_production    = pd.read_csv(f"{root_folder}/production.csv")
stop_logs        = pd.read_csv(f"{root_folder}/stop_logs.csv")
turbine_metadata = pd.read_csv(f"{root_folder}/turbine_metadata.csv")
weather          = pd.read_csv(f"{root_folder}/weather.csv")

datasets = {"production": df_production, "stop_logs": stop_logs, "turbine_metadata": turbine_metadata, "weather": weather}

LINE_LENGTH = 100

continuous_data  = {}
categorical_data = {}

def check_data_costitency(df: pd.DataFrame, df_name: str) -> None:
    cols = df.columns

    duplicates_rows = df[df.duplicated(keep=False)]
    if not duplicates_rows.empty:
        print_alert("Found duplicated rows", f"Dataset {df_name} contains {len(duplicates_rows)} duplicated rows", "red")
        df.drop_duplicates(inplace=True)
    
    continuous_data.setdefault(df_name, {})
    categorical_data.setdefault(df_name, {})

    for col_name in cols:
        if len(col_name.strip()) != len(col_name):
            print_alert("Empty spaces in column name", f"Dataset {df_name} column '{col_name}' contains space symbols", "red")
            df.rename(columns={col_name: col_name.strip()}, inplace=True)
            col_name = col_name.strip()

        NaN_records = df[df[col_name].isna()]
        if len(NaN_records) > 0:
            print_alert("NaN values found", f"Dataset {df_name} column '{col_name}' contains {len(NaN_records)} NaN values", "red")
            for idx, row in NaN_records.iterrows():
                find_replace_missing_timestamp(df, row)
            
        empty_cells_count = df[col_name].apply(lambda x: isinstance(x, str) and x.strip() == "").sum()
        if empty_cells_count > 0:
            print_alert("Empty cells detected", f"Dataset {df_name} column '{col_name}' contains {empty_cells_count} empty cells", "red")

        # Išskirčių skaičiavimas
        description = df[col_name].describe()
        if is_numeric_dtype(df[col_name]) and not df[col_name].empty:
            lower = description['25%']
            upper = description['75%']
            IQR = upper - lower
            lower_threshold =  lower - 1.5 * IQR
            upper_threshold =  upper + 1.5 * IQR
            outliers_records = df[(df[col_name] < lower_threshold) | (df[col_name] > upper_threshold)]
            if len(outliers_records) > 0:
                print_alert("Outliers detected", f"Dataset {df_name} column '{col_name}' contains {len(outliers_records)} outleirs", "red")

            continuous_data[df_name][col_name] = {
                "count": description["count"],
                "mean": f"{description["mean"]:.2f}",
                "std": f"{description["std"]:.2f}",
                "min": f"{description["min"]:.2f}",
                "25%": f"{description['25%']:.2f}",
                "median": f"{description["50%"]:.2f}",
                "75%": f"{description['75%']:.2f}",
                "max": f"{description["max"]:.2f}",
                "IQR": f"{IQR:.2f}",
                "lower_threshold": f"{lower_threshold:.2f}",
                "upper_threshold": f"{upper_threshold:.2f}",
                "outliers_count": len(outliers_records),
                "missing_count": df[col_name].isna().sum()
            }

        elif is_string_dtype(df[col_name]) and col_name not in ['timestamp', 'timestamp_start', 'timestamp_end']:
            print(f"Text description: {description}")
            categorical_data[df_name][col_name] = {
                "count": description["count"],
                "unique": description["unique"],
                "top": description.get("top"),
                "freq": description.get("freq"),
                "missing_count": df[col_name].isna().sum(),
                "empty_count": empty_cells_count,
                "value_counts": df[col_name].value_counts().to_dict(),
                "value_percentages": (df[col_name].value_counts(normalize=True) * 100).round(2).to_dict()
            }
            
    if df_name == "stop_logs":
        df['time_diff'] = pd.to_datetime(df['timestamp_end']) - pd.to_datetime(df['timestamp_start'])
        negative_count = (df["time_diff"] <= pd.Timedelta(0)).sum()
        if negative_count > 0:
            print_alert("Found overlapping timestamp_start and timestamp_end values", f"Overlapping {negative_count} values", "red")
        print(df.head(10))

        # Kiek kiekviena turbina turi stop reikšmių
        turbines_id = list(df['turbine_id'].unique())
        for turbine in turbines_id:
            stop_records = df[df['turbine_id'] == turbine]
            records_by_group = (stop_records.groupby('stop_code').size().reset_index())
            print(f"{turbine} ({len(stop_records)} stop counts)\n{records_by_group}\n\n")

    if df_name == "weather":
        duplicates = df[df['timestamp'].duplicated(keep=False)]
        print(f"Weather duplicates:\n{duplicates}")

def find_replace_missing_timestamp(original_df: pd.DataFrame, missing_value_row: pd.Series) -> pd.DataFrame:
    start_time = missing_value_row['timestamp_start']
    stop_code  = missing_value_row['stop_code']
    other_turbines_records = original_df[(original_df['timestamp_start'] == start_time) & (original_df['stop_code'] == stop_code)]
    valid_end_times = other_turbines_records['timestamp_end'].dropna()
    is_same_finish_time = len(valid_end_times) > 0 and valid_end_times.nunique() == 1

    if is_same_finish_time:
        original_df.loc[missing_value_row.name, 'timestamp_end'] = valid_end_times.iloc[0]
    return original_df

def print_alert(title: str, text: str, color: str) -> None:
    text_colors: dict[str, str] = {
        "red": "31",
        "green": "32",
        "blue": "34"
    }
    line = "=" * LINE_LENGTH
    print(f"\033[1;{text_colors.get(color, '31')}m{line}\n{title}\n{f'Explanation: {text}'}\n{line}\033[0m\n")

def print_statistics(continuous_data: dict, categorical_data: dict) -> None:
    for df_name in continuous_data:
        print(f"\n{'=' * 80}\nDATASET: {df_name.upper()}\n{'=' * 80}")

        if continuous_data.get(df_name):
            print("\nCONTINUOUS DATA")
            df = pd.DataFrame(continuous_data[df_name]).T
            print(tabulate(df, headers="keys", tablefmt="rounded_grid"))

        if categorical_data.get(df_name):
            print("\nCATEGORICAL DATA")
            df = pd.DataFrame(categorical_data[df_name]).T
            df = df.drop(columns=["value_counts", "value_percentages"], errors="ignore")
            print(tabulate(df, headers="keys", tablefmt="rounded_grid"))


for key, df in datasets.items():
    check_data_costitency(df, key)

# Clear data copies
turbine_metadata = turbine_metadata.copy()
df_production = df_production.copy()
stop_logs = stop_logs.copy()
weather = weather.copy()

print_statistics(continuous_data, categorical_data)
visualizer = DataVisualizer()
turbines_count = turbine_metadata['turbine_id'].nunique()

# ===== Park level performance =====
counts = stop_logs["turbine_id"].value_counts()
service_days = turbine_metadata.set_index("turbine_id")["last_service_days_ago"]
labels = [f"{service_days[turbine]} days since service" for turbine, _ in counts.items()]
print(f"counts: {counts}")
# visualizer.countplot(stop_logs, "turbine_id", title="Number of Stops by Turbine", filename="turbine_stops.png", labels=labels)

stop_logs['timestamp_start'] = pd.to_datetime(stop_logs['timestamp_start'])
stop_logs['timestamp_end'] = pd.to_datetime(stop_logs['timestamp_end'])
stop_logs['duration_h'] = (stop_logs['timestamp_end'] - stop_logs['timestamp_start']).dt.total_seconds() / 3600

df_production["timestamp"] = pd.to_datetime(df_production["timestamp"])
first_record = df_production["timestamp"].min()
last_record = df_production["timestamp"].max() + pd.Timedelta(minutes=10)
TOTAL_WORKING_PERIOD = (last_record - first_record).total_seconds() / 3600

duration_by_reason = stop_logs.groupby('comment')['duration_h'].sum().sort_values().reset_index()
total_downtime_h = duration_by_reason["duration_h"].sum()
downtime_percentage = total_downtime_h / (TOTAL_WORKING_PERIOD * turbines_count) * 100

# visualizer.barplot(duration_by_reason,  x="comment", y="duration_h", horizontal=True, title=f"Total Downtime is {downtime_percentage:.2f}% ({total_downtime_h:.2f}h / {TOTAL_WORKING_PERIOD * turbines_count:.2f}h) by Reason", filename="downtime_by_reason.png")

# Kiek % prastovų sudarė viso parko paveiktos problemos, o kiek asmeninės problemos
park_level_errors = ["WND", "GRD"]
turbine_level_errors = ["FLT", "MTN"]
colors = {
    "total": "#75589d",
    "park_level": "#4C86C6",
    "turbine_level": "#DC5B52"
}

park_level_rows = stop_logs[stop_logs['stop_code'].isin(park_level_errors)]['duration_h'].sum()
turbine_level_rows = stop_logs[stop_logs['stop_code'].isin(turbine_level_errors)]['duration_h'].sum()
downtime_reason = pd.DataFrame({"category": ["total", "park_level", "turbine_level"], "durations": [park_level_rows + turbine_level_rows, park_level_rows, turbine_level_rows]})
# visualizer.barplot(downtime_reason, x="category", y="durations", palette=colors, title="Total vs Park vs Turbine level total time count", filename="downtime_by_category.png")


# ===== Turbine level performance =====
production_by_turbine = df_production.groupby('turbine_id')['energy_kwh'].sum().reset_index()
labels = [f"{el:.2f}kW" for el in production_by_turbine['energy_kwh'].to_list()]
total_kW_generated = production_by_turbine['energy_kwh'].sum()
# visualizer.lineplot(production_by_turbine, x="turbine_id", y="energy_kwh", labels=labels, title=f"In {TOTAL_WORKING_PERIOD / 24:.2f} days generated energy {total_kW_generated:.2f}kWh -> {total_kW_generated / 1000:.2f}MWh", filename="generated_energy_by_turbine.png")

THRESHOLD = 90
availability_by_turbine = stop_logs.groupby('turbine_id')['duration_h'].sum().reset_index()
availability_by_turbine['availability, %'] = round(100 - (availability_by_turbine['duration_h'] / TOTAL_WORKING_PERIOD * 100), 2)
availability_by_turbine.loc[len(availability_by_turbine)] = ["Average", availability_by_turbine['duration_h'].agg('mean'), availability_by_turbine['availability, %'].agg('mean')]
# visualizer.lollipop(availability_by_turbine, x="turbine_id", y="availability, %", threshold=90, title=f"Turbines with availability >{THRESHOLD}% are not effective", filename="turbine_availability.png")

WIND_BIN_SIZE = 1
weather['timestamp']       = pd.to_datetime(weather['timestamp'])
df_production['timestamp'] = pd.to_datetime(df_production['timestamp'])

production_wind_speed = pd.merge(weather, df_production, how="left", on="timestamp").reset_index()

max_wind_speed = production_wind_speed['wind_speed_ms'].max()
bins = np.arange(0, max_wind_speed + WIND_BIN_SIZE * 2, WIND_BIN_SIZE)

production_wind_speed['wind_bin'] = pd.cut(production_wind_speed['wind_speed_ms'], bins=bins, right=False)
production_wind_speed_copy = production_wind_speed.copy()
production_wind_speed = production_wind_speed.groupby(['turbine_id', 'wind_bin']).agg({"energy_kwh": "median", "wind_speed_ms": "median"}).reset_index()
print(f"Production:\n{production_wind_speed_copy}")
# visualizer.lineplot(data=production_wind_speed, x="wind_speed_ms", y="energy_kwh", hue="turbine_id", marker="o", title="Wind speed vs Energy Production", filename="wind_speed_vs_energy_kwh.png")

turbine_energy_kwh_by_wind_bin = production_wind_speed.groupby('wind_bin')['energy_kwh'].median()
print(f"Mean by all turbines:\n{turbine_energy_kwh_by_wind_bin}")

energy_loss_df = production_wind_speed_copy.copy()

energy_loss_df["is_stopped"] = False

for _, stop in stop_logs.iterrows():
    mask = (
        (energy_loss_df["turbine_id"] == stop["turbine_id"]) &
        (energy_loss_df["timestamp"] >= stop["timestamp_start"]) &
        (energy_loss_df["timestamp"] < stop["timestamp_end"])
    )
    energy_loss_df.loc[mask, "is_stopped"] = True
normal_production = energy_loss_df[~energy_loss_df["is_stopped"]]

expected_by_wind = normal_production.groupby("wind_bin", observed=True)["energy_kwh"].median()

energy_loss_df["expected_kwh"] = energy_loss_df["wind_bin"].map(expected_by_wind).astype(float)

energy_loss_df["energy_kwh_diff"] = (energy_loss_df["expected_kwh"] - energy_loss_df["energy_kwh"]).clip(lower=0)
grouped_loss_by_turbine = energy_loss_df.groupby(['turbine_id', 'wind_bin'])['energy_kwh_diff'].sum()
print(f"Grouped loss by bin and turbine:\n{grouped_loss_by_turbine.to_string()}")

heatmap_data = grouped_loss_by_turbine.unstack(level="wind_bin")
# visualizer.heatmap(heatmap_data, title=f"Energy loss by turbine", filename="energy_loss_heatmap.png")

# ===== Expected production model =====

# Compare expected and actual production.

# Identify periods of significant production losses.

# Estimate energy losses by cause.
stop_intervals = stop_logs.copy()
stop_intervals["timestamp"] = stop_intervals.apply(lambda row: pd.date_range(start=row["timestamp_start"], end=row["timestamp_end"], freq="10min", inclusive="left"), axis=1)
stop_intervals = stop_intervals.explode("timestamp")

stop_intervals = stop_intervals.merge(weather[["timestamp", "wind_speed_ms"]], on="timestamp", how="left")
stop_intervals["wind_bin"] = pd.cut(stop_intervals["wind_speed_ms"], bins=bins, right=False)

stop_intervals['loss_energy'] = stop_intervals["wind_bin"].map(expected_by_wind).astype(float)
stop_intervals = stop_intervals.merge(df_production[["timestamp", "turbine_id", "energy_kwh"]], on=["timestamp", "turbine_id"], how="left")
stop_intervals["loss_energy"] = (stop_intervals["loss_energy"] - stop_intervals["energy_kwh"]).clip(lower=0)

# Theoretical assumption, that WND status_code and turbines are able to generate max possible energy in park
WND_ASSUMED_ENERGY_KWH = df_production['energy_kwh'].max()
stop_intervals.loc[stop_intervals["stop_code"] == "WND", "loss_energy"] = WND_ASSUMED_ENERGY_KWH

TARGET_STOP_CAUSE = "FLT"
loss_by_turbine = stop_intervals.groupby(['turbine_id', 'stop_code'])['loss_energy'].sum().reset_index()
loss_pivot = loss_by_turbine.pivot(index="turbine_id", columns="stop_code", values="loss_energy").fillna(0)

# visualizer.stacked_barplot(loss_pivot, title=f"Lose by cause type including theoretical assumption (WND status code = 250kW power ~ 41,67kWh)", filename="turbine_lose_by_cause.png")

# ===== Lose by category =====
lose_turbines_by_cause = stop_intervals.groupby(['stop_code'])['loss_energy'].sum().reset_index()
print(f"Got lose:\n{lose_turbines_by_cause}")

unexplained_df = energy_loss_df[~energy_loss_df["is_stopped"]].copy()
unexplained_by_turbine = unexplained_df.groupby("turbine_id")["energy_kwh_diff"].sum().sort_values(ascending=False)

total_unexplained = unexplained_by_turbine.sum()

print(f"Unexplained losses by turbine:\n{unexplained_by_turbine}")
print(f"Total unexplained energy loss: {total_unexplained:.2f} kWh")

# Actual production vs lost energy
actual_kwh = df_production["energy_kwh"].sum()
loss_kwh = loss_by_turbine['loss_energy'].sum() + total_unexplained  # Sum of all looses

production_summary = pd.DataFrame({"energy_mwh": [actual_kwh / 1000, loss_kwh / 1000]}, index=["Actual Production", "Estimated Shortfall"])

# visualizer.donutplot(production_summary, column="energy_mwh", title=f"{TOTAL_WORKING_PERIOD / 24:.0f} days Energy Production vs Estimated Loss", filename="weekly_energy_donut.png")

print(df_production.groupby('turbine_id')['energy_kwh'].sum() / 1000)

# Testas
park_production = df_production.groupby("timestamp")["energy_kwh"].sum().reset_index(name="park_energy_kwh")

# GRD stop start times (unique park-level events)
grd_starts = stop_logs.loc[stop_logs["stop_code"] == "GRD", "timestamp_start"].drop_duplicates()

# Production 10 minutes before GRD starts
grd_before = park_production[park_production["timestamp"].isin(grd_starts - pd.Timedelta(minutes=10))]

print("Maximum park production:", park_production["park_energy_kwh"].max(), "kWh / 10 min")
print("Production before GRD events:")
print(grd_before[["timestamp", "park_energy_kwh"]].to_string(index=False))

print("GRD production statistics:")
print(grd_before["park_energy_kwh"].describe())

grd_starts = stop_logs.loc[stop_logs["stop_code"] == "GRD", "timestamp_start"].drop_duplicates().sort_values()

grd_analysis = pd.DataFrame({"grd_start": grd_starts})
grd_analysis["before"] = grd_analysis["grd_start"] - pd.Timedelta(minutes=10)

grd_analysis = grd_analysis.merge(park_production.rename(columns={"timestamp": "before", "park_energy_kwh": "energy_before"}), on="before", how="left")
grd_analysis = grd_analysis.merge(park_production.rename(columns={"timestamp": "grd_start", "park_energy_kwh": "energy_during"}), on="grd_start", how="left")
grd_analysis = grd_analysis.merge(weather.rename(columns={"timestamp": "grd_start"}), on="grd_start", how="left")

grd_analysis["drop_pct"] = (grd_analysis["energy_before"] - grd_analysis["energy_during"]) / grd_analysis["energy_before"] * 100

# visualizer.grd_comparison(grd_analysis, title="Wind Farm Production Before and During GRD Events", filename="grd_comparison.png")


overlaps = stop_intervals[
    stop_intervals.duplicated(
        subset=["turbine_id", "timestamp"],
        keep=False
    )
]

print(f"Overlaps:\n{overlaps}")