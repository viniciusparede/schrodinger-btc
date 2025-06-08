import streamlit as st
import pandas as pd
import altair as alt
import json
import requests
import re
from pathlib import Path


# --- CONFIGURAÇÃO DA PÁGINA E CONSTANTES ---
st.set_page_config(
    page_title="Schrödinger's Coin Model",
    layout="wide",
    page_icon="🪙",
    initial_sidebar_state="expanded",
)


# CSS
css_path = Path("styles.css")
st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def resolve_placeholders(obj, context):
    """
    Recursively resolve placeholders and evaluate expressions using the context dictionary.
    """
    if isinstance(obj, dict):
        return {k: resolve_placeholders(v, context) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_placeholders(i, context) for i in obj]
    elif isinstance(obj, str):
        # Substituir todos os placeholders
        while "{{" in obj and "}}" in obj:
            matches = re.findall(r"{{\s*(.*?)\s*}}", obj)
            for match in matches:
                if match not in context:
                    raise ValueError(f"Missing variable in context: {match}")
                obj = obj.replace(f"{{{{{match}}}}}", str(context[match]))
        try:
            return eval(obj)
        except:
            return obj
    else:
        return obj


@st.cache_data
def load_config(filepath="config.json", btc_price=None):
    """Carrega as configurações de um arquivo JSON e resolve placeholders."""
    with open(filepath, "r") as f:
        raw_config = json.load(f)

    # Monta o contexto com os valores do global_settings + btc_price dinâmico
    context = raw_config.get("global_settings", {}).copy()
    if btc_price is not None:
        context["default_btc_price"] = btc_price

    resolved_config = resolve_placeholders(raw_config, context)
    return resolved_config


config = load_config()
SUPPLY = config["global_settings"]["supply"]
SCENARIOS = config["scenarios"]


@st.cache_data(ttl=300)
def get_current_btc_price():
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        )
        data = response.json()
        return data["bitcoin"]["usd"]
    except Exception as e:
        st.error(f"Failed to fetch BTC price: {e}")
        return config["global_settings"]["default_btc_price"]


def display_sidebar():
    """Renderiza a barra lateral e retorna os inputs do usuário."""
    with st.sidebar:
        st.header("⚙️ Model Inputs")

        input_scenario = st.selectbox(
            "Market Scenario",
            ["Bearish", "Base", "Bullish", "Hyper"],
            index=0,
            help="Select a market scenario to adjust asset parameters.",
        )

        rate_percentage = st.slider(
            "Discount Rate (%)",
            0.0,
            25.0,
            value=SCENARIOS[input_scenario]["discount_rate_pct"],
            step=0.25,
            format="%.2f%%",
            help="Annual discount rate for present value calculations.",
        )
        discount_rate = rate_percentage / 100.0

        btc_price = float(get_current_btc_price())

        st.metric("Current BTC Price", f"${btc_price:,.2f}")

        st.markdown("---")

        # --- Definições e Agrupamento de Ativos ---
        default_assets = SCENARIOS[input_scenario]["assets"]
        asset_groups = {
            "Traditional Finance": ["Stocks", "Bonds"],
            "Precious Metals": ["Gold", "Silver"],
            "Real Assets": ["Real Estate"],
            "Crypto & Collectibles": ["Crypto (ex-BTC)", "Fine Art"],
        }

        st.subheader("Asset Assumptions")
        asset_params = {}
        for group, names in asset_groups.items():
            with st.expander(group, expanded=True):
                for name in names:
                    p = default_assets[name]
                    st.markdown(f"**{name}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        mcap = (
                            st.slider(
                                "Mcap ($T)",
                                0,
                                500,
                                int(p["mcap"] / 1e12),
                                10,
                                key=f"mcap_{name}",
                            )
                            * 1e12
                        )
                        mp = (
                            st.slider(
                                "Monetary Premium (%)",
                                0,
                                100,
                                p["monetary_premium_pct"],
                                5,
                                key=f"mp_{name}",
                            )
                            / 100
                        )
                    with col2:
                        prob = (
                            st.slider(
                                "Probability (%)",
                                0,
                                100,
                                p["probability_capture_pct"],
                                5,
                                key=f"prob_{name}",
                            )
                            / 100
                        )
                        time = st.slider(
                            "Time Horizon (Yrs)",
                            1,
                            50,
                            p["time_horizon_years"],
                            key=f"time_{name}",
                        )
                    asset_params[name] = {
                        "mcap": mcap,
                        "mp": mp,
                        "prob": prob,
                        "time": time,
                    }

    return asset_params, discount_rate, btc_price


def compute_valuations(asset_params: dict, discount_rate: float):
    """Calcula as valorações com base nos parâmetros."""
    data = []
    total_pv = 0
    for name, v in asset_params.items():
        cap_val = v["mcap"] * v["mp"] * v["prob"]
        pv = cap_val / ((1 + discount_rate) ** v["time"])
        data.append({"Asset": name, "Present Value (PV)": pv})
        total_pv += pv

    fair_mktcap = total_pv
    fair_price = fair_mktcap / SUPPLY
    df_breakdown = pd.DataFrame(data)

    return fair_mktcap, fair_price, df_breakdown


def display_main_content(
    fair_mktcap, fair_price, current_price, asset_params, discount_rate, df_breakdown
):
    """Renders the main content of the page."""
    st.title("🪙 Schrödinger's Bitcoin Model Simulator")
    st.markdown(
        "Explore the fair value of Bitcoin under different market scenarios. "
        "Adjust the inputs in the sidebar to customize the model."
    )

    with st.expander("ℹ️ About the Schrödinger's Coin Model"):
        st.markdown("""
        This model calculates the fair value of Bitcoin (BTC) by treating it as a "black hole" for the monetary premium of other assets. The idea is that Bitcoin will gradually absorb a portion of the market value (Market Cap) that other assets (such as Gold, Bonds, and Real Estate) hold purely as a store of value (Monetary Premium).

        - **Market Cap (Mcap):** The total value of an asset.
        - **Monetary Premium (MP):** The percentage of the Mcap not due to the asset’s utility, but to its ability to preserve value.
        - **Probability (Prob):** The probability that Bitcoin will capture this monetary premium from a given asset.
        - **Time Horizon (Time):** The number of years until this value capture is expected to occur.
        - **Discount Rate:** A rate used to bring future values to the present (Present Value).

        The **"Fair Value"** is the sum of the present value of all the monetary premiums that Bitcoin is expected to capture in the future.
        """)

    # --- Métricas Principais ---
    st.header("📈 Key Metrics")
    upside = (fair_price / current_price - 1) * 100 if current_price > 0 else 0
    cap_label = (
        f"${fair_mktcap / 1e12:.2f}T"
        if fair_mktcap >= 1e12
        else f"${fair_mktcap / 1e9:.2f}B"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Fair Market Cap", cap_label)
    col2.metric("Fair BTC Price", f"${fair_price:,.2f}")
    col3.metric("Upside Potential", f"{upside:.2f}%")

    # 🚨 Oportunidade clara de compra
    if upside > 100:
        st.success(
            f"🚀 **Bitcoin is trading at a massive discount!**\n\nBased on the model, BTC has a potential upside of **{upside:.2f}%** compared to its fair value."
        )
    elif upside > 30:
        st.info(
            f"📉 **Bitcoin appears undervalued.**\n\nPotential upside of **{upside:.2f}%** from the current price."
        )
    elif upside < -10:
        st.warning(
            f"⚠️ **Bitcoin is currently trading above its modeled fair value.**\n\nPotential downside of **{abs(upside):.2f}%**."
        )
    else:
        st.caption(
            f"📊 BTC is trading close to its fair value, deviation: {upside:.2f}%."
        )

    st.markdown("---")

    # --- Gráfico de Projeção ---
    st.subheader("Future Monetization Path")
    max_time = max(v["time"] for v in asset_params.values()) if asset_params else 1
    yrs = list(range(max_time + 1))
    proj_prices = [fair_price * ((1 + discount_rate) ** y) for y in yrs]
    path_df = pd.DataFrame({"Year": yrs, "Projected Price": proj_prices})

    chart = (
        alt.Chart(path_df)
        .mark_line(
            point=alt.OverlayMarkDef(color="#1a73e8", size=50, filled=True),
            color="#1a73e8",
        )
        .encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y(
                "Projected Price:Q",
                title="Projected BTC Price ($)",
                axis=alt.Axis(format="$,.0f"),
            ),
            tooltip=[
                alt.Tooltip("Year:O"),
                alt.Tooltip("Projected Price:Q", title="Price", format="$,.2f"),
            ],
        )
        .properties(height=400, title="Bitcoin Price Projection Over Time")
    )

    rule = (
        alt.Chart(pd.DataFrame({"y": [current_price]}))
        .mark_rule(color="red", strokeDash=[4, 4])
        .encode(y="y:Q")
    )

    st.altair_chart(
        (chart + rule)
        .configure_axis(grid=True, titleFontSize=14, labelFontSize=12)
        .configure_title(fontSize=16, anchor="start"),
        use_container_width=True,
    )
    st.markdown("---")


def main():
    asset_params, discount_rate, current_price = display_sidebar()

    if asset_params:
        fair_mktcap, fair_price, df_breakdown = compute_valuations(
            asset_params, discount_rate
        )
        display_main_content(
            fair_mktcap,
            fair_price,
            current_price,
            asset_params,
            discount_rate,
            df_breakdown,
        )
    else:
        st.warning("Please configure asset assumptions in the sidebar.")


if __name__ == "__main__":
    main()
