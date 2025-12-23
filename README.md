📈 Stock & Index Price Movement Prediction using Trend-Based Data and Machine Learning

This repository contains the implementation and analysis of a machine learning–based framework for predicting stock and stock price index movement directions using both continuous technical indicators and a novel trend-deterministic (discrete) data representation.

The project compares the performance of multiple machine learning models on Indian stocks and indices over a 10-year period.

⚙️ Methodology

This project predicts stock and index price movement direction (up/down) using machine learning models and two different data representation strategies.

📊 Dataset

     10 years of historical data (2011–2020)

         Stocks: Tata Motors, BHEL

         Indices: Nifty Bank, S&P BSE Sensex

     Data split into parameter tuning and evaluation sets with balanced class distribution

🔁 Data Representation Approaches 

1️⃣ Continuous Data Approach

      Computes 10 technical indicators from historical price data

      Indicator values are normalized to the range [-1, +1]

      Used directly as input features to ML models

2️⃣ Trend-Deterministic Data Approach (Proposed)

      Converts continuous technical indicators into discrete trend signals

      Each indicator outputs:

          +1 → Upward trend

          -1 → Downward trend

      Based on trader-oriented rules and indicator behavior

      Helps reduce noise and improve model generalization

🤖 Machine Learning Models

      Artificial Neural Network (ANN)

      Support Vector Machine (SVM)

      Random Forest (RF)

      Naive Bayes

Model parameters are optimized using a validation subset, and final performance is evaluated using prediction accuracy.
