# Project Modules

## Live monitoring
- Open-Meteo current and hourly weather
- 1h / 3h / 6h / 24h rainfall windows
- 6-hour forecast rain context
- precipitation probability
- soil moisture model context

## Location intelligence
- NER monitoring database search
- Open-Meteo geocoding fallback
- browser GPS
- map click coordinate risk

## Terrain intelligence
- Open-Meteo elevation API
- Copernicus DEM GLO-90 elevation
- approximate local slope from a five-point neighborhood
- stored slope history

## Risk engine
- rainfall score
- slope score
- optional soil/forecast context
- LOW / MEDIUM / HIGH / CRITICAL levels
- thresholds are configurable prototype thresholds

## Early warning
- HIGH/CRITICAL alerts persisted in PostgreSQL
- alert acknowledgement
- optional browser notifications

## Analytics
- regional risk distribution
- state-wise overview
- risk history time series
- CSV export

## AI/ML
- RandomForest training pipeline from historical_landslides
- model status
- evaluation metrics: accuracy, precision, recall, F1, ROC-AUC
- model deliberately marked experimental until sufficient representative data exist

## Satellite context
- NASA GIBS MODIS Terra true-color layer
- satellite layer is visual context only; it is not used as a validated risk feature
