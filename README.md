# ₿ Schrödinger's Bitcoin Model Simulator

A Streamlit-based simulator for modeling Bitcoin's fair market value by estimating its potential to absorb the monetary premium of traditional store-of-value assets like gold, real estate, and bonds.

https://schrodinger-btc.streamlit.app/

---

## How It Works

This model is based on the hypothesis that Bitcoin can gradually absorb the **monetary premium** of other major assets — the portion of their value that comes from being used as a store of value, rather than from their utility.

You define:

- Market capitalizations of other assets
- Percentage of monetary premium
- Estimated share Bitcoin might capture

Then the simulator estimates a **Fair Market Cap** and **Fair Price** for BTC.

---

## Run with Docker

```bash
# Build the image
docker build -t schrodinger-btc-app .

# Run the container
docker run -p 8501:8501 schrodinger-btc-app
```

## References

- [Schrödinger's Bitcoin Thesis (PDF)](https://nakamotoportfolio.com/static/docs/Schrodingers_Coin_Model.pdf) – Conceptual foundation for the monetary premium absorption model.

