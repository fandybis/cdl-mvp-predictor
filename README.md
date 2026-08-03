# CDL MVP Predictor

A data science project that ranks Call of Duty League players by their
consistent impact on the map.

## Initial data source

BreakingPoint player statistics.

## Initial impact metrics

- Overall K/D
- Hardpoint kills or engagements per 10 minutes
- Hardpoint damage per 10 minutes
- Search and Destroy K/D
- Search and Destroy kills per round
- Search opening-duel win percentage
- Control damage per 10 minutes
- Consistency across stages and events

## Project stages

1. Collect player statistics
2. Clean and validate the data
3. Engineer impact and consistency features
4. Build an explainable baseline ranking
5. Train and backtest prediction models
6. Publish an MVP leaderboard

## Repository structure

- `data/raw` — original collected data
- `data/interim` — partially cleaned data
- `data/processed` — model-ready datasets
- `notebooks` — exploration and model development
- `src` — reusable Python code
- `models` — saved model files
- `tests` — automated data and code tests
