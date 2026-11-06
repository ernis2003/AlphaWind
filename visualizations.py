
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

FIGSIZE = (14, 11)

class DataVisualizer:
    BLUE = "#2453FF"
    DARK = "#182238"
    GREY = "#AEB4BF"
    LIGHT = "#E7E9EE"

    def __init__(self, output_dir="charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="white", font="DejaVu Sans")
        plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "font.size": 11, "axes.titlesize": 17, "axes.titleweight": "bold", "text.color": self.DARK, "savefig.dpi": 300})

    def _finish(self, fig, ax, title, filename=None):
        ax.set_title(title, loc="left", pad=20, fontweight="bold")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        fig.tight_layout()

        if filename:
            fig.savefig(self.output_dir / filename, bbox_inches="tight", pad_inches=0.3)

        plt.show()
        plt.close(fig)

    def barplot(self, data, x, y, title="Bar Chart", horizontal=False, filename=None, labels=None, palette=None):
        fig, ax = plt.subplots(figsize=FIGSIZE)

        if horizontal:
            sns.barplot(data=data, x=y, y=x, color=self.BLUE, errorbar=None, ax=ax, palette=palette)
            ax.grid(axis="x", alpha=0.1)
        else:
            sns.barplot(data=data, x=x, y=y, color=self.BLUE, errorbar=None, ax=ax, palette=palette)
            ax.grid(axis="y", alpha=0.1)

        ax.set_axisbelow(True)
        for container in ax.containers:
            ax.bar_label(container, fmt="%.1f h", padding=5, fontsize=10, fontweight="bold")
            if labels:
                ax.bar_label(container, labels=labels, padding=5, fontsize=10, fontweight="bold")

        self._finish(fig, ax, title, filename)

    def lineplot(self, data, x, y, title="Time Series", hue=None, filename=None, labels=None, marker="o"):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        sns.lineplot(data=data, x=x, y=y, color=self.BLUE, hue=hue, linewidth=2.2, marker=marker, errorbar=None, ax=ax)
        if labels:
            for x_val, y_val, label in zip(data[x], data[y], labels):
                ax.annotate(str(label), (x_val, y_val), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, fontweight="bold")
        ax.grid(axis="y", alpha=0.12)
        ax.set_axisbelow(True)
        self._finish(fig, ax, title, filename)

    def countplot(self, data, column, title="Category Frequency", filename=None, labels=None):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        order = data[column].value_counts().index
        sns.countplot(data=data, x=column, order=order, color=self.BLUE, ax=ax)

        for container in ax.containers:
            ax.bar_label(container, padding=4, fontsize=10, fontweight="bold")
            if labels:
                ax.bar_label(container, padding=-50, labels=labels, color='white')

        ax.grid(axis="y", alpha=0.1)
        ax.set_axisbelow(True)
        self._finish(fig, ax, title, filename)

    def donutplot(self, data, column, title="Energy Distribution", filename=None):
        values = data[column]

        if values.empty or values.sum() <= 0:
            return

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = [self.BLUE, "#DC5B52"]

        wedges, _ = ax.pie(values.values, colors=colors[:len(values)], startangle=90, counterclock=False, wedgeprops={"width": 0.28, "edgecolor": "white", "linewidth": 3})

        total = values.sum()
        ax.text(0, 0.08, f"{total:,.2f}", ha="center", va="center", fontsize=25, fontweight="bold", color=self.DARK)
        ax.text(0, -0.15, "TOTAL MWh", ha="center", va="center", fontsize=11, color=self.GREY)

        ax.legend(wedges, [f"{name}: {value:,.2f} MWh ({value / total * 100:.1f}%)" for name, value in zip(data.index, values)], loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=1, frameon=False)

        self._finish(fig, ax, title, filename)

    def heatmap(self, data, title="Heatmap", filename=None, correlation=False, annot=False, cmap="Blues", center=None):
        if correlation:
            numeric = data.select_dtypes(include="number")
            if numeric.shape[1] < 2:
                return
            plot_data = numeric.corr()
            center = 0
            vmin, vmax = -1, 1
        else:
            plot_data = data.select_dtypes(include="number")
            if plot_data.empty:
                return
            vmin, vmax = None, None

        fig, ax = plt.subplots(figsize=(18, 6))
        sns.heatmap(plot_data, annot=annot, fmt=".2f", cmap=cmap, vmin=vmin, vmax=vmax, center=center, linewidths=0.5, linecolor="white", cbar_kws={"label": "Correlation" if correlation else "Energy Loss (kWh)"}, ax=ax)
        ax.set_xlabel("Wind Speed (m/s)" if not correlation else "")
        ax.set_ylabel("Turbine" if not correlation else "")
        ax.tick_params(axis="x", labelrotation=45)
        ax.tick_params(axis="y", labelrotation=0)
        self._finish(fig, ax, title, filename)

    def stacked_barplot(self, data, title="Stacked Bar Chart", horizontal=False, filename=None, colors=None, labels=True, suffix="kWh"):
        fig, ax = plt.subplots(figsize=FIGSIZE)

        default_colors = {"FLT": "#DC5B52", "GRD": self.BLUE, "MTN": "#F0B35A", "WND": self.GREY}
        colors = colors or default_colors
        palette = [colors.get(col, self.BLUE) for col in data.columns]

        data.plot(kind="barh" if horizontal else "bar", stacked=True, color=palette, width=0.65, edgecolor="white", linewidth=1, ax=ax)

        if labels:
            totals = data.sum(axis=1)
            for i, total in enumerate(totals):
                if horizontal:
                    ax.annotate(f"{total:,.1f} {suffix}", (total, i), xytext=(8, 0), textcoords="offset points", va="center", fontsize=10, fontweight="bold", color=self.DARK)
                else:
                    ax.annotate(f"{total:,.1f} {suffix}", (i, total), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=10, fontweight="bold", color=self.DARK)

        ax.set_xlabel("Energy Loss (kWh)" if horizontal else "Turbine")
        ax.set_ylabel("Turbine" if horizontal else "Energy Loss (kWh)")
        ax.grid(axis="x" if horizontal else "y", alpha=0.12)
        ax.set_axisbelow(True)
        ax.legend(title="Stop Reason", frameon=False)

        if horizontal:
            ax.invert_yaxis()
            ax.margins(x=0.15)
        else:
            ax.tick_params(axis="x", rotation=0)
            ax.margins(y=0.15)

        self._finish(fig, ax, title, filename)

    def lollipop(self, data, x, y, title="Lollipop Chart", filename=None, min_value=0, max_value=100, threshold=None, labels=True, suffix="%"):
        fig, ax = plt.subplots(figsize=FIGSIZE)

        values = pd.to_numeric(data[y])
        categories = data[x].astype(str)
        positions = range(len(data))

        colors = [self.BLUE if threshold is None or value >= threshold else "#DC5B52" for value in values]

        ax.hlines(y=positions, xmin=min_value, xmax=values, colors=colors, linewidth=2.5)
        ax.scatter(values, positions, c=colors, s=130, zorder=3)

        if labels:
            for i, value in enumerate(values):
                ax.annotate(f"{value:.2f}{suffix}", (value, i), xytext=(10, 0), textcoords="offset points", va="center", fontsize=11, fontweight="bold", color=self.DARK)

        ax.set_yticks(list(positions))
        ax.set_yticklabels(categories)
        ax.set_xlim(min_value, max_value)
        ax.set_xlabel(y)
        ax.set_ylabel(x)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.12)
        ax.set_axisbelow(True)

        self._finish(fig, ax, title, filename)

    def grd_comparison(self, data, title="Energy Production Before and During GRD", filename=None):
        fig, ax = plt.subplots(figsize=(12, 6))
        x = np.arange(len(data))
        width = 0.4
        labels = data["grd_start"].dt.strftime("%m-%d %H:%M")
        bars_before = ax.bar(x - width / 2, data["energy_before"], width, label="Before GRD", color=self.BLUE)
        bars_after = ax.bar(x + width / 2, data["energy_during"], width, label="During GRD", color="#388444")
        ax.bar_label(bars_before, fmt="%.2f kWh", padding=4, fontsize=10, fontweight="bold")
        ax.bar_label(bars_after, fmt="%.2f kWh", padding=4, fontsize=10, fontweight="bold")
        for i, row in enumerate(data.itertuples()):
            ax.text(x[i], max(row.energy_before, row.energy_during) * 1.10, f"-{row.drop_pct:.2f}%", ha="center", fontsize=11, fontweight="bold", color="#DC5B52")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Energy Production (kWh / 10 min)")
        ax.set_ylim(0, max(data["energy_before"].max(), data["energy_during"].max()) * 1.25)
        ax.grid(axis="y", alpha=0.12)
        ax.set_axisbelow(True)
        ax.legend(frameon=False)
        self._finish(fig, ax, title, filename)